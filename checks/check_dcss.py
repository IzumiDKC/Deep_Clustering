"""Source-forward parity, full finite differences and training checks for DCSS."""
from pathlib import Path
import argparse
from datetime import datetime,timezone
import json
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from scipy.special import softmax
from threadpoolctl import threadpool_limits
from src.models import Autoencoder,fit_kmeans
from src.dcss import (soft_silhouette_loss_and_gradients,rbf_assignments,
                      dcss_loss_and_gradients,train_dcss,_batch_indices)


def source_silhouette(z,q,normalization="source"):
    distances = np.linalg.norm(z[:,None,:]-z[None,:,:],axis=2)
    alpha = distances @ q
    n,k = alpha.shape
    if normalization == "paper":
        alpha /= q.sum(axis=0,keepdims=True)-q
    # Literal translation of Objectives.py, including the mask/view/reversal.
    repeated = np.repeat(alpha[:,:,None],k,axis=2)
    mask = ~np.eye(k,dtype=bool)
    without_self = repeated[:,mask].reshape(n,k-1,k)
    beta = without_self.min(axis=1)[:,::-1]
    conditional = (beta-alpha)/np.maximum(alpha,beta)
    return float(np.mean(np.sum(q*conditional,axis=1)))


def independent_total(model,x,centers):
    z,reconstruction,_ = model.forward(x)
    difference = z[:,None,:]-centers[None,:,:]
    gaussian = np.exp(-np.sum(difference**2,axis=2)/np.exp(2*model.params["log_sigmas"]))
    q = softmax(gaussian/.25,axis=1)
    entropy = np.mean(-np.sum(q*np.log(q+1e-10),axis=1))/np.log(2)
    return np.mean((reconstruction-x)**2)+.01*(1-source_silhouette(z,q))+.01*entropy


def check_gradient(function,array,index,analytic):
    saved = array[index]
    try:
        array[index] = saved+1e-5
        plus = function()
        array[index] = saved-1e-5
        minus = function()
    finally:
        array[index] = saved
    numeric = (plus-minus)/(2e-5)
    error = abs(numeric-analytic)/max(1e-6,abs(numeric)+abs(analytic))
    if error > 2e-4:
        raise AssertionError(f"Gradient {index}: numerical={numeric}, analytic={analytic}, relative={error}")
    return error


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path)
    args = parser.parse_args()
    rng = np.random.default_rng(31)
    errors,counts = [],{}
    z = rng.normal(size=(7,3))
    q = softmax(rng.normal(size=(7,4)),axis=1)
    for normalization in ("source","paper"):
        loss,gz,gq = soft_silhouette_loss_and_gradients(z,q,distance_normalization=normalization)
        np.testing.assert_allclose(loss,1-source_silhouette(z,q,normalization),rtol=1e-12,atol=1e-14)
        scalar = lambda: 1-source_silhouette(z,q,normalization)
        counts[f"{normalization}_silhouette_z"] = z.size
        counts[f"{normalization}_silhouette_Q"] = q.size
        for index in np.ndindex(z.shape):
            errors.append(check_gradient(scalar,z,index,gz[index]))
        for index in np.ndindex(q.shape):
            errors.append(check_gradient(scalar,q,index,gq[index]))
    # Check source's unusual masking construction for several cluster counts.
    for k in (2,3,5,10):
        qq = softmax(rng.normal(size=(7,k)),axis=1)
        value,_,_ = soft_silhouette_loss_and_gradients(z,qq)
        np.testing.assert_allclose(value,1-source_silhouette(z,qq),rtol=1e-12,atol=1e-14)

    x = rng.uniform(.1,.9,size=(7,5))
    model = Autoencoder(5,3,31)
    model.params["log_sigmas"] = rng.uniform(-.2,.3,size=4)
    centers = rng.normal(size=(4,3))
    components,grads,gc = dcss_loss_and_gradients(model,x,centers)
    np.testing.assert_allclose(components["total"],independent_total(model,x,centers),rtol=1e-12,atol=1e-14)
    scalar = lambda: independent_total(model,x,centers)
    counts["network"] = 0
    counts["RBF_log_sigmas"] = 4
    counts["RBF_centers"] = centers.size
    for key,value in model.params.items():
        indices = list(np.ndindex(value.shape)) if key == "log_sigmas" else [
            tuple(int(rng.integers(dim)) for dim in value.shape) for _ in range(8)]
        for index in indices:
            errors.append(check_gradient(scalar,value,index,grads[key][index]))
            if key != "log_sigmas":
                counts["network"] += 1
    for index in np.ndindex(centers.shape):
        errors.append(check_gradient(scalar,centers,index,gc[index]))

    collapsed_z = np.zeros((4,3))
    loss,gz,gq = soft_silhouette_loss_and_gradients(collapsed_z,np.full((4,4),.25))
    assert loss == 1 and np.isfinite(gz).all() and np.isfinite(gq).all()
    np.testing.assert_allclose(gz,0)
    for n in (2,5,9,13):
        batches = _batch_indices(np.arange(n),4)
        assert all(len(batch)>=2 for batch in batches)
        np.testing.assert_array_equal(np.concatenate(batches),np.arange(n))
    small_x = rng.uniform(.1,.9,size=(13,5))
    init = Autoencoder(5,3,4)
    _,init_centers = fit_kmeans(init.encode(small_x),4,4)
    first,second = init.clone(),init.clone()
    kwargs = dict(epochs=3,batch_size=4,learning_rate=.001,seed=4)
    result = train_dcss(first,small_x,init_centers.copy(),**kwargs)
    repeat = train_dcss(second,small_x,init_centers.copy(),**kwargs)
    labels,latent,centers,history = result
    predicted = rbf_assignments(latent,centers,first.params["log_sigmas"]).argmax(axis=1)
    np.testing.assert_array_equal(labels,predicted)
    np.testing.assert_array_equal(labels,repeat[0])
    np.testing.assert_array_equal(centers,repeat[2])
    for key,value in first.params.items():
        assert np.isfinite(value).all()
        np.testing.assert_array_equal(value,second.params[key])
    expected = 0.
    for batch in _batch_indices(np.arange(len(small_x)),4):
        expected += independent_total(first,small_x[batch],centers)*len(batch)/len(small_x)
    np.testing.assert_allclose(history[-1]["total"],expected,rtol=1e-12,atol=1e-14)
    report = {
        "created_utc":datetime.now(timezone.utc).isoformat(),"status":"passed",
        "python":sys.version,"numpy":np.__version__,"gradient_checks":len(errors),
        "gradient_groups":counts,"max_gradient_relative_error":max(errors),
        "default_objective":"MSE+0.01*(1-softsil_source)+0.01*entropy_bits; Gaussian RBF softmax T=0.25",
        "checks":["literal author mask/view/reversal forward","source and paper silhouette gradients",
            "full network distance and assignment gradients","RBF centroid and log_sigma gradients",
            "zero-distance safety","singleton tail preserves all samples","deterministic training",
            "epoch trace matches post-update evaluation batches","final prediction matches RBF Q"],
        "scope":"DCSS public-code objective on shared NumPy backbone; no original author environment execution"
    }
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    print(f"PASS: DCSS {len(errors)} gradient checks; maximum relative error {max(errors):.3e}")
    print("PASS: literal source forward, RBF, edge cases, deterministic training and epoch trace")


if __name__ == "__main__":
    with threadpool_limits(limits=1):
        main()
