"""Label-free DCSS RBF-width diagnostics; does not train or select by accuracy.

Reads only X, autoencoder checkpoints and K-means initialization. The proposed
RMS widths use unsupervised initial assignments. Main experiment is untouched.
"""
from pathlib import Path
import argparse
from datetime import datetime,timezone
import json
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from threadpoolctl import threadpool_limits
from src.models import Autoencoder,reconstruct_loss_and_gradient
from src.dcss import rbf_assignments,dcss_loss_and_gradients


def quantiles(values):
    keys = ["min","p10","median","p90","p99","max"]
    return {key:float(value) for key,value in zip(keys,np.quantile(values,[0,.1,.5,.9,.99,1]))}


def describe(z,centers,widths):
    squared = ((z[:,None,:]-centers[None,:,:])**2).sum(axis=2)
    phi = np.exp(-squared/widths[None,:]**2)
    q = rbf_assignments(z,centers,np.log(widths),.25)
    entropy = -np.sum(q*np.log(q+1e-10),axis=1)
    ordered = np.sort(q,axis=1)
    maximum_phi = phi.max(axis=1)
    return {
        "widths":widths.tolist(),"width_summary":quantiles(widths),
        "max_gaussian_activation":quantiles(maximum_phi),
        "fraction_max_phi_below_1e-8":float(np.mean(maximum_phi<1e-8)),
        "fraction_max_phi_below_1e-3":float(np.mean(maximum_phi<1e-3)),
        "max_assignment_probability":quantiles(q.max(axis=1)),
        "mean_max_assignment_probability":float(np.mean(q.max(axis=1))),
        "mean_top_two_probability_margin":float(np.mean(ordered[:,-1]-ordered[:,-2])),
        "mean_entropy_nats":float(np.mean(entropy)),
        "mean_entropy_normalized_logK":float(np.mean(entropy)/np.log(len(centers))),
        "fraction_max_q_within_0.001_of_uniform":float(np.mean(q.max(axis=1)-1/len(centers)<.001)),
        "nonempty_argmax_clusters":int(len(np.unique(q.argmax(axis=1))))
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results",type=Path,default=Path("results/timeline_20261013"))
    parser.add_argument("--seed",type=int,default=0)
    parser.add_argument("--output",type=Path,default=Path("checks/dcss_width_diagnostics.json"))
    args = parser.parse_args()
    config = json.loads((args.results/"config.json").read_text(encoding="utf-8"))
    # Intentionally do not access y in the data bundle.
    with np.load(config["data"],allow_pickle=False) as data:
        x = np.asarray(data["X"],dtype=np.float64)
    sample_indices = np.load(args.results/"sample_indices.npy",allow_pickle=False)
    x = x[sample_indices]
    with np.load(args.results/"models"/f"pretrain_seed{args.seed}.npz",allow_pickle=False) as checkpoint:
        model = Autoencoder(x.shape[1],config["latent_dim"],args.seed)
        model.params.update({key:checkpoint[key].copy() for key in model.params})
    with np.load(args.results/"models"/f"initialization_seed{args.seed}.npz",allow_pickle=False) as checkpoint:
        centers = checkpoint["centers"].copy()
    z = model.encode(x)
    squared = ((z[:,None,:]-centers[None,:,:])**2).sum(axis=2)
    nearest = squared.argmin(axis=1)
    within = squared[np.arange(len(z)),nearest]
    global_rms = np.sqrt(within.mean())
    per_cluster_rms = np.asarray([np.sqrt(within[nearest==cluster].mean())
        if np.any(nearest==cluster) else global_rms for cluster in range(len(centers))])
    # RMS can only vanish for exact duplicate embeddings; use a defined floor.
    global_rms = max(float(global_rms),1e-12)
    per_cluster_rms = np.maximum(per_cluster_rms,1e-12)
    widths = {"source_sigma_1":np.ones(len(centers)),
        "global_within_cluster_rms":np.full(len(centers),global_rms),
        "per_cluster_within_rms":per_cluster_rms}
    subset = np.sort(np.random.default_rng(42).choice(len(x),min(128,len(x)),replace=False))
    _,reconstruction,cache = model.forward(x[subset])
    _,reconstruction_gradient = reconstruct_loss_and_gradient(reconstruction,x[subset])
    reconstruction_grads = model.backward(cache,reconstruction_gradient)
    variants = {}
    for name,width in widths.items():
        trial = model.clone()
        trial.params["log_sigmas"] = np.log(width)
        result = describe(z,centers,width)
        components,grads,grad_centers = dcss_loss_and_gradients(trial,x[subset],centers)
        encoder_keys = [f"{prefix}{layer}" for layer in range(3) for prefix in ("W","b")]
        result.update({"gradient_probe_samples":len(subset),"loss_components":components,
            "centers_gradient_norm":float(np.linalg.norm(grad_centers)),
            "log_sigmas_gradient_norm":float(np.linalg.norm(grads["log_sigmas"])),
            "clustering_only_encoder_gradient_norm":float(np.sqrt(sum(
                np.sum((grads[key]-reconstruction_grads[key])**2) for key in encoder_keys)))})
        variants[name] = result
    final_path = args.results/"models"/f"DCSS_seed{args.seed}.npz"
    final = None
    if final_path.exists():
        with np.load(final_path,allow_pickle=False) as checkpoint:
            trained = model.clone()
            trained.params.update({key:checkpoint[key].copy() for key in model.params})
            trained_centers = checkpoint["centers"]
            trained_widths = np.exp(checkpoint["log_sigmas"])
            final = describe(trained.encode(x),trained_centers,trained_widths)
    report = {"created_utc":datetime.now(timezone.utc).isoformat(),"seed":args.seed,
        "n_samples":len(x),"n_clusters":len(centers),"temperature":.25,
        "uses_ground_truth":False,"main_experiment_modified":False,
        "scope":"label-free diagnostics only; no accuracy, tuning or training",
        "pretrained_latent_norm":quantiles(np.linalg.norm(z,axis=1)),
        "pretrained_coordinate_range":quantiles(z.ravel()),
        "nearest_center_squared_distance":quantiles(within),
        "all_center_squared_distance":quantiles(squared.ravel()),
        "width_estimator":"sqrt(mean nearest-center squared Euclidean distance), global or within each initial K-means cluster",
        "initialization_variants":variants,"existing_final_source_checkpoint":final}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    print(json.dumps({name:{key:value[key] for key in (
        "mean_max_assignment_probability","mean_entropy_normalized_logK",
        "fraction_max_phi_below_1e-3","centers_gradient_norm",
        "clustering_only_encoder_gradient_norm")} for name,value in variants.items()},indent=2))
    print(f"Saved label-free diagnostics: {args.output}")


if __name__ == "__main__":
    with threadpool_limits(limits=1):
        main()
