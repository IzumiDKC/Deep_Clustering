"""Finite differences and source-objective checks for the DECRA code adaptation.

Run: python checks/check_decra.py --output checks/verification_decra.json
No original PyTorch environment or author checkpoint is required or claimed.
"""
from pathlib import Path
import argparse
from datetime import datetime, timezone
import json
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from src.models import Autoencoder,assignments,target_distribution,fit_kmeans
from src.decra import initialize_adaptive_layer,decode,decra_loss_and_gradients,train_decra


def independent_source_loss(model,x,centers,p):
    """Translate the public fine-tune objective directly into scalar NumPy ops."""
    z = x
    for layer in range(3):
        z = z @ model.params[f"W{layer}"] + model.params[f"b{layer}"]
        if layer < 2:
            z = np.maximum(z,0)
    def reference_decoder(latent):
        hidden = latent
        for layer in range(3,6):
            hidden = hidden @ model.params[f"W{layer}"] + model.params[f"b{layer}"]
            hidden = 1/(1+np.exp(-hidden)) if layer == 5 else np.maximum(hidden,0)
        return hidden
    main = reference_decoder(z)
    adaptive = z @ model.params["W_residual"] + model.params["b_residual"]
    auxiliary = reference_decoder(adaptive)
    distance = ((z[:,None,:]-centers[None,:,:])**2).sum(axis=2)
    q = 1/(1+distance)
    q /= q.sum(axis=1,keepdims=True)
    return 2*np.mean((main-x)**2) + .6*np.mean((auxiliary-main)**2) + .1*np.mean(p*(np.log(p)-np.log(q)))


def finite_difference(function,array,index,analytic):
    original = array[index]
    try:
        array[index] = original+1e-5
        plus = function()
        array[index] = original-1e-5
        minus = function()
    finally:
        array[index] = original
    numeric = (plus-minus)/(2e-5)
    relative = abs(numeric-analytic)/max(1e-6,abs(numeric)+abs(analytic))
    if relative > 2e-4:
        raise AssertionError(f"gradient {index}: numerical={numeric}, analytic={analytic}, relative={relative}")
    return relative


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path)
    args = parser.parse_args()
    rng = np.random.default_rng(42)
    x = rng.uniform(.1,.9,size=(7,5))
    model = Autoencoder(5,3,42)
    backbone = {key:value.copy() for key,value in model.params.items()}
    initial_embedding = model.encode(x)
    initialize_adaptive_layer(model,42)
    for key,value in backbone.items():
        np.testing.assert_array_equal(model.params[key],value)
    np.testing.assert_array_equal(model.encode(x),initial_embedding)
    replay = Autoencoder(5,3,42)
    initialize_adaptive_layer(replay,42)
    for key in model.params:
        np.testing.assert_array_equal(model.params[key],replay.params[key])

    centers = rng.normal(size=(3,3))
    p = target_distribution(assignments(model.encode(x),centers))
    components,grads,gc = decra_loss_and_gradients(model,x,centers,p)
    np.testing.assert_allclose(components["total"],independent_source_loss(model,x,centers,p),rtol=1e-12,atol=1e-14)
    np.testing.assert_allclose(components["clustering"]*len(centers),components["kl_batchmean"])
    z,reconstruction,_ = model.forward(x)
    decoded,_ = decode(model,z)
    np.testing.assert_allclose(decoded,reconstruction,rtol=1e-12,atol=1e-14)

    scalar_loss = lambda: independent_source_loss(model,x,centers,p)
    errors = []
    counts = {"backbone":0,"adaptive":0,"centers":0}
    for key,value in model.params.items():
        indices = list(np.ndindex(value.shape)) if "residual" in key else [
            tuple(int(rng.integers(dim)) for dim in value.shape) for _ in range(8)]
        for index in indices:
            errors.append(finite_difference(scalar_loss,value,index,grads[key][index]))
            counts["adaptive" if "residual" in key else "backbone"] += 1
    for index in np.ndindex(centers.shape):
        errors.append(finite_difference(scalar_loss,centers,index,gc[index]))
        counts["centers"] += 1

    # Shared initialization and complete snapshots survive the training path.
    init_model = Autoencoder(5,3,9)
    _, initial_centers = fit_kmeans(init_model.encode(x),3,9)
    trained, replay = init_model.clone(),init_model.clone()
    train_kwargs = dict(epochs=3,batch_size=4,learning_rate=.001,gamma=.1,seed=9,target_interval=2)
    result = train_decra(trained,x,initial_centers.copy(),**train_kwargs)
    again = train_decra(replay,x,initial_centers.copy(),**train_kwargs)
    labels,z,final_centers,history = result
    np.testing.assert_array_equal(labels,assignments(z,final_centers).argmax(1))
    np.testing.assert_array_equal(labels,again[0])
    np.testing.assert_array_equal(final_centers,again[2])
    for key in trained.params:
        np.testing.assert_array_equal(trained.params[key],replay.params[key])
        assert np.isfinite(trained.params[key]).all()
    assert len(history) == 3 and all(np.isfinite(row["total"]) for row in history)
    p_last = target_distribution(assignments(again[1],again[2]))
    final_components,_,_ = decra_loss_and_gradients(trained,x,final_centers,p_last)
    assert np.isfinite(final_components["total"])
    assert not np.array_equal(trained.params["W_residual"],model.params["W_residual"])
    report = {
        "created_utc":datetime.now(timezone.utc).isoformat(),
        "status":"passed","python":sys.version,"numpy":np.__version__,
        "gradient_checks":len(errors),"gradient_groups":counts,
        "max_gradient_relative_error":max(errors),
        "objective":"2*MSE(main,X)+0.6*MSE(auxiliary,main)+0.1*KL_mean(N*K)",
        "checks":["independent scalar source objective","two decoder branches, no detach",
            "affine adaptive layer and centroid gradients","shared decoder forward parity",
            "backbone unchanged on adaptive initialization","deterministic full training",
            "finite parameters and losses","prediction matches final Q"],
        "scope":"DECRA public-code mechanism adapted to shared NumPy backbone; not original author execution",
        "author_code":"https://github.com/lml-mengli/DECRA/blob/main/decra.py"
    }
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    print(f"PASS: DECRA {len(errors)} finite-difference gradients, maximum relative error {max(errors):.3e}")
    print("PASS: source objective, forward parity, unchanged initialization and deterministic training")


if __name__ == "__main__":
    main()
