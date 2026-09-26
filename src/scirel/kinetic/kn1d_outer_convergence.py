"""Source-free top-level KN1DPy outer-loop convergence relation.

This operator is intentionally separate from the 10*truncate seed relation
used inside ``kinetic_h``/``kinetic_h2``.  The top-level ``kn1d`` loop compares
the molecular density before and after an outer pass and re-enters while the
relative change is greater than ``truncate``.
"""

from __future__ import annotations

import numpy as np


def evaluate_kn1d_outer_convergence(
    previous_density_m3,
    current_density_m3,
    truncate,
):
    """Evaluate the source top-level ``kn1d`` outer-pass stop condition."""

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
            "top-level outer density profiles must be finite, nonnegative, "
            "aligned, and current density must be positive"
        )

    seed_error = float(np.max(np.abs(current - previous)) / np.max(current))
    threshold = float(truncate)
    should_reiterate = seed_error > threshold
    return {
        "seed_error": seed_error,
        "reentry_threshold": threshold,
        "should_reiterate": should_reiterate,
        "reason": "reiterate" if should_reiterate else "converged",
    }


