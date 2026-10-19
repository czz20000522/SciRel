"""KN1DPy H/H2 collision-generation stopping criterion."""
from __future__ import annotations

import numpy as np

__all__ = ["evaluate_neutral_generation_stopping"]


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


def _relative_generation_change(generation, accumulated):
    """Return the source-defined max-norm generation ratio."""
    with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
        return float(np.max(generation) / np.max(accumulated))


def evaluate_neutral_generation_stopping(generation_density_m3, accumulated_density_m3, truncate, seed_iteration_enabled=False, seed_error=None):
    """Return source Delta_n and whether the next collision generation is unnecessary."""
    generation = _finite_real(generation_density_m3, "generation_density_m3")
    accumulated = _finite_real(accumulated_density_m3, "accumulated_density_m3")
    truncate = _finite_real(truncate, "truncate", scalar=True)
    if generation.shape != accumulated.shape or generation.ndim != 1 or generation.size == 0 or np.any(generation < 0.0) or np.any(accumulated < 0.0) or truncate <= 0.0:
        raise ValueError("density vectors must be finite/nonnegative and truncate positive")
    if not isinstance(seed_iteration_enabled, (bool, np.bool_)):
        raise ValueError("seed_iteration_enabled must be a boolean scalar")
    if seed_iteration_enabled:
        if seed_error is None:
            raise ValueError("seed_error is required when seed iteration is enabled")
        seed_error = _finite_real(seed_error, "seed_error", scalar=True)
        if seed_error < 0.0:
            raise ValueError("seed_error must be nonnegative")
    elif seed_error is not None:
        raise ValueError("seed_error must be None when seed iteration is disabled")
    maximum = float(np.max(accumulated))
    if maximum <= 0.0:
        raise ValueError("accumulated_density_m3 must contain a positive value")
    delta = _relative_generation_change(generation, accumulated)
    if not np.isfinite(delta):
        raise ValueError("delta must be finite")
    if delta < truncate:
        return delta, True, "truncate"
    if seed_iteration_enabled:
        if delta < 0.003 * seed_error:
            return delta, True, "seed_relative"
    return delta, False, "continue"
