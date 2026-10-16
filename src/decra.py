"""DECRA public-code mechanism adapted to the shared small NumPy autoencoder.

Source: https://github.com/lml-mengli/DECRA/blob/main/decra.py
Paper: https://doi.org/10.1007/s11063-024-11586-0

The public PyTorch code differs from the paper's explicit z + H(z) residual:
it decodes z and an affine z_hat separately and uses their reconstruction
consistency. This module follows that CODE, including both gradient paths.
It retains the common pretrained backbone and sigmoid decoder in this demo;
it is not an exact reproduction of the published experiments or original AE.
"""
from __future__ import annotations

import numpy as np
from scipy.special import expit

from .models import (Adam, assignments, target_distribution,
                     kl_loss_and_gradients, reconstruct_loss_and_gradient)


def initialize_adaptive_layer(model, seed):
    """Add torch.Linear-style affine parameters without changing the backbone.

    PyTorch Linear samples weights and biases uniformly in +/-1/sqrt(fan_in).
    This matches the distribution, not PyTorch's random-number sequence.
    Existing parameters are retained so saved DECRA checkpoints can be resumed.
    """
    latent_dim = model.dims[3]
    keys = ("W_residual", "b_residual")
    if any(key in model.params for key in keys):
        if not all(key in model.params for key in keys):
            raise ValueError("Adaptive weight and bias must both be present.")
        if model.params[keys[0]].shape != (latent_dim, latent_dim) or model.params[keys[1]].shape != (latent_dim,):
            raise ValueError("Adaptive parameters must match the latent dimension.")
        return
    # Separate generator preserves the same seed-driven minibatch stream.
    rng = np.random.default_rng(np.random.SeedSequence([seed, 2024]))
    bound = 1.0 / np.sqrt(latent_dim)
    model.params[keys[0]] = rng.uniform(-bound, bound, size=(latent_dim, latent_dim))
    model.params[keys[1]] = rng.uniform(-bound, bound, size=latent_dim)


def decode(model, latent):
    """Decode with the same W3-W5 used by Autoencoder.forward."""
    values, preacts = [latent], []
    for layer in range(3, 6):
        preactivation = values[-1] @ model.params[f"W{layer}"] + model.params[f"b{layer}"]
        preacts.append(preactivation)
        values.append(expit(preactivation) if layer == 5 else np.maximum(preactivation, 0))
    return values[-1], (values, preacts)


def _decoder_backward(model, cache, gradient):
    values, preacts = cache
    grads = {}
    for layer in reversed(range(3, 6)):
        offset = layer - 3
        if layer == 5:
            gradient = gradient * values[-1] * (1.0 - values[-1])
        else:
            gradient = gradient * (preacts[offset] > 0)
        grads[f"W{layer}"] = values[offset].T @ gradient
        grads[f"b{layer}"] = gradient.sum(axis=0)
        gradient = gradient @ model.params[f"W{layer}"].T
    return grads, gradient


def decra_loss_and_gradients(model, x, centers, p, *, gamma=0.1,
                             reconstruction_weight=2.0, consistency_weight=0.6,
                             kl_reduction="mean"):
    """Return loss components, network gradients and centroid gradient.

    L = 2*MSE(decode(z), X) + .6*MSE(decode(A(z)), decode(z)) + .1*KL_mean.
    Defaults reproduce the public code's fine-tuning objective. KL_mean divides
    the summed divergence by N*K, as torch F.kl_div's default reduction='mean'.
    'batchmean' divides by N instead, and is an explicit protocol change.
    The consistency target decode(z) is NOT detached in the author's code.
    P must be fixed while differentiating; ground-truth labels are not inputs.
    """
    if kl_reduction not in ("mean", "batchmean"):
        raise ValueError("kl_reduction must be 'mean' or 'batchmean'.")
    z, reconstruction, base_cache = model.forward(x)
    adapted = z @ model.params["W_residual"] + model.params["b_residual"]
    auxiliary, auxiliary_cache = decode(model, adapted)
    rec_loss, rec_grad = reconstruct_loss_and_gradient(reconstruction, x)
    consistency_loss, consistency_grad = reconstruct_loss_and_gradient(auxiliary, reconstruction)
    kl_batchmean, grad_z, grad_centers = kl_loss_and_gradients(z, centers, p)
    kl_divisor = len(centers) if kl_reduction == "mean" else 1
    kl = kl_batchmean / kl_divisor

    # Both decoded outputs depend on the shared decoder and encoder.
    # The main branch receives the negative consistency gradient.
    aux_grads, grad_adapted = _decoder_backward(model, auxiliary_cache,
                                              consistency_weight * consistency_grad)
    adaptive_grad_z = grad_adapted @ model.params["W_residual"].T
    grads = model.backward(base_cache,
        reconstruction_weight * rec_grad - consistency_weight * consistency_grad,
        adaptive_grad_z + gamma * grad_z / kl_divisor)
    for key, value in aux_grads.items():
        grads[key] += value
    grads["W_residual"] = z.T @ grad_adapted
    grads["b_residual"] = grad_adapted.sum(axis=0)
    components = {
        "reconstruction":rec_loss,
        "consistency":consistency_loss,
        "clustering":kl,
        "kl_batchmean":kl_batchmean,
        "total":reconstruction_weight*rec_loss + consistency_weight*consistency_loss + gamma*kl,
    }
    return components, grads, gamma * grad_centers / kl_divisor


def train_decra(model, x, centers, *, epochs, batch_size, learning_rate, gamma=0.1,
                seed=0, target_interval=5, consistency_weight=0.6,
                reconstruction_weight=2.0, kl_reduction="mean"):
    """Train the public-code DECRA adaptation from a shared pretrained AE.

    Mutates model.params (including new W_residual/b_residual) and centers.
    Returns (labels, embedding_z, centers, history), like train_dec/train_dcn.
    Unlike the source, the benchmark uses shared AE pretraining, shuffled
    minibatches, a fixed epoch budget and the common target-update interval.
    """
    if min(epochs, batch_size, target_interval) < 1:
        raise ValueError("Epochs, batch size and target interval must be positive.")
    settings = np.asarray([learning_rate,gamma,consistency_weight,reconstruction_weight], dtype=float)
    if not np.isfinite(settings).all() or learning_rate <= 0 or min(gamma,consistency_weight,reconstruction_weight) < 0:
        raise ValueError("Learning rate must be positive and all loss weights nonnegative and finite.")
    initialize_adaptive_layer(model, seed)
    rng, optimizer, history = np.random.default_rng(seed), Adam(learning_rate), []
    p = None
    for epoch in range(1, epochs+1):
        if p is None or (epoch-1) % target_interval == 0:
            p = target_distribution(assignments(model.encode(x), centers))
        order = rng.permutation(len(x))
        for start in range(0, len(x), batch_size):
            indices = order[start:start+batch_size]
            _, grads, grad_centers = decra_loss_and_gradients(model,x[indices],centers,p[indices],
                gamma=gamma,reconstruction_weight=reconstruction_weight,
                consistency_weight=consistency_weight,kl_reduction=kl_reduction)
            optimizer.update(model.params,grads)
            optimizer.update({"centers":centers},{"centers":grad_centers})
        components, _, _ = decra_loss_and_gradients(model,x,centers,p,
            gamma=gamma,reconstruction_weight=reconstruction_weight,
            consistency_weight=consistency_weight,kl_reduction=kl_reduction)
        history.append({"epoch":epoch,"phase":"cluster",**components,"reset":0})
    z = model.encode(x)
    return assignments(z,centers).argmax(1),z,centers,history
