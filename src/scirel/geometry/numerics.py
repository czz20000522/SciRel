"""Validated nonuniform finite-difference operators for the D2 proposal.

This module is deliberately separate from the frozen source.  It qualifies only
finite, one-dimensional, strictly increasing abscissae; it does not broaden the
legacy API's applicability domain.
"""
from __future__ import annotations

import numpy as np


class NumericalContractError(ValueError):
    """Input violates the supported numerical contract."""


def _validated_pair(x, y):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if x.ndim != 1 or y.ndim != 1 or x.size != y.size or x.size < 3:
        raise NumericalContractError("x and y must be 1-D arrays of equal length >= 3")
    if not (np.all(np.isfinite(x)) and np.all(np.isfinite(y))):
        raise NumericalContractError("x and y must be finite")
    dx = np.diff(x)
    if not np.all(dx > 0.0):
        raise NumericalContractError("x must be strictly increasing")
    return x, y


def diff_12_central(x, y):
    """Return first and second derivatives at interior points of a nonuniform grid.

    The three-point quadratic interpolant is evaluated analytically at each
    interior abscissa.  Endpoint derivatives are intentionally not fabricated;
    callers receive arrays of length ``len(x)-2`` as in the predecessor.
    """
    x, y = _validated_pair(x, y)
    x0, x1, x2 = x[:-2], x[1:-1], x[2:]
    y0, y1, y2 = y[:-2], y[1:-1], y[2:]
    h0, h1 = x1 - x0, x2 - x1
    d_one = (h0 * (y2 - y1) / h1 + h1 * (y1 - y0) / h0) / (h0 + h1)
    d_two = 2.0 * (
        y0 / (h0 * (h0 + h1))
        - y1 / (h0 * h1)
        + y2 / (h1 * (h0 + h1))
    )
    return d_one, d_two
