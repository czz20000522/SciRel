"""Explicit outer-seed convergence relation for H/H2 generation lifecycles."""
from __future__ import annotations

import numpy as np


def _finite_real(value, name, *, scalar=False):
    try:
        if isinstance(value, (list, tuple)) and any(
            isinstance(item, (bool, np.bool_)) for item in np.asarray(value, dtype=object).flat
        ):
            raise ValueError
        raw = np.asarray(value)
        if raw.dtype.kind not in "iuf" or (scalar and raw.ndim != 0):
            raise ValueError
        result = np.asarray(raw, dtype=float)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be finite real {'scalar' if scalar else 'array'}") from exc
    if not np.all(np.isfinite(result)):
        raise ValueError(f"{name} must be finite real {'scalar' if scalar else 'array'}")
    return float(result) if scalar else result


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
    previous = _finite_real(previous_density_m3, "previous_density_m3")
    current = _finite_real(current_density_m3, "current_density_m3")
    truncate = _finite_real(truncate, "truncate", scalar=True)
    if (
        previous.ndim != 1
        or current.shape != previous.shape
        or previous.size == 0
        or np.any(previous < 0.0)
        or np.any(current < 0.0)
        or truncate <= 0.0
        or np.max(current) <= 0.0
    ):
        raise ValueError(
            "outer seed density profiles must be finite, nonnegative, aligned, "
            "and current density must be positive"
        )

    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        seed_error = float(np.max(np.abs(previous - current)) / np.max(current))
        threshold = float(10.0 * truncate)
    if not np.isfinite(seed_error):
        raise ValueError("seed_error must be finite")
    if not np.isfinite(threshold):
        raise ValueError("reentry_threshold must be finite")
    should_reiterate = seed_error > threshold
    return {
        "seed_error": seed_error,
        "reentry_threshold": threshold,
        "should_reiterate": should_reiterate,
        "reason": "reiterate" if should_reiterate else "converged",
    }
