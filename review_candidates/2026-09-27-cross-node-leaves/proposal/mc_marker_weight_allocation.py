"""Source-shaped FIDASIM get_nlaunch marker allocation with caller-owned
CDF draws.

Source: FIDASIM ``get_nlaunch`` -- every active cell (positive approximate
weight) first receives ``minimum_per_active_cell`` markers; the remainder is
distributed by inverse-CDF sampling over the Fortran-order flattened weight
volume using caller-owned uniform draws (deterministic, replayable mapping;
no RNG is bound).

Registered hardening: the total allocated marker count is checked against
``requested_markers``; the saved arm has no such conservation check.
"""
from __future__ import annotations

import numpy as np

__all__ = ["allocate_mc_markers_by_weight"]


def allocate_mc_markers_by_weight(*, approximate_cell_weight, requested_markers, cdf_uniform_draws, minimum_per_active_cell=5):
    weight = np.asarray(approximate_cell_weight, dtype=float)
    draws = np.asarray(cdf_uniform_draws, dtype=float)
    if (weight.ndim != 3 or not np.all(np.isfinite(weight)) or np.any(weight < 0)
            or isinstance(requested_markers, bool) or int(requested_markers) != requested_markers
            or requested_markers < 0
            or isinstance(minimum_per_active_cell, bool)
            or int(minimum_per_active_cell) != minimum_per_active_cell
            or minimum_per_active_cell < 0):
        raise ValueError("weights must be finite nonnegative 3-D values and count inputs nonnegative integers")
    mask = weight > 0
    counts = np.zeros(weight.shape, dtype=np.int64)
    counts[mask] = int(minimum_per_active_cell)
    remainder = int(requested_markers) - int(counts.sum())
    if remainder <= 0:
        return counts
    if (draws.shape != (remainder,) or not np.all(np.isfinite(draws))
            or np.any(draws < 0) or np.any(draws >= 1)):
        raise ValueError("cdf_uniform_draws must be finite [0,1) values, one for each leftover marker")
    flat = weight.ravel(order="F")
    cdf = np.cumsum(flat)
    total = cdf[-1]
    if total <= 0:
        raise ValueError("positive remainder requires at least one active cell")
    selected = np.searchsorted(cdf, draws * total, side="right")
    for index in selected:
        counts[np.unravel_index(index, weight.shape, order="F")] += 1
    if int(counts.sum()) != int(requested_markers):
        # Registered hardening: conservation of the requested marker count.
        raise ValueError(
            "marker allocation does not conserve requested_markers "
            "(registered hardening)")
    return counts
