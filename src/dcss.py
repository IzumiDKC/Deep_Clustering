"""DCSS public-code objective/RBF adapted to the common NumPy autoencoder.

Paper: https://doi.org/10.1007/s10994-026-07026-w (Machine Learning, 2026).
Code: https://github.com/gvardakas/Soft-Silhouette

Defaults follow public Objectives.py/RBF.py/Autoencoder.py: Gaussian RBF,
softmax temperature .25, entropy in bits, and unnormalized D @ Q distances.
The 2026 paper Eq.13 divides D @ Q by cluster membership mass excluding the
current point; this is an explicit selectable variant, NOT the code default.
The shared small AE replaces the authors' BatchNorm/tanh architecture.
"""
from __future__ import annotations

import numpy as np
from scipy.special import softmax
from scipy.spatial.distance import cdist

from .models import Adam,reconstruct_loss_and_gradient


def rbf_assignments(z,centers,log_sigmas,temperature=0.25):
    """Source RBF = exp(-||z-c||^2 / exp(2*log_sigma)); Q=softmax(RBF/T)."""
    if temperature <= 0:
        raise ValueError("Softmax temperature must be positive.")
    difference = z[:,None,:]-centers[None,:,:]
    squared = np.sum(difference*difference,axis=2)
    inv_variance = np.exp(-2*log_sigmas)
    gaussian = np.exp(-squared*inv_variance[None,:])
    return softmax(gaussian/temperature,axis=1)


def soft_silhouette_loss_and_gradients(z,q,*,distance_normalization="source"):
    """Return 1-soft_silhouette and derivatives w.r.t. both z and Q.

    Min/max make this piecewise differentiable, as in PyTorch autograd.
    Exact zero denominators (collapsed embeddings) receive epsilon protection;
    pairwise zero-distance derivative is defined as zero, matching cdist.
    """
    n,k = q.shape
    if n < 2 or k < 2:
        raise ValueError("Soft silhouette needs at least two samples and clusters.")
    if distance_normalization not in ("source","paper"):
        raise ValueError("distance_normalization must be 'source' or 'paper'.")
    distances = cdist(z,z,metric="euclidean")
    numerator = distances @ q
    if distance_normalization == "paper":
        mass = q.sum(axis=0,keepdims=True)-q
        safe_mass = np.maximum(mass,1e-12)
        alpha = numerator/safe_mass
    else:
        alpha = numerator
    other = np.broadcast_to(alpha[:,None,:],(n,k,k)).copy()
    other[:,np.arange(k),np.arange(k)] = np.inf
    nearest_other = other.argmin(axis=2)
    beta = np.take_along_axis(alpha,nearest_other,axis=1)
    denominator = np.maximum(np.maximum(alpha,beta),1e-12)
    silhouette = (beta-alpha)/denominator
    score = float(np.mean(np.sum(q*silhouette,axis=1)))
    grad_q = -silhouette/n
    grad_s = -q/n
    grad_denominator = -grad_s*(beta-alpha)/denominator**2
    grad_alpha = -grad_s/denominator + grad_denominator*((alpha>beta)&(alpha>1e-12))
    grad_beta = grad_s/denominator + grad_denominator*((beta>=alpha)&(beta>1e-12))
    np.add.at(grad_alpha,(np.arange(n)[:,None],nearest_other),grad_beta)
    if distance_normalization == "paper":
        grad_numerator = grad_alpha/safe_mass
        grad_mass = -grad_alpha*numerator/safe_mass**2*(mass>1e-12)
        grad_q += grad_mass.sum(axis=0,keepdims=True)-grad_mass
    else:
        grad_numerator = grad_alpha
    grad_q += distances.T @ grad_numerator
    grad_distances = grad_numerator @ q.T
    coefficients = np.divide(grad_distances+grad_distances.T,distances,
        out=np.zeros_like(distances),where=distances>0)
    grad_z = coefficients.sum(axis=1)[:,None]*z-coefficients @ z
    return 1.0-score,grad_z,grad_q


def dcss_loss_and_gradients(model,x,centers,*,silhouette_weight=0.01,
                             entropy_weight=0.01,temperature=0.25,
                             distance_normalization="source"):
    """Public-code MSE + .01*(1-softsil) + .01*mean entropy_bits objective."""
    z,reconstruction,cache = model.forward(x)
    log_sigmas = model.params["log_sigmas"]
    q = rbf_assignments(z,centers,log_sigmas,temperature)
    clustering,grad_z_sil,grad_q_sil = soft_silhouette_loss_and_gradients(z,q,
        distance_normalization=distance_normalization)
    entropy = float(np.mean(-np.sum(q*np.log(q+1e-10),axis=1))/np.log(2))
    grad_q_entropy = -(np.log(q+1e-10)+q/(q+1e-10))/(len(x)*np.log(2))
    grad_q = silhouette_weight*grad_q_sil+entropy_weight*grad_q_entropy
    grad_logits = q*(grad_q-np.sum(q*grad_q,axis=1,keepdims=True))
    difference = z[:,None,:]-centers[None,:,:]
    squared = np.sum(difference*difference,axis=2)
    inv_variance = np.exp(-2*log_sigmas)
    gaussian = np.exp(-squared*inv_variance[None,:])
    grad_gaussian = grad_logits/temperature
    grad_squared = -grad_gaussian*gaussian*inv_variance[None,:]
    grad_z_rbf = np.sum(2*grad_squared[:,:,None]*difference,axis=1)
    grad_centers = np.sum(-2*grad_squared[:,:,None]*difference,axis=0)
    grad_log_sigmas = np.sum(grad_gaussian*gaussian*2*squared*inv_variance[None,:],axis=0)
    reconstruction_loss,grad_x = reconstruct_loss_and_gradient(reconstruction,x)
    grads = model.backward(cache,grad_x,silhouette_weight*grad_z_sil+grad_z_rbf)
    grads["log_sigmas"] = grad_log_sigmas
    components = {"reconstruction":reconstruction_loss,"clustering":clustering,
        "soft_silhouette":1-clustering,"entropy_bits":entropy,
        "total":reconstruction_loss+silhouette_weight*clustering+entropy_weight*entropy}
    return components,grads,grad_centers


def _batch_indices(order,batch_size):
    batches = [order[start:start+batch_size] for start in range(0,len(order),batch_size)]
    # cdist/silhouette require two points. Include a singleton tail in the
    # preceding batch, preserving every sample exactly once per epoch.
    if len(batches)>1 and len(batches[-1]) == 1:
        tail = batches.pop()
        batches[-1] = np.concatenate((batches[-1],tail))
    return batches


def train_dcss(model,x,centers,*,epochs,batch_size,learning_rate,seed=0,
                silhouette_weight=0.01,entropy_weight=0.01,temperature=0.25,
                distance_normalization="source"):
    """Return (labels,z,centers,history) from shared pretraining/initial centers.

    Adds log_sigmas to model.params, initialized at zero (sigma=1) like RBF.py.
    Epoch trace is a sample-weighted average over fixed contiguous evaluation
    minibatches AFTER updates. The silhouette objective depends on minibatches;
    it is not a full-dataset silhouette or comparable to DEC/IDEC KL losses.
    """
    if epochs < 1 or batch_size < 2 or len(x)<2 or len(centers)<2:
        raise ValueError("DCSS requires positive epochs and at least two samples, clusters, and batch size.")
    settings = np.asarray([learning_rate,silhouette_weight,entropy_weight,temperature],dtype=float)
    if not np.isfinite(settings).all() or learning_rate<=0 or temperature<=0 or min(silhouette_weight,entropy_weight)<0:
        raise ValueError("Invalid DCSS learning rate, temperature or loss weights.")
    if "log_sigmas" not in model.params:
        model.params["log_sigmas"] = np.zeros(len(centers))
    if model.params["log_sigmas"].shape != (len(centers),):
        raise ValueError("log_sigmas must have one entry per center.")
    rng,optimizer,history = np.random.default_rng(seed),Adam(learning_rate),[]
    kwargs = dict(silhouette_weight=silhouette_weight,entropy_weight=entropy_weight,
                  temperature=temperature,distance_normalization=distance_normalization)
    for epoch in range(1,epochs+1):
        for indices in _batch_indices(rng.permutation(len(x)),batch_size):
            _,grads,grad_centers = dcss_loss_and_gradients(model,x[indices],centers,**kwargs)
            optimizer.update(model.params,grads)
            optimizer.update({"centers":centers},{"centers":grad_centers})
        totals = None
        for indices in _batch_indices(np.arange(len(x)),batch_size):
            components,_,_ = dcss_loss_and_gradients(model,x[indices],centers,**kwargs)
            if totals is None:
                totals = {key:0.0 for key in components}
            for key,value in components.items():
                totals[key] += value*len(indices)/len(x)
        history.append({"epoch":epoch,"phase":"cluster",**totals,"reset":0,
                        "loss_scope":"fixed_evaluation_minibatches"})
    z = model.encode(x)
    q = rbf_assignments(z,centers,model.params["log_sigmas"],temperature)
    return q.argmax(axis=1),z,centers,history
