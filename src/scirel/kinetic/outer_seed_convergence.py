"""Explicit outer-seed convergence relation for H/H2 generation lifecycles."""
from __future__ import annotations

import numpy as np


def evaluate_neutral_outer_seed_convergence(
    previous_density_m3,
    current_density_m3,
    truncate,
):
    """Evaluate the source-defined outer seed re-entry condition.

    The source compares the density profile before and after an outer seed
    pass and re-enters when ``Delta_seed > 10 * truncate``.  This operator
    owns only that scalar relation; generation propagation and state reset are
    owned by the task graph.
    """
    previous = np.asarray(previous_density_m3, dtype=float)
    current = np.asarray(current_density_m3, dtype=float)
    if (
        previous.ndim != 1
        or current.shape != previous.shape
        or previous.size == 0
        or not np.all(np.isfinite(previous))
        or not np.all(np.isfinite(current))
        or np.any(previous < 0.0)
        or np.any(current < 0.0)
        or not np.isfinite(truncate)
        or truncate <= 0.0
        or np.max(current) <= 0.0
    ):
        raise ValueError(
            "outer seed density profiles must be finite, nonnegative, aligned, "
            "and current density must be positive"
        )

    seed_error = float(np.max(np.abs(previous - current)) / np.max(current))
    threshold = float(10.0 * truncate)
    should_reiterate = seed_error > threshold
    return {
        "seed_error": seed_error,
        "reentry_threshold": threshold,
        "should_reiterate": should_reiterate,
        "reason": "reiterate" if should_reiterate else "converged",
    }


