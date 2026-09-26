"""KN1DPy H/H2 collision-generation stopping criterion."""
from __future__ import annotations

import numpy as np


def evaluate_neutral_generation_stopping(generation_density_m3, accumulated_density_m3, truncate, seed_iteration_enabled=False, seed_error=None):
    """Return source Delta_n and whether the next collision generation is unnecessary."""
    generation = np.asarray(generation_density_m3, dtype=float)
    accumulated = np.asarray(accumulated_density_m3, dtype=float)
    if generation.shape != accumulated.shape or generation.ndim != 1 or np.any(generation < 0.0) or np.any(accumulated < 0.0) or not np.all(np.isfinite(generation)) or not np.all(np.isfinite(accumulated)) or truncate <= 0.0:
        raise ValueError("density vectors must be finite/nonnegative and truncate positive")
    maximum = float(np.max(accumulated))
    if maximum <= 0.0:
        raise ValueError("accumulated_density_m3 must contain a positive value")
    delta = float(np.max(generation) / maximum)
    if delta < truncate:
        return delta, True, "truncate"
    if seed_iteration_enabled:
        if seed_error is None or seed_error < 0.0 or not np.isfinite(seed_error):
            raise ValueError("seed iteration needs a finite nonnegative seed_error")
        if delta < 0.003 * seed_error:
            return delta, True, "seed_relative"
    return delta, False, "continue"
