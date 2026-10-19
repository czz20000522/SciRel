"""Source-free top-level KN1DPy outer-loop convergence relation.

This operator is intentionally separate from the 10*truncate seed relation
used inside ``kinetic_h``/``kinetic_h2``.  The top-level ``kn1d`` loop compares
the molecular density before and after an outer pass and re-enters while the
relative change is greater than ``truncate``.
"""

from __future__ import annotations

import numpy as np

__all__ = ["evaluate_kn1d_outer_convergence"]


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


def _profile_error(previous, current):
    """Compute the top-level outer-pass max-norm relative change."""
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        return float(np.max(np.abs(current - previous)) / np.max(current))


def evaluate_kn1d_outer_convergence(
    previous_density_m3,
    current_density_m3,
    truncate,
):
    """Evaluate the source top-level ``kn1d`` outer-pass stop condition."""

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
            "top-level outer density profiles must be finite, nonnegative, "
            "aligned, and current density must be positive"
        )

    seed_error = _profile_error(previous, current)
    if not np.isfinite(seed_error):
        raise ValueError("seed_error must be finite")
    threshold = float(truncate)
    should_reiterate = seed_error > threshold
    return {
        "seed_error": seed_error,
        "reentry_threshold": threshold,
        "should_reiterate": should_reiterate,
        "reason": "reiterate" if should_reiterate else "converged",
    }
