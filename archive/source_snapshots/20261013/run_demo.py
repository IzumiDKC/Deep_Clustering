"""Compare deep-clustering timeline adaptations on the same bundled data.

Example: python run_demo.py --seeds 0 1 2 3 4
No network access is used. Figures and CSV files are written to --output.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import sys
import time
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy
import sklearn
from sklearn.decomposition import PCA
from sklearn.metrics import adjusted_rand_score, confusion_matrix
from threadpoolctl import threadpool_limits

from src.evaluation import evaluate, mapped_labels
from src.models import Autoencoder, fit_kmeans, pretrain, train_dec, train_dcn
from src.sane import density_aware_centers, train_sane_idec
from src.decra import train_decra
from src.dcss import train_dcss
from src.method_registry import METHOD_REGISTRY

ROOT = Path(__file__).resolve().parent
METHODS = ["AE_KMeans", "DEC", "IDEC", "DCN", "IDEC_BRB", "DECRA", "DCSS", "SANE_IDEC"]
DEFAULT_METHODS = ["DEC", "IDEC", "DECRA", "DCSS"]
NAMES = {"AE_KMeans": "AE + K-means", "DEC": "DEC", "IDEC": "IDEC", "DCN": "DCN",
         "IDEC_BRB": "IDEC + BRB demo", "DECRA": "DECRA code adaptation (2024)",
         "DCSS": "DCSS code adaptation (2026)",
         "SANE_IDEC": "IDEC + SANE-inspired (2026)"}


def write_rows(path, rows):
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def plot_results(out, runs, summary, representatives, x, y, seeds, dataset_name, digit_images=False):
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
    methods = summary.method.tolist()
    indices = np.arange(len(methods))
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.8), constrained_layout=True)
    for ax, metric in zip(axes, ["acc", "nmi", "ari"]):
        mean = summary[f"{metric}_mean"].to_numpy()*100
        std = summary[f"{metric}_std"].to_numpy()*100
        ax.bar(indices, mean, yerr=std, capsize=4, color=plt.get_cmap("tab10")(indices % 10))
        ax.set_xticks(indices, [NAMES[m] for m in methods], rotation=32, ha="right")
        ax.set_ylabel(f"{metric.upper()} (%)")
        ax.set_ylim(min(0, float((mean-std).min())-5), 100)
        ax.set_title(f"{metric.upper()} mean and sample std")
        ax.grid(axis="y", alpha=.2)
    fig.suptitle(f"{dataset_name} | {len(x)} samples | {len(seeds)} seeds", fontsize=12)
    fig.savefig(out / "performance.png", dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8), constrained_layout=True)
    values = [runs.loc[runs.method == method, "acc"].to_numpy()*100 for method in methods]
    axes[0].boxplot(values, tick_labels=[NAMES[m] for m in methods], showmeans=True)
    axes[0].set_ylabel("ACC (%)")
    axes[0].set_title("Variation across full-pipeline seeds")
    axes[0].tick_params(axis="x", labelrotation=30)
    pairmeans = summary.pairwise_ari_mean.to_numpy()
    axes[1].bar(indices, pairmeans, color="#346889")
    axes[1].set_xticks(indices, [NAMES[m] for m in methods], rotation=30, ha="right")
    axes[1].set_ylabel("Mean pairwise ARI between runs")
    axes[1].set_ylim(min(0, float(np.nanmin(pairmeans))-.05) if len(seeds)>1 else 0, 1)
    axes[1].set_title("Agreement between final partitions")
    fig.savefig(out / "stability.png", dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(len(methods), 2, figsize=(9, 2.6*len(methods)), constrained_layout=True, squeeze=False)
    for row, method in enumerate(methods):
        z, labels = representatives[method]
        if len(z) < 2:
            two_d = np.zeros((len(z), 2))
        else:
            projected = PCA(n_components=min(2, z.shape[1]), svd_solver="full").fit_transform(z)
            two_d = np.pad(projected, ((0,0),(0,2-projected.shape[1])))
        mapped, _ = mapped_labels(y, labels)
        classes = np.union1d(y, mapped)
        for col, color_values in enumerate([y, mapped]):
            colors = np.searchsorted(classes, color_values)
            axes[row, col].scatter(two_d[:,0], two_d[:,1], c=colors, cmap="tab20", vmin=0, vmax=max(1,len(classes)-1), s=6, alpha=.65, rasterized=True)
            axes[row, col].set_title(f"{NAMES[method]} | " + ("true class" if col == 0 else "mapped cluster"))
            axes[row, col].set_xticks([])
            axes[row, col].set_yticks([])
    fig.suptitle(f"PCA of latent embeddings | illustrative seed {seeds[0]} | no labels used in training")
    fig.savefig(out / "embeddings.png", dpi=150)
    plt.close(fig)

    cm_cols = min(3, len(methods))
    cm_rows = int(np.ceil(len(methods)/cm_cols))
    fig, axes = plt.subplots(cm_rows, cm_cols, figsize=(11, 3.5*cm_rows), constrained_layout=True, squeeze=False)
    for ax, method in zip(axes.flat, methods):
        _, labels = representatives[method]
        mapped, _ = mapped_labels(y, labels)
        classes = np.union1d(y, mapped)
        cm = confusion_matrix(y, mapped, labels=classes)
        ax.imshow(cm, cmap="Blues")
        ax.set_title(NAMES[method])
        ax.set_xlabel("Mapped cluster")
        ax.set_ylabel("True class")
        ticks = np.unique(np.linspace(0, len(classes)-1, min(5,len(classes)), dtype=int))
        ax.set_xticks(ticks, classes[ticks]); ax.set_yticks(ticks, classes[ticks])
    for ax in list(axes.flat)[len(methods):]:
        ax.axis("off")
    fig.savefig(out / "confusion_matrices.png", dpi=160)
    plt.close(fig)

    if digit_images:
        fig, axes = plt.subplots(4, 5, figsize=(8, 6), constrained_layout=True)
        for ax, i in zip(axes.flat, range(min(len(x), 20))):
            ax.imshow(x[i].reshape(8,8), cmap="gray_r", vmin=0, vmax=1)
            ax.set_title(f"Sample {i} | digit {y[i]}", fontsize=9)
            ax.axis("off")
        fig.savefig(out / "sample_images.png", dpi=160)
        plt.close(fig)

    ncols = 3
    phases = [("pretrain", "Pretraining: mean pixel MSE")]
    phases += [(m, NAMES[m] + ": own training objective") for m in methods if m != "AE_KMeans"]
    nrows = int(np.ceil(len(phases)/ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(12, 3.5*nrows), constrained_layout=True)
    for ax, (phase, title) in zip(axes.flat, phases):
        for seed in seeds:
            trace = pd.read_csv(out/"traces"/f"{phase}_seed{seed}.csv")
            ax.plot(trace.epoch, trace.total, label=f"seed {seed}", linewidth=1.2)
            if seed == seeds[0]:
                for epoch in trace.loc[trace.reset == 1, "epoch"]:
                    ax.axvline(epoch, color="#be8c55", linestyle="--", alpha=.6)
        ax.set_title(title, fontsize=10)
        ax.set_xlabel("Epoch"); ax.set_ylabel("Loss")
        ax.grid(alpha=.2)
    axes.flat[0].legend(fontsize=8)
    for ax in list(axes.flat)[len(phases):]:
        ax.axis("off")
    fig.suptitle("Training activity | losses use different definitions; do not rank methods by loss")
    fig.savefig(out/"loss_curves.png", dpi=160)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=ROOT/"data"/"digits_1797.npz")
    parser.add_argument("--dataset-name", default=None, help="Display name; defaults to the input filename")
    parser.add_argument("--output", type=Path, default=ROOT/"results_local")
    parser.add_argument("--seeds", nargs="+", type=int, default=[0,1,2,3,4])
    parser.add_argument("--methods", nargs="+", choices=METHODS, default=DEFAULT_METHODS)
    parser.add_argument("--clusters", type=int, default=10, help="Known K specified by the benchmark protocol, not inferred from y")
    parser.add_argument("--latent-dim", type=int, default=10)
    parser.add_argument("--pretrain-epochs", type=int, default=120)
    parser.add_argument("--cluster-epochs", type=int, default=60)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--gamma", type=float, default=.1)
    parser.add_argument("--dcn-weight", type=float, default=.01)
    parser.add_argument("--decra-gamma", type=float, default=.1)
    parser.add_argument("--decra-reconstruction-weight", type=float, default=2.0)
    parser.add_argument("--decra-consistency-weight", type=float, default=.6)
    parser.add_argument("--decra-kl-reduction", choices=["mean", "batchmean"], default="mean")
    parser.add_argument("--dcss-silhouette-weight", type=float, default=.01)
    parser.add_argument("--dcss-entropy-weight", type=float, default=.01)
    parser.add_argument("--dcss-temperature", type=float, default=.25)
    parser.add_argument("--dcss-distance-normalization", choices=["source", "paper"], default="source")
    parser.add_argument("--target-interval", type=int, default=5, help="Full-data P update interval in epochs")
    parser.add_argument("--brb-interval", type=int, default=20)
    parser.add_argument("--brb-alpha", type=float, default=.8)
    parser.add_argument("--sane-alpha", type=float, default=2.0, help="DACHI density weight, ICLR 2026 adaptation")
    parser.add_argument("--sane-neighbors", type=int, default=10)
    parser.add_argument("--sane-epsilon", type=float, default=.1, help="DSS second-order stability threshold")
    parser.add_argument("--sane-min-retain", type=float, default=.25, help="Small-data retention floor; adaptation only")
    parser.add_argument("--sane-weak-sigma", type=float, default=.025)
    parser.add_argument("--sane-strong-sigma", type=float, default=.08)
    parser.add_argument("--limit", type=int, default=0, help="Optional fixed random unlabeled subset; 0 uses all samples")
    args = parser.parse_args()
    if len(set(args.seeds)) != len(args.seeds) or len(set(args.methods)) != len(args.methods):
        parser.error("Seeds and methods must be unique.")
    if min(args.pretrain_epochs, args.cluster_epochs, args.batch_size, args.clusters, args.latent_dim, args.target_interval) < 1:
        parser.error("Epochs, batch size, clusters, latent dimension and target interval must be positive.")
    if not 0 < args.brb_alpha < 1 or args.brb_interval < 1 or args.learning_rate <= 0 or args.gamma < 0 or args.dcn_weight < 0:
        parser.error("Invalid learning rate, weights, or BRB settings.")
    if (args.sane_alpha < 0 or args.sane_neighbors < 1 or args.sane_epsilon < 0
            or not 0 < args.sane_min_retain <= 1
            or not 0 <= args.sane_weak_sigma < args.sane_strong_sigma):
        parser.error("Invalid SANE adaptation settings.")
    if min(args.decra_gamma, args.decra_reconstruction_weight, args.decra_consistency_weight) < 0:
        parser.error("DECRA loss weights must be nonnegative.")
    if min(args.dcss_silhouette_weight, args.dcss_entropy_weight) < 0 or args.dcss_temperature <= 0:
        parser.error("Invalid DCSS loss weights or temperature.")
    if any(seed < 0 or seed >= 2**31-1 for seed in args.seeds):
        parser.error("Seeds must be in [0, 2**31-2].")
    if not args.data.is_file():
        parser.error(f"Data file not found: {args.data}. Run python prepare_data.py first.")
    with np.load(args.data, allow_pickle=False) as bundle:
        if "X" not in bundle or "y" not in bundle:
            parser.error("NPZ must contain X and y; y is used only for evaluation.")
        x, raw_y = np.asarray(bundle["X"], dtype=np.float64), np.asarray(bundle["y"])
    if x.ndim != 2 or raw_y.ndim != 1 or len(x) != len(raw_y) or not x.size or not np.isfinite(x).all():
        parser.error("Expected finite X with shape (N,D) and y with shape (N,).")
    if not np.issubdtype(raw_y.dtype, np.number) or not np.isfinite(raw_y).all() or not np.equal(raw_y, np.floor(raw_y)).all():
        parser.error("Evaluation labels y must be finite integers; fractional labels are not cast silently.")
    y = raw_y.astype(np.int64)
    if x.min() < 0 or x.max() > 1:
        parser.error("Sigmoid reconstruction expects X already normalized to [0,1].")
    indices = np.arange(len(x))
    if args.limit:
        if args.limit < args.clusters or args.limit > len(x):
            parser.error("--limit must be between --clusters and the sample count.")
        indices = np.sort(np.random.default_rng(42).choice(len(x), args.limit, replace=False))
        x, y = x[indices], y[indices]
    if len(x) < args.clusters:
        parser.error("More clusters than samples.")
    out = args.output.resolve()
    if out.exists() and any(out.iterdir()):
        parser.error("Output already contains results. Choose a new --output folder to preserve the previous run.")
    for child in ["", "predictions", "traces", "models"]:
        (out/child).mkdir(parents=True, exist_ok=True)
    np.save(out / "sample_indices.npy", indices)
    settings = {k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()}
    settings["dataset_name"] = args.dataset_name or args.data.stem
    settings.update({"n_samples":len(x), "n_features":x.shape[1], "protocol":"transductive clustering on all X; y is evaluation only",
                     "implementation":"educational NumPy; not an exact paper reproduction", "architecture":[x.shape[1],64,32,args.latent_dim,32,64,x.shape[1]],
                     "n_init":20, "loss_scaling":"reconstruction averages N*D; KL and k-means distortion average N",
                     "sha256_data":hashlib.sha256(args.data.read_bytes()).hexdigest(),
                     "sha256_training_X":hashlib.sha256(np.ascontiguousarray(x).tobytes()).hexdigest(),
                     "sha256_sample_indices":hashlib.sha256(indices.tobytes()).hexdigest(),
                     "sane_scope":"IDEC adaptation of ICLR 2026 DACHI/DSS; original ResNet/MoCo-v2 code was not run",
                     "method_registry":{m:METHOD_REGISTRY[m] for m in args.methods if m in METHOD_REGISTRY},
                     "initialization_protocol":"Within each seed all methods clone identical plain-AE pretrained weights and initial KMeans centers; SANE then applies DACHI; DECRA adds randomly initialized adaptive branch",
                     "architecture_by_method":{m:{"base":[x.shape[1],64,32,args.latent_dim,32,64,x.shape[1]], "extra_adaptive_linear": m == "DECRA", "extra_rbf_log_sigmas": m == "DCSS"} for m in args.methods},
                     "implementation_checks":["checks/verification_local_models.json", "checks/verification_decra.json", "checks/verification_dcss.json"],
                     "executed_notebook":"notebooks/demo_4_timeline_verified.ipynb",
                     "selection_protocol":"Literature-led exploratory candidates, fixed settings before five-seed run; highest Digits mean is not universal 2025/2026 SOTA",
                     "decra_scope":"Released-code loss on shared NumPy backbone; no residual-AE pretraining; KL mean averages N*K unlike IDEC N",
                     "dcss_scope":"Released-code soft silhouette + RBF + entropy on shared backbone; source normalization and temperature differ from paper equations",
                     "timing_definition":"standalone = pretrain + shared KMeans initialization + method fitting including epoch loss traces; excludes final external metrics, plots and file writes"})
    settings["source_sha256"] = {str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest()
        for path in [ROOT/"run_demo.py",ROOT/"src/models.py",ROOT/"src/decra.py",ROOT/"src/dcss.py",
                     ROOT/"src/sane.py",ROOT/"src/evaluation.py",ROOT/"src/method_registry.py"]}
    (out/"config.json").write_text(json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8")
    environment = {"created_utc":datetime.now(timezone.utc).isoformat(), "python":sys.version,
                   "platform":platform.platform(), "processor":platform.processor(), "threads":1,
                   "numpy":np.__version__, "scipy":scipy.__version__, "sklearn":sklearn.__version__,
                   "pandas":pd.__version__, "matplotlib":matplotlib.__version__}
    (out/"environment.json").write_text(json.dumps(environment, indent=2), encoding="utf-8")
    all_rows, labels_by_method, representatives = [], {m:[] for m in args.methods}, {}
    with threadpool_limits(limits=1):
        for seed in args.seeds:
            start = time.perf_counter()
            pretrained = Autoencoder(x.shape[1], args.latent_dim, seed)
            history = pretrain(pretrained, x, args.pretrain_epochs, args.batch_size, args.learning_rate, seed)
            pretrain_seconds = time.perf_counter()-start
            write_rows(out/"traces"/f"pretrain_seed{seed}.csv", history)
            np.savez_compressed(out/"models"/f"pretrain_seed{seed}.npz", **pretrained.params)
            start = time.perf_counter()
            init_labels, init_centers = fit_kmeans(pretrained.encode(x), args.clusters, seed)
            initialization_seconds = time.perf_counter()-start
            np.savez_compressed(out/"models"/f"initialization_seed{seed}.npz", labels=init_labels, centers=init_centers)
            print(f"Seed {seed}: pretraining finished ({pretrain_seconds:.2f} s); common KMeans initialization ({initialization_seconds:.2f} s)", flush=True)
            for method in args.methods:
                model, centers = pretrained.clone(), init_centers.copy()
                print(f"  [{len(all_rows)+1}/{len(args.seeds)*len(args.methods)}] Training {method}...", flush=True)
                start = time.perf_counter()
                if method == "AE_KMeans":
                    labels = init_labels.copy()
                    z, trace = model.encode(x), []
                elif method == "DCN":
                    labels, z, centers, trace = train_dcn(model, x, centers,
                        epochs=args.cluster_epochs, batch_size=args.batch_size, learning_rate=args.learning_rate,
                        dcn_weight=args.dcn_weight, seed=seed)
                elif method == "DECRA":
                    labels, z, centers, trace = train_decra(model, x, centers,
                        epochs=args.cluster_epochs, batch_size=args.batch_size,
                        learning_rate=args.learning_rate, gamma=args.decra_gamma, seed=seed,
                        target_interval=args.target_interval,
                        consistency_weight=args.decra_consistency_weight,
                        reconstruction_weight=args.decra_reconstruction_weight,
                        kl_reduction=args.decra_kl_reduction)
                elif method == "DCSS":
                    labels, z, centers, trace = train_dcss(model, x, centers,
                        epochs=args.cluster_epochs, batch_size=args.batch_size,
                        learning_rate=args.learning_rate, seed=seed,
                        silhouette_weight=args.dcss_silhouette_weight,
                        entropy_weight=args.dcss_entropy_weight,
                        temperature=args.dcss_temperature,
                        distance_normalization=args.dcss_distance_normalization)
                elif method == "SANE_IDEC":
                    centers = density_aware_centers(pretrained.encode(x), init_labels, centers,
                                                    alpha=args.sane_alpha, k=args.sane_neighbors)
                    labels, z, centers, trace = train_sane_idec(model, x, centers,
                        epochs=args.cluster_epochs, batch_size=args.batch_size,
                        learning_rate=args.learning_rate, gamma=args.gamma, seed=seed,
                        target_interval=args.target_interval, epsilon=args.sane_epsilon,
                        min_retain_fraction=args.sane_min_retain,
                        weak_sigma=args.sane_weak_sigma, strong_sigma=args.sane_strong_sigma)
                else:
                    labels, z, centers, trace = train_dec(model, x, centers,
                        reconstruct=method != "DEC", epochs=args.cluster_epochs, batch_size=args.batch_size,
                        learning_rate=args.learning_rate, gamma=args.gamma, seed=seed,
                        target_interval=args.target_interval,
                        brb_interval=args.brb_interval if method == "IDEC_BRB" else 0, brb_alpha=args.brb_alpha)
                fit_seconds = time.perf_counter()-start
                scores = evaluate(y, labels)
                row = {"method":method,"seed":seed, **scores,"pretrain_seconds":pretrain_seconds,
                       "initialization_seconds":initialization_seconds,
                       "fit_seconds":fit_seconds,"standalone_seconds":pretrain_seconds+initialization_seconds+fit_seconds,
                       "nonempty_clusters":len(np.unique(labels)),"samples":len(x),
                       "sha256_training_X":settings["sha256_training_X"]}
                all_rows.append(row)
                labels_by_method[method].append((seed, labels.copy()))
                if seed == args.seeds[0]:
                    representatives[method] = (z.copy(), labels.copy())
                predictions = pd.DataFrame({"sample_id":indices,"label_evaluation_only":y,"cluster":labels})
                predictions.to_csv(out/"predictions"/f"{method}_seed{seed}.csv", index=False)
                write_rows(out/"traces"/f"{method}_seed{seed}.csv", trace)
                np.savez_compressed(out/"models"/f"{method}_seed{seed}.npz", **model.params, centers=centers)
                write_rows(out/"runs.csv", all_rows)
                print(f"  {method:<12} ACC={scores['acc']:.4f} NMI={scores['nmi']:.4f} ARI={scores['ari']:.4f} fit={fit_seconds:.2f}s clusters={row['nonempty_clusters']}", flush=True)
    runs = pd.DataFrame(all_rows)
    summary_rows, pair_rows = [], []
    for method in args.methods:
        rows = runs[runs.method == method]
        record = {"method":method,"n_runs":len(rows)}
        for key in ["acc","nmi","ari","standalone_seconds"]:
            record[key+"_mean"] = float(rows[key].mean())
            record[key+"_std"] = float(rows[key].std(ddof=1)) if len(rows)>1 else float("nan")
        pairs = []
        for (seed_a, a), (seed_b, b) in combinations(labels_by_method[method], 2):
            value = float(adjusted_rand_score(a,b))
            pairs.append(value)
            pair_rows.append({"method":method,"seed_a":seed_a,"seed_b":seed_b,"pairwise_ari":value})
        record.update({"pairwise_ari_mean":float(np.mean(pairs)) if pairs else float("nan"),
                       "pairwise_ari_std":float(np.std(pairs,ddof=1)) if len(pairs)>1 else float("nan"),
                       "n_pairs":len(pairs)})
        summary_rows.append(record)
    summary = pd.DataFrame(summary_rows)
    summary.to_csv(out/"summary.csv", index=False, encoding="utf-8-sig")
    write_rows(out/"pairwise_ari.csv", pair_rows)
    plot_results(out, runs, summary, representatives, x, y, args.seeds, settings["dataset_name"],
                 digit_images=args.data.resolve() == (ROOT/"data"/"digits_1797.npz").resolve())
    columns = ["method","acc_mean","acc_std","nmi_mean","ari_mean","pairwise_ari_mean"]
    print("\n"+summary[columns].to_string(index=False), flush=True)
    print(f"\nSaved results: {out}", flush=True)


if __name__ == "__main__":
    main()
