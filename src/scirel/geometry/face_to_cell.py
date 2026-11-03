"""Midpoint mapping from a one-dimensional face grid to cell centers."""
from __future__ import annotations

import numpy as np

__all__ = ["face_to_cell"]


def face_to_cell(face):
    """Return ``(face[:-1] + face[1:]) / 2`` as finite float64 values."""
    try:
        raw = np.asarray(face)
    except (TypeError, ValueError) as exc:
        raise ValueError("face must be a finite real one-dimensional array") from exc
    if raw.ndim != 1 or raw.size < 2 or raw.dtype.kind not in "iuf":
        raise ValueError("face must be a finite real one-dimensional array of at least two values")
    if np.ma.isMaskedArray(face) or any(
        isinstance(item, (bool, np.bool_)) for item in np.asarray(face, dtype=object).flat
    ):
        raise ValueError("face must be a finite real one-dimensional array of at least two values")
    values = raw.astype(np.float64, copy=False)
    if not np.isfinite(values).all():
        raise ValueError("face must contain only finite values")
    left, right = values[:-1], values[1:]
    with np.errstate(over="ignore", under="ignore", invalid="ignore"):
        summed = left + right
        result = np.where(np.isfinite(summed), summed * 0.5, left * 0.5 + right * 0.5)
    if not np.isfinite(result).all():
        raise FloatingPointError("face midpoint is not representable")
    return result
