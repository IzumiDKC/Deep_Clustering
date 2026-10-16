"""Evaluation only. Ground-truth labels never enter model training."""
import numpy as np
from scipy.optimize import linear_sum_assignment
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score


def mapped_labels(y_true, y_pred):
    """Match integer cluster IDs one-to-one to evaluation labels.

    Unmatched clusters get a sentinel absent from y_true, including when the
    dataset itself uses -1 as a valid class label.
    """
    y_true, y_pred = np.asarray(y_true), np.asarray(y_pred)
    if y_true.ndim != 1 or y_pred.ndim != 1 or len(y_true) != len(y_pred) or not len(y_true):
        raise ValueError("Expected nonempty one-dimensional labels of equal length.")
    if not np.issubdtype(y_true.dtype, np.integer) or not np.issubdtype(y_pred.dtype, np.integer):
        raise ValueError("Expected integer class labels and cluster IDs.")
    true_values, true_index = np.unique(y_true, return_inverse=True)
    pred_values, pred_index = np.unique(y_pred, return_inverse=True)
    contingency = np.zeros((len(pred_values), len(true_values)), dtype=np.int64)
    np.add.at(contingency, (pred_index, true_index), 1)
    row, column = linear_sum_assignment(-contingency)
    mapping = {int(pred_values[r]): int(true_values[c]) for r, c in zip(row, column)}
    known_labels = {int(value) for value in true_values}
    unmatched = -1
    while unmatched in known_labels:
        unmatched -= 1
    mapped = np.array([mapping.get(int(value), unmatched) for value in y_pred], dtype=int)
    return mapped, mapping


def evaluate(y_true, y_pred):
    mapped, _ = mapped_labels(y_true, y_pred)
    return {"acc": float(np.mean(mapped == y_true)),
            "nmi": float(normalized_mutual_info_score(y_true, y_pred, average_method="arithmetic")),
            "ari": float(adjusted_rand_score(y_true, y_pred))}
