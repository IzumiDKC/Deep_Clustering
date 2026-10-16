"""Small-data IDEC with the two ideas from SANE (ICLR 2026).

This is an independently written *adaptation*, not the authors' ResNet/MoCo-v2
implementation. The paper's density-aware prototype initialization (DACHI)
and dynamic sample selection (DSS) are used with the common NumPy IDEC model.
Original: https://proceedings.iclr.cc/paper_files/paper/2026/hash/63ef323523f3be8b58ed9277cc747485-Abstract-Conference.html
"""
from __future__ import annotations

import numpy as np
from sklearn.neighbors import NearestNeighbors

from .models import (Adam, assignments, kl_loss_and_gradients,
                     reconstruct_loss_and_gradient, target_distribution)


def density_aware_centers(z, initial_labels, centers, *, alpha=2.0, k=10):
    """DACHI: weight cluster prototypes by within-cluster k-NN distance.

    Neighbors use L2-normalized features as in modern contrastive backbones;
    the returned prototypes remain in the unnormalized latent coordinates
    expected by the NumPy IDEC model. No evaluation label is used.
    """
    if alpha < 0 or k < 1:
        raise ValueError("alpha must be nonnegative and k must be positive")
    z = np.asarray(z, dtype=np.float64)
    initial_labels = np.asarray(initial_labels)
    updated = np.asarray(centers, dtype=np.float64).copy()
    if z.ndim != 2 or initial_labels.shape != (len(z),) or updated.ndim != 2 or updated.shape[1] != z.shape[1]:
        raise ValueError("Incompatible latent vectors, initial labels, or centers")
    norm = np.linalg.norm(z, axis=1, keepdims=True)
    normalized = z / np.maximum(norm, 1e-12)
    for cluster in range(len(updated)):
        members = np.flatnonzero(initial_labels == cluster)
        if len(members) < 2:
            continue
        neighbors = NearestNeighbors(n_neighbors=min(k + 1, len(members))).fit(normalized[members])
        distances = neighbors.kneighbors(normalized[members], return_distance=True)[0][:, 1:]
        avg_distance = distances.mean(axis=1)
        logits = alpha * avg_distance
        weights = np.exp(logits - logits.max())
        updated[cluster] = np.average(z[members], axis=0, weights=weights)
    return updated


def stable_samples(consistency: np.ndarray, pseudo_labels: np.ndarray, epsilon=0.1,
                   min_retain_fraction=0.25, rng=None):
    """DSS: exclude samples stable over three epochs; retain hard cases.

    `consistency` and `pseudo_labels` each contain three full-data rows.
    A fixed retention floor prevents an empty training epoch on tiny datasets;
    this floor is an explicit adaptation absent from the original paper.
    """
    c = np.asarray(consistency, dtype=np.float64)
    p = np.asarray(pseudo_labels)
    if c.ndim != 2 or c.shape[0] != 3 or p.shape != c.shape:
        raise ValueError("Expected three epochs of consistency and pseudo labels")
    if not 0 <= epsilon or not 0 < min_retain_fraction <= 1:
        raise ValueError("Invalid DSS epsilon or retention floor")
    second_difference = np.abs(c[2] - 2*c[1] + c[0])
    label_stable = (p[0] == p[1]) & (p[1] == p[2])
    retained = (second_difference >= epsilon) | ~label_stable
    minimum = max(1, int(np.ceil(min_retain_fraction * c.shape[1])))
    if retained.sum() < minimum:
        # Prefer temporal inconsistency while preserving every changing label.
        priority = second_difference + (~label_stable).astype(float)
        order = np.arange(len(priority)) if rng is None else rng.permutation(len(priority))
        retained[order[np.argsort(priority[order])[-minimum:]]] = True
    return retained


def _prediction_consistency(model, x, centers, rng, weak_sigma, strong_sigma):
    weak = np.clip(x + rng.normal(0, weak_sigma, size=x.shape), 0, 1)
    strong = np.clip(x + rng.normal(0, strong_sigma, size=x.shape), 0, 1)
    q_weak = assignments(model.encode(weak), centers)
    q_strong = assignments(model.encode(strong), centers)
    numerator = np.sum(q_weak*q_strong, axis=1)
    denominator = np.linalg.norm(q_weak,axis=1)*np.linalg.norm(q_strong,axis=1)
    return numerator / np.maximum(denominator, 1e-12)


def train_sane_idec(model, x, centers, *, epochs, batch_size, learning_rate,
                    gamma, seed, target_interval=5, epsilon=0.1,
                    min_retain_fraction=0.25, weak_sigma=0.025,
                    strong_sigma=0.08):
    """Train IDEC with SANE-inspired DACHI/DSS under the common epoch budget.

    `centers` should already be DACHI-refined. Unlike the ICLR experiment this
    uses additive pixel noise, a small fully-connected AE, and KL+MSE of IDEC.
    The fixed seed and floor are declared before evaluation; y is not accepted.
    """
    if not (0 <= weak_sigma < strong_sigma) or epochs < 1 or target_interval < 1:
        raise ValueError("Invalid perturbation or training settings")
    order_rng = np.random.default_rng(seed)
    view_rng = np.random.default_rng(seed + 314159)
    optimizer = Adam(learning_rate)
    score_history, label_history, trace = [], [], []
    p = None
    for epoch in range(1, epochs+1):
        z_all = model.encode(x)
        q_all = assignments(z_all, centers)
        if p is None or (epoch - 1) % target_interval == 0:
            p = target_distribution(q_all)
        score_history.append(_prediction_consistency(model,x,centers,view_rng,weak_sigma,strong_sigma))
        label_history.append(q_all.argmax(axis=1))
        if len(score_history) >= 3:
            active = stable_samples(np.stack(score_history[-3:]), np.stack(label_history[-3:]),
                                    epsilon, min_retain_fraction, view_rng)
        else:
            active = np.ones(len(x), dtype=bool)
        order = order_rng.permutation(len(x))
        order = order[active[order]]
        for start in range(0,len(order),batch_size):
            indices = order[start:start+batch_size]
            batch = x[indices]
            z, reconstructed, cache = model.forward(batch)
            _, grad_z, grad_centers = kl_loss_and_gradients(z, centers, p[indices])
            _, grad_x = reconstruct_loss_and_gradient(reconstructed,batch)
            optimizer.update(model.params,model.backward(cache,grad_x,gamma*grad_z))
            optimizer.update({"centers":centers},{"centers":gamma*grad_centers})
        z_all,reconstructed,_ = model.forward(x)
        rec,_ = reconstruct_loss_and_gradient(reconstructed,x)
        kl,_,_ = kl_loss_and_gradients(z_all,centers,p)
        trace.append({"epoch":epoch,"phase":"cluster","reconstruction":rec,
                      "clustering":kl,"total":rec+gamma*kl,"reset":0,
                      "retained_samples":int(active.sum()),
                      "retained_fraction":float(active.mean()),
                      "mean_prediction_consistency":float(score_history[-1].mean())})
    z_all = model.encode(x)
    return assignments(z_all,centers).argmax(axis=1), z_all, centers, trace
