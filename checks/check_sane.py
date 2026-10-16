"""Check the SANE-inspired NumPy adaptation on the bundled common dataset."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np

from src.models import Autoencoder, fit_kmeans, pretrain
from src.sane import density_aware_centers, stable_samples, train_sane_idec


def main():
    with np.load(ROOT/"data"/"digits_1797.npz", allow_pickle=False) as bundle:
        x = bundle["X"][:250]
    model = Autoencoder(x.shape[1],10,0)
    pretrain(model,x,epochs=3,batch_size=64,learning_rate=1e-3,seed=0)
    labels,centers = fit_kmeans(model.encode(x),10,0)
    refined = density_aware_centers(model.encode(x),labels,centers,alpha=2.0,k=10)
    assert refined.shape == centers.shape and np.isfinite(refined).all()
    assert np.linalg.norm(refined-centers) > 0
    score = np.array([[.2,.4,.7,.8],[.4,.5,.6,.8],[.2,.6,.5,.8]])
    pseudo = np.array([[0,0,0,0],[0,0,1,0],[0,0,1,0]])
    selected = stable_samples(score,pseudo,epsilon=.1,min_retain_fraction=.25)
    np.testing.assert_array_equal(selected,[True,False,True,False])
    candidate_a = model.clone()
    candidate_b = model.clone()
    first = train_sane_idec(candidate_a,x,refined.copy(),epochs=4,batch_size=64,
                            learning_rate=1e-3,gamma=.1,seed=0)
    second = train_sane_idec(candidate_b,x,refined.copy(),epochs=4,batch_size=64,
                             learning_rate=1e-3,gamma=.1,seed=0)
    np.testing.assert_array_equal(first[0],second[0])
    np.testing.assert_allclose(first[2],second[2],rtol=0,atol=0)
    assert len(first[3]) == 4
    assert all(np.isfinite(row["total"]) and .25 <= row["retained_fraction"] <= 1
               for row in first[3])
    assert all(row["retained_fraction"] == 1 for row in first[3][:2])
    result = {"status":"passed", "dachi_finite_and_changes_centers":True,
              "dss_expected_selection":True, "same_seed_deterministic":True,
              "nonempty_training_batches":True, "samples_checked":len(x),
              "scope":"SANE-inspired IDEC adaptation; no original-author reproduction"}
    (ROOT/"checks"/"verification_sane.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    print("PASS: DACHI finite, DSS selection, same-seed deterministic training, nonempty batches")


if __name__ == "__main__":
    main()
