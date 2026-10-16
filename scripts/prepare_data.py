"""Regenerate the bundled UCI Digits subset without an Internet download."""
from pathlib import Path
import json
import hashlib
import numpy as np
import pandas as pd
from sklearn.datasets import load_digits

ROOT = Path(__file__).resolve().parents[1]


def main():
    out = ROOT / "data"
    out.mkdir(exist_ok=True)
    data = load_digits()
    x = (data.data/16.0).astype(np.float64)
    y = data.target.astype(np.int64)
    np.savez_compressed(out / "digits_1797.npz", X=x, y=y)
    frame = pd.DataFrame(data.data.astype(int), columns=[f"pixel_{i:02d}" for i in range(64)])
    frame.insert(0, "sample_id", np.arange(len(y)))
    frame["label_evaluation_only"] = y
    frame.to_csv(out / "digits_1797.csv", index=False)
    metadata = {"dataset": "UCI Optical Recognition of Handwritten Digits test subset via sklearn.load_digits",
                "n_samples": len(y), "n_features": x.shape[1], "image_shape": [8,8],
                "known_n_clusters": 10, "raw_pixel_range": [0,16], "normalization": "X = raw_pixels / 16.0",
                "class_counts": {str(k): int((y == k).sum()) for k in range(10)},
                "sklearn_url": "https://scikit-learn.org/stable/modules/generated/sklearn.datasets.load_digits.html",
                "uci_url": "https://archive.ics.uci.edu/dataset/80/optical+recognition+of+handwritten+digits",
                "doi": "10.24432/C50P49", "creators": ["E. Alpaydin", "C. Kaynak"],
                "dataset_license": "CC BY 4.0", "label_usage": "Evaluation only",
                "sha256_npz": hashlib.sha256((out / "digits_1797.npz").read_bytes()).hexdigest()}
    (out / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved {len(y)} samples to {out}")


if __name__ == "__main__":
    main()
