"""Private numerical kernels shared across scientific domains."""

from __future__ import annotations

import numpy as np


def stable_gradient(values, coordinates, axis):
    """Quadratic three-point derivative written as local value differences."""

    f = np.moveaxis(np.asarray(values, dtype=float), axis, -1)
    h = np.diff(np.asarray(coordinates, dtype=float))
    slopes = np.diff(f, axis=-1) / h
    result = np.empty_like(f)
    result[..., 1:-1] = (
        h[1:] * slopes[..., :-1] + h[:-1] * slopes[..., 1:]
    ) / (h[:-1] + h[1:])
    result[..., 0] = slopes[..., 0] - h[0] * (slopes[..., 1] - slopes[..., 0]) / (h[0] + h[1])
    result[..., -1] = slopes[..., -1] + h[-1] * (slopes[..., -1] - slopes[..., -2]) / (h[-2] + h[-1])
    return np.moveaxis(result, -1, axis)


__all__ = ["stable_gradient"]
