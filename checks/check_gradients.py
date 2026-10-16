"""Finite-difference and protocol checks for the NumPy clustering models.

Run from project root: python checks/check_gradients.py
This checks the mathematical derivatives, not the reported clustering ranking.
"""
from pathlib import Path
import argparse
from datetime import datetime, timezone
import json
import sys
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from src.models import (Adam, Autoencoder, assignments, target_distribution,
                        kl_loss_and_gradients, reconstruct_loss_and_gradient,
                        squared_distances, train_dec, train_dcn)
from src.evaluation import evaluate, mapped_labels


def check_value(function, array, index, analytic, name, eps=1e-5):
    saved = array[index]
    array[index] = saved + eps
    plus = function()
    array[index] = saved - eps
    minus = function()
    array[index] = saved
    numeric = (plus-minus)/(2*eps)
    error = abs(numeric-analytic) / max(1e-6, abs(numeric)+abs(analytic))
    if error > 2e-4:
        raise AssertionError(f"{name}: numerical={numeric}, analytic={analytic}, error={error}")
    return error


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Optional JSON evidence from this execution")
    args = parser.parse_args()
    rng = np.random.default_rng(7)
    z, centers = rng.normal(size=(5,3)), rng.normal(size=(3,3))
    p = target_distribution(assignments(z, centers))
    _, gz, gc = kl_loss_and_gradients(z, centers, p)
    errors = []
    loss = lambda: kl_loss_and_gradients(z, centers, p)[0]
    for index in np.ndindex(z.shape):
        errors.append(check_value(loss,z,index,gz[index],"DEC z"))
    for index in np.ndindex(centers.shape):
        errors.append(check_value(loss,centers,index,gc[index],"DEC centers"))
    x = rng.uniform(.1,.9,size=(5,4))
    model = Autoencoder(4,3,7)
    z, reconstructed, cache = model.forward(x)
    _, gx = reconstruct_loss_and_gradient(reconstructed,x)
    centers = rng.normal(size=(3,3))
    p = target_distribution(assignments(z,centers))
    _, gz, _ = kl_loss_and_gradients(z,centers,p)
    grads = model.backward(cache,gx,.1*gz)
    def joint_loss():
        latent, rec, _ = model.forward(x)
        return reconstruct_loss_and_gradient(rec,x)[0] + .1*kl_loss_and_gradients(latent,centers,p)[0]
    for key in model.params:
        for _ in range(8):
            index = tuple(int(rng.integers(size)) for size in model.params[key].shape)
            errors.append(check_value(joint_loss,model.params[key],index,grads[key][index],key))
    # DCN differentiates with hard assignments and centroids held fixed.
    # This independently checks its distortion scaling through all AE layers.
    hard_labels = squared_distances(z, centers).argmin(1)
    weight = .01
    grad_dcn = weight*2.0*(z-centers[hard_labels])/len(x)
    grads = model.backward(cache, gx, grad_dcn)
    def dcn_loss():
        latent, rec, _ = model.forward(x)
        distortion = np.mean(np.sum((latent-centers[hard_labels])**2, axis=1))
        return reconstruct_loss_and_gradient(rec,x)[0] + weight*distortion
    for key in model.params:
        for _ in range(8):
            index = tuple(int(rng.integers(size)) for size in model.params[key].shape)
            errors.append(check_value(dcn_loss,model.params[key],index,grads[key][index],f"DCN {key}"))
    # ACC must account for arbitrary cluster-label permutation.
    true = np.array([0,0,1,1,2,2])
    pred = np.array([2,2,0,0,1,1])
    assert all(abs(value-1)<1e-12 for value in evaluate(true,pred).values())
    # When K exceeds the number of classes, unmatched clusters must not
    # accidentally match a true class named -1 (a collision in the old code).
    true_negative = np.array([-1,-1,-1,-1])
    split_pred = np.array([0,0,1,1])
    mapped, mapping = mapped_labels(true_negative,split_pred)
    assert len(mapping) == 1 and np.count_nonzero(mapped == -1) == 2
    assert abs(evaluate(true_negative,split_pred)["acc"]-.5) < 1e-12
    # Missing predicted clusters still use an optimal one-to-one match.
    assert abs(evaluate(np.array([0,0,1,1,2,2]),np.array([0,0,1,1,1,1]))["acc"]-2/3) < 1e-12
    for bad_true, bad_pred in [([], []), ([0,1], [0]), ([[0]], [[0]])]:
        try:
            evaluate(np.asarray(bad_true),np.asarray(bad_pred))
        except ValueError:
            pass
        else:
            raise AssertionError("Invalid label shape must fail clearly")
    # BRB must keep decoder parameters and apply the advertised interpolation.
    model = Autoencoder(4,3,9)
    before = {key:value.copy() for key,value in model.params.items()}
    trial_rng = np.random.default_rng(19)
    fresh_seed = int(trial_rng.integers(2**31-1))
    fresh = Autoencoder(4,3,fresh_seed)
    model.soft_reset_encoder(np.random.default_rng(19),.8)
    for key in model.params:
        expected = .8*before[key]+.2*fresh.params[key] if int(key[1:])<3 else before[key]
        np.testing.assert_allclose(model.params[key],expected)
    # A reset centroid must start Adam at step 1, while network moments persist.
    optimizer = Adam()
    params = {"centers":np.ones((2,3)), "W0":np.ones((4,3))}
    optimizer.update(params,{key:np.ones_like(value) for key,value in params.items()})
    network_momentum = optimizer.m["W0"].copy()
    optimizer.reset("centers")
    assert all("centers" not in state for state in (optimizer.m,optimizer.v,optimizer.steps))
    np.testing.assert_array_equal(optimizer.m["W0"],network_momentum)
    optimizer.update(params,{"centers":np.ones_like(params["centers"])})
    assert optimizer.steps["centers"] == 1 and optimizer.steps["W0"] == 1
    # Exercise actual training paths, including reset epochs and centroid resets.
    small_x = rng.uniform(.1,.9,size=(12,4))
    init_model = Autoencoder(4,3,13)
    initial_centers = init_model.encode(small_x)[[0,3,8]].copy()
    dec_model = init_model.clone()
    decoder_before = {key:value.copy() for key,value in dec_model.params.items() if int(key[1:]) >= 3}
    train_dec(dec_model,small_x,initial_centers.copy(),reconstruct=False,epochs=2,
              batch_size=5,learning_rate=.001,gamma=.1,seed=13)
    for key, value in decoder_before.items():
        np.testing.assert_array_equal(dec_model.params[key],value)
    original_reset, reset_calls = Adam.reset, []
    def recorded_reset(self,key):
        reset_calls.append(key)
        original_reset(self,key)
    with patch.object(Adam,"reset",recorded_reset):
        _, _, _, brb_history = train_dec(init_model.clone(),small_x,initial_centers.copy(),
            reconstruct=True,epochs=5,batch_size=5,learning_rate=.001,gamma=.1,
            seed=13,target_interval=5,brb_interval=2,brb_alpha=.8)
    assert [row["epoch"] for row in brb_history if row["reset"]] == [3,5]
    assert reset_calls == ["centers","centers"]
    dcn_model = init_model.clone()
    labels, latent, final_centers, dcn_history = train_dcn(dcn_model,small_x,
        initial_centers.copy(),epochs=2,batch_size=5,learning_rate=.001,dcn_weight=.01,seed=13)
    expected_distortion = np.mean(np.sum((latent-final_centers[labels])**2,axis=1))
    np.testing.assert_allclose(dcn_history[-1]["clustering"],expected_distortion)
    print(f"PASS: {len(errors)} finite-difference gradients; largest relative error {max(errors):.3e}")
    print("PASS: clustering metrics, BRB interpolation/schedule/Adam reset, DEC decoder, DCN trace")
    if args.output:
        evidence = {
            "created_utc":datetime.now(timezone.utc).isoformat(),
            "python":sys.version,"numpy":np.__version__,"status":"passed",
            "gradient_checks":len(errors),"max_gradient_relative_error":max(errors),
            "gradient_groups":{"DEC_embedding":15,"DEC_centers":9,"IDEC_network":96,"DCN_network":96},
            "semantic_checks":["permuted cluster labels","negative labels with unmatched clusters",
                "fewer clusters than classes","invalid metric input","BRB encoder interpolation",
                "Adam centroid reset","DEC decoder unchanged","BRB reset epochs and center moments",
                "DCN final-epoch nearest-center distortion"],
            "scope":"independent educational NumPy implementation; original authors' code not executed"
        }
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(evidence,indent=2,ensure_ascii=False),encoding="utf-8")


if __name__ == "__main__":
    main()
