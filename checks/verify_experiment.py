"""Independently recompute metrics and verify shared-data experiment artifacts."""
from pathlib import Path
import argparse
import hashlib
import json
import sys

import numpy as np
import pandas as pd
from sklearn.metrics import adjusted_rand_score
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.evaluation import evaluate
from src.models import Autoencoder, assignments, squared_distances


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--data", type=Path, default=ROOT/"data"/"digits_1797.npz")
    parser.add_argument("--reference", type=Path, default=ROOT/"archive/reference_results")
    args = parser.parse_args()
    out = args.results.resolve()
    config = json.loads((out/"config.json").read_text(encoding="utf-8"))
    runs = pd.read_csv(out/"runs.csv")
    summary = pd.read_csv(out/"summary.csv")
    indices = np.load(out/"sample_indices.npy", allow_pickle=False)
    with np.load(args.data, allow_pickle=False) as data:
        x, y = data["X"][indices].astype(np.float64), data["y"][indices]
    x_hash = hashlib.sha256(np.ascontiguousarray(x).tobytes()).hexdigest()
    assert hashlib.sha256(args.data.read_bytes()).hexdigest() == config["sha256_data"]
    assert x_hash == config["sha256_training_X"]
    assert hashlib.sha256(indices.tobytes()).hexdigest() == config["sha256_sample_indices"]
    assert not runs.duplicated(["method", "seed"]).any()
    assert len(runs) == len(config["methods"])*len(config["seeds"])
    assert set(runs.method) == set(config["methods"])
    assert set(runs.seed) == set(config["seeds"])
    assert (runs.samples == len(x)).all() and (runs.sha256_training_X == x_hash).all()
    assert np.isfinite(runs[["acc","nmi","ari","standalone_seconds"]]).all().all()
    for source, expected_hash in config.get("source_sha256", {}).items():
        location = config.get("source_locations", {}).get(source, source)
        assert hashlib.sha256((ROOT/location).read_bytes()).hexdigest() == expected_hash, f"Training source changed: {source}"
    predictions, differences = {}, []
    with threadpool_limits(limits=1):
        for row in runs.itertuples():
            predictions_file = out/"predictions"/f"{row.method}_seed{row.seed}.csv"
            frame = pd.read_csv(predictions_file)
            np.testing.assert_array_equal(frame.sample_id, indices)
            np.testing.assert_array_equal(frame.label_evaluation_only, y)
            labels = frame.cluster.to_numpy()
            predictions[row.method, row.seed] = labels
            for metric, actual in evaluate(y, labels).items():
                differences.append(abs(actual-getattr(row, metric)))
                np.testing.assert_allclose(actual, getattr(row,metric), atol=1e-12, rtol=0)
            model = Autoencoder(x.shape[1], config["latent_dim"], row.seed)
            with np.load(out/"models"/f"{row.method}_seed{row.seed}.npz", allow_pickle=False) as saved:
                model.params = {key:saved[key].copy() for key in saved.files if key != "centers"}
                centers = saved["centers"].copy()
            latent = model.encode(x)
            if row.method == "DCSS":
                from src.dcss import rbf_assignments
                recomputed = rbf_assignments(latent,centers,model.params["log_sigmas"],
                                             temperature=config["dcss_temperature"]).argmax(1)
            else:
                recomputed = (squared_distances(latent,centers).argmin(1) if row.method in ["AE_KMeans","DCN"]
                              else assignments(latent,centers).argmax(1))
            np.testing.assert_array_equal(recomputed, labels)
            assert row.nonempty_clusters == len(np.unique(labels))
            np.testing.assert_allclose(row.standalone_seconds,
                row.pretrain_seconds+row.initialization_seconds+row.fit_seconds, atol=1e-9)
            if row.method == "AE_KMeans":
                with np.load(out/"models"/f"pretrain_seed{row.seed}.npz", allow_pickle=False) as pretrained:
                    for key, value in model.params.items():
                        np.testing.assert_array_equal(value, pretrained[key])
                with np.load(out/"models"/f"initialization_seed{row.seed}.npz", allow_pickle=False) as initial:
                    np.testing.assert_array_equal(centers, initial["centers"])
                    np.testing.assert_array_equal(labels, initial["labels"])
            else:
                trace = pd.read_csv(out/"traces"/f"{row.method}_seed{row.seed}.csv")
                assert len(trace) == config["cluster_epochs"]
                assert np.isfinite(trace[["reconstruction","clustering","total"]]).all().all()
                expected_resets = list(range(1+config["brb_interval"], config["cluster_epochs"]+1,
                                             config["brb_interval"])) if row.method == "IDEC_BRB" else []
                assert trace.loc[trace.reset == 1, "epoch"].tolist() == expected_resets
        for row in summary.itertuples():
            subset = runs[runs.method == row.method]
            assert row.n_runs == len(subset)
            for metric in ["acc","nmi","ari","standalone_seconds"]:
                np.testing.assert_allclose(getattr(row,metric+"_mean"), subset[metric].mean(), atol=1e-12)
                np.testing.assert_allclose(getattr(row,metric+"_std"), subset[metric].std(ddof=1), atol=1e-12, equal_nan=True)
        pair_file = out/"pairwise_ari.csv"
        pair_count = 0
        if pair_file.exists():
            pairs = pd.read_csv(pair_file)
            pair_count = len(pairs)
            for row in pairs.itertuples():
                actual = adjusted_rand_score(predictions[row.method,row.seed_a], predictions[row.method,row.seed_b])
                np.testing.assert_allclose(actual,row.pairwise_ari,atol=1e-12)
            for row in summary.itertuples():
                values = pairs.loc[pairs.method == row.method,"pairwise_ari"]
                assert row.n_pairs == len(values)
                np.testing.assert_allclose(row.pairwise_ari_mean,values.mean(),atol=1e-12)
                np.testing.assert_allclose(row.pairwise_ari_std,values.std(ddof=1),atol=1e-12,equal_nan=True)
        expected_pairs = len(config["methods"])*len(config["seeds"])*(len(config["seeds"])-1)//2
        assert pair_count == expected_pairs
    result = {"status":"passed", "runs_verified":len(runs),"dataset_samples":len(x),
              "same_training_data_all_methods":True,"sha256_training_X":x_hash,
              "metrics_recomputed_from_predictions":True,"predictions_recomputed_from_saved_models":True,
              "max_metric_error":max(differences),"seed_pairs_verified":pair_count,
              "summary_and_sample_std_verified":True,"brb_reset_schedule_verified":True,
              "training_source_hashes_verified":bool(config.get("source_sha256")),
              "original_training_source_snapshots":config.get("source_locations", {}),
              "original_authors_code":"not executed; independent NumPy demonstration"}
    reference = args.reference/"runs.csv"
    if reference.exists():
        reference_config_file = args.reference/"config.json"
        reference_config = json.loads(reference_config_file.read_text(encoding="utf-8")) if reference_config_file.exists() else {}
        protocol_keys = ["pretrain_epochs","cluster_epochs","batch_size","learning_rate","gamma",
                         "latent_dim","clusters","target_interval","limit"]
        mismatches = [key for key in protocol_keys if reference_config.get(key) != config.get(key)]
        if reference_config.get("sha256_training_X") and reference_config["sha256_training_X"] != x_hash:
            mismatches.append("sha256_training_X")
        if mismatches:
            result["reference_comparison"] = {"skipped":True,"different_protocol_fields":mismatches}
        else:
            old = pd.read_csv(reference)
            merged = runs.merge(old,on=["method","seed"],suffixes=("_local","_reference"))
            result["reference_comparison"] = {"matched_runs":len(merged),
                "max_absolute_metric_difference":{m:float((merged[m+"_local"]-merged[m+"_reference"]).abs().max())
                                                   for m in ["acc","nmi","ari"]} if len(merged) else {},
                "note":"Only common methods with matching training settings; timing rules may differ."}
    (out/"verification.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__ == "__main__":
    main()
