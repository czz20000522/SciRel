"""Thresholded Moore-Penrose pseudo-inverse for dense real matrices."""

from __future__ import annotations

import numpy as np

__all__ = ["truncated_svd_inverse"]


def truncated_svd_inverse(mat, rcond=1e-10):
    """Compute the Moore-Penrose inverse with truncated singular values.

    Parameters
    ----------
    mat : array_like
        Finite real matrix of shape ``(m, n)``.
    rcond : float, optional
        Relative singular-value threshold; values below ``rcond`` are
        discarded (default ``1e-10``).

    Returns
    -------
    numpy.ndarray
        Pseudo-inverse of shape ``(n, m)``.
    """
    matrix = np.asarray(mat, dtype=float)
    if matrix.ndim != 2:
        raise ValueError("mat must be a 2-D array")
    if not np.isfinite(matrix).all():
        raise ValueError("mat must contain only finite values")
    threshold = float(rcond)
    if not np.isfinite(threshold) or threshold <= 0.0:
        raise ValueError("rcond must be a positive finite scalar")
    u, singular, vt = np.linalg.svd(matrix, full_matrices=False)
    inverse = np.zeros_like(singular)
    if singular.size and singular.max() == 0.0:
        # The zero matrix has a zero pseudo-inverse; relative thresholding
        # would otherwise keep a zero singular value and divide by it.
        return np.zeros((matrix.shape[1], matrix.shape[0]), dtype=float)
    keep = singular >= threshold * singular.max() if singular.size else singular.astype(bool)
    inverse[keep] = 1.0 / singular[keep]
    return (vt.T * inverse) @ u.T
