"""Readable NumPy implementations for a small deep-clustering demonstration.

These are independent educational implementations, not the authors' code.
DEC uses its Student-t assignments and KL loss. IDEC adds reconstruction.
DCN uses reconstruction plus hard k-means distortion with batch centroid updates.
IDEC_BRB adds encoder soft resets, reclustering and centroid Adam-state resets.
Architectures, optimizer and schedules differ from the original experiments.
"""
from __future__ import annotations

from copy import deepcopy
import numpy as np
from scipy.special import expit
from sklearn.cluster import KMeans


class Autoencoder:
    """64 -> 64 -> 32 -> 10 -> 32 -> 64 -> 64 by default."""

    def __init__(self, input_dim=64, latent_dim=10, seed=0):
        rng = np.random.default_rng(seed)
        self.dims = [input_dim, 64, 32, latent_dim, 32, 64, input_dim]
        self.params = {}
        for i, (fan_in, fan_out) in enumerate(zip(self.dims[:-1], self.dims[1:])):
            scale = np.sqrt(2.0 / fan_in) if i not in (2, 5) else np.sqrt(1.0 / fan_in)
            self.params[f"W{i}"] = rng.normal(0, scale, (fan_in, fan_out))
            self.params[f"b{i}"] = np.zeros(fan_out)

    def clone(self):
        return deepcopy(self)

    def encode(self, x):
        h = x
        for i in range(3):
            h = h @ self.params[f"W{i}"] + self.params[f"b{i}"]
            if i < 2:
                h = np.maximum(h, 0)
        return h

    def forward(self, x):
        values, preacts = [x], []
        for i in range(6):
            a = values[-1] @ self.params[f"W{i}"] + self.params[f"b{i}"]
            preacts.append(a)
            h = a if i == 2 else (expit(a) if i == 5 else np.maximum(a, 0))
            values.append(h)
        return values[3], values[-1], (values, preacts)

    def backward(self, cache, grad_reconstruction=None, grad_latent=None):
        values, preacts = cache
        grads = {}
        g = np.zeros_like(values[-1]) if grad_reconstruction is None else grad_reconstruction
        for i in reversed(range(6)):
            if i == 2 and grad_latent is not None:
                g = g + grad_latent
            if i == 5:
                g = g * values[-1] * (1 - values[-1])
            elif i != 2:
                g = g * (preacts[i] > 0)
            grads[f"W{i}"] = values[i].T @ g
            grads[f"b{i}"] = g.sum(axis=0)
            g = g @ self.params[f"W{i}"].T
        return grads

    def soft_reset_encoder(self, rng, alpha=0.8):
        """Interpolate encoder parameters with fresh random initialization.

        alpha is the fraction of the learned parameters kept. Decoder is retained.
        The random initialization uses the same distribution as Autoencoder.
        """
        fresh = Autoencoder(self.dims[0], self.dims[3], int(rng.integers(2**31 - 1)))
        for i in range(3):
            for prefix in ("W", "b"):
                key = f"{prefix}{i}"
                self.params[key] *= alpha
                self.params[key] += (1 - alpha) * fresh.params[key]


class Adam:
    def __init__(self, learning_rate=1e-3):
        self.lr = learning_rate
        self.m, self.v, self.steps = {}, {}, {}

    def update(self, params, grads):
        for key, g in grads.items():
            if key not in self.m:
                self.m[key], self.v[key], self.steps[key] = np.zeros_like(g), np.zeros_like(g), 0
            self.steps[key] += 1
            t = self.steps[key]
            self.m[key] = 0.9 * self.m[key] + 0.1 * g
            self.v[key] = 0.999 * self.v[key] + 0.001 * g**2
            params[key] -= self.lr * (self.m[key] / (1 - 0.9**t)) / (
                np.sqrt(self.v[key] / (1 - 0.999**t)) + 1e-8
            )

    def reset(self, key):
        self.m.pop(key, None)
        self.v.pop(key, None)
        self.steps.pop(key, None)


def squared_distances(z, centers):
    return np.maximum((z*z).sum(1)[:, None] + (centers*centers).sum(1)[None, :] - 2*z @ centers.T, 0)


def assignments(z, centers):
    """Student-t kernel with alpha=1, as in DEC."""
    unnormalized = 1.0 / (1.0 + squared_distances(z, centers))
    return unnormalized / unnormalized.sum(axis=1, keepdims=True)


def target_distribution(q):
    weighted = q*q / np.maximum(q.sum(axis=0, keepdims=True), 1e-12)
    return weighted / weighted.sum(axis=1, keepdims=True)


def kl_loss_and_gradients(z, centers, p):
    """p is treated as a fixed target during each gradient update."""
    dist = squared_distances(z, centers)
    q = assignments(z, centers)
    loss = np.sum(p * (np.log(np.maximum(p, 1e-12)) - np.log(np.maximum(q, 1e-12)))) / len(z)
    coefficient = 2.0 * (p - q) / (1.0 + dist) / len(z)
    grad_z = coefficient.sum(1)[:, None]*z - coefficient @ centers
    grad_centers = coefficient.sum(0)[:, None]*centers - coefficient.T @ z
    return float(loss), grad_z, grad_centers


def reconstruct_loss_and_gradient(reconstruction, x):
    difference = reconstruction - x
    return float(np.mean(difference*difference)), 2.0*difference/difference.size


def fit_kmeans(z, n_clusters, seed, n_init=20):
    km = KMeans(n_clusters=n_clusters, n_init=n_init, random_state=seed)
    labels = km.fit_predict(z)
    return labels, km.cluster_centers_.copy()


def pretrain(model, x, epochs, batch_size, learning_rate, seed):
    rng, optimizer, history = np.random.default_rng(seed), Adam(learning_rate), []
    for epoch in range(1, epochs+1):
        order = rng.permutation(len(x))
        for start in range(0, len(x), batch_size):
            batch = x[order[start:start+batch_size]]
            _, reconstructed, cache = model.forward(batch)
            _, gradient = reconstruct_loss_and_gradient(reconstructed, batch)
            optimizer.update(model.params, model.backward(cache, gradient))
        _, reconstructed, _ = model.forward(x)
        loss, _ = reconstruct_loss_and_gradient(reconstructed, x)
        history.append({"epoch": epoch, "phase": "pretrain", "reconstruction": loss, "clustering": 0.0, "total": loss, "reset": 0})
    return history


def train_dec(model, x, centers, *, reconstruct, epochs, batch_size,
              learning_rate, gamma, seed, target_interval=5,
              brb_interval=0, brb_alpha=0.8):
    """DEC, IDEC, or educational IDEC+BRB; uses a fixed epoch budget.

    Target P is recomputed over ALL samples, not independently inside a batch.
    BRB applies a reset before an epoch and refreshes centers and P afterwards.
    No ground-truth labels enter this training function.
    """
    rng, optimizer, history = np.random.default_rng(seed), Adam(learning_rate), []
    p = None
    for epoch in range(1, epochs+1):
        reset = brb_interval > 0 and epoch > 1 and (epoch-1) % brb_interval == 0
        if reset:
            model.soft_reset_encoder(rng, brb_alpha)
            _, centers = fit_kmeans(model.encode(x), len(centers), int(rng.integers(2**31-1)))
            optimizer.reset("centers")
        if p is None or (epoch-1) % target_interval == 0 or reset:
            p = target_distribution(assignments(model.encode(x), centers))
        order = rng.permutation(len(x))
        for start in range(0, len(x), batch_size):
            indices = order[start:start+batch_size]
            batch = x[indices]
            z, reconstructed, cache = model.forward(batch)
            _, grad_z, grad_mu = kl_loss_and_gradients(z, centers, p[indices])
            cluster_weight = gamma if reconstruct else 1.0
            grad_x = None
            if reconstruct:
                _, grad_x = reconstruct_loss_and_gradient(reconstructed, batch)
            grads = model.backward(cache, grad_x, cluster_weight*grad_z)
            if not reconstruct:
                # DEC removes the decoder from fine-tuning.
                grads = {key: value for key, value in grads.items() if int(key[1:]) < 3}
            optimizer.update(model.params, grads)
            optimizer.update({"centers": centers}, {"centers": cluster_weight*grad_mu})
        z, reconstructed, _ = model.forward(x)
        rec, _ = reconstruct_loss_and_gradient(reconstructed, x)
        kl, _, _ = kl_loss_and_gradients(z, centers, p)
        total = rec + gamma*kl if reconstruct else kl
        history.append({"epoch": epoch, "phase": "cluster", "reconstruction": rec,
                        "clustering": kl, "total": total, "reset": int(reset)})
    z = model.encode(x)
    return assignments(z, centers).argmax(1), z, centers, history


def train_dcn(model, x, centers, *, epochs, batch_size, learning_rate, dcn_weight, seed):
    """Batch-alternating DCN illustration.

    L = mean_pixel_reconstruction_error + weight*mean_sample_squared_distance.
    Hard assignments are computed before each epoch, and centroids are updated
    by full-data averages afterwards. Original DCN uses online centroid updates.
    """
    rng, optimizer, history = np.random.default_rng(seed), Adam(learning_rate), []
    for epoch in range(1, epochs+1):
        labels = squared_distances(model.encode(x), centers).argmin(1)
        order = rng.permutation(len(x))
        for start in range(0, len(x), batch_size):
            indices = order[start:start+batch_size]
            batch = x[indices]
            z, reconstructed, cache = model.forward(batch)
            difference = z - centers[labels[indices]]
            grad_z = dcn_weight*2.0*difference/len(batch)
            _, grad_x = reconstruct_loss_and_gradient(reconstructed, batch)
            optimizer.update(model.params, model.backward(cache, grad_x, grad_z))
        z, reconstructed, _ = model.forward(x)
        labels = squared_distances(z, centers).argmin(1)
        for cluster in range(len(centers)):
            selected = z[labels == cluster]
            if len(selected):
                centers[cluster] = selected.mean(0)
        # Report the hard-clustering objective for the updated centroids.
        # Their movement can change assignments at the end of an epoch.
        labels = squared_distances(z, centers).argmin(1)
        rec, _ = reconstruct_loss_and_gradient(reconstructed, x)
        distortion = float(np.mean(np.sum((z-centers[labels])**2, axis=1)))
        history.append({"epoch": epoch, "phase": "cluster", "reconstruction": rec,
                        "clustering": distortion, "total": rec+dcn_weight*distortion, "reset": 0})
    z = model.encode(x)
    return squared_distances(z, centers).argmin(1), z, centers, history
