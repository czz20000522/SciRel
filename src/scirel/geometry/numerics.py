"""Small validated finite-difference operators."""
from __future__ import annotations

import numpy as np

__all__ = ["NumericalContractError", "diff_12_central"]


class NumericalContractError(ValueError):
    """Input violates the supported numerical contract."""


def _validated_pair(x, y):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if x.ndim != 1 or y.ndim != 1 or x.size != y.size or x.size < 3:
        raise NumericalContractError("x and y must be 1-D arrays of equal length >= 3")
    if not np.isfinite(x).all() or not np.isfinite(y).all():
        raise NumericalContractError("x and y must be finite")
    if np.any(np.diff(x) <= 0.0):
        raise NumericalContractError("x must be strictly increasing")
    return x, y


def diff_12_central(x, y):
    """Return first and second derivatives at interior points of ``x``."""
    x, y = _validated_pair(x, y)
    h_left = x[1:-1] - x[:-2]
    h_right = x[2:] - x[1:-1]
    first = (
        h_left * (y[2:] - y[1:-1]) / h_right
        + h_right * (y[1:-1] - y[:-2]) / h_left
    ) / (h_left + h_right)
    second = 2.0 * (
        y[:-2] / (h_left * (h_left + h_right))
        - y[1:-1] / (h_left * h_right)
        + y[2:] / (h_right * (h_left + h_right))
    )
    return first, second
