"""KN1DPy finite-generation neutral accumulation state update."""

from __future__ import annotations

import numpy as np


def update_neutral_generation_accumulation(state, generation_distribution, generation_density_m3):
    """Append one source-order generation and preserve source-defined signed fields.

    Moment-compensated Maxwellian fields are allowed to contain signed cells in
    the source contract.  The independently reduced density remains the
    physical nonnegative quantity used by the generation stopping rule.
    """
    distribution = np.asarray(generation_distribution, dtype=float)
    density = np.asarray(generation_density_m3, dtype=float)
    if distribution.ndim != 3 or density.shape != (distribution.shape[2],) or not np.all(np.isfinite(distribution)) or not np.all(np.isfinite(density)) or np.any(density < 0.0):
        raise ValueError("generation distribution must be finite and density must be finite nonnegative aligned fields")
    if state is None:
        distributions, densities = [distribution.copy()], [density.copy()]
        total_distribution, total_density = distribution.copy(), density.copy()
    else:
        distributions = list(state["generation_distributions"])
        densities = list(state["generation_density_m3"])
        total_distribution = np.asarray(state["total_distribution"], dtype=float) + distribution
        total_density = np.asarray(state["total_density_m3"], dtype=float) + density
        distributions.append(distribution.copy())
        densities.append(density.copy())
    return {
        "total_distribution": total_distribution,
        "total_density_m3": total_density,
        "generation_distributions": np.stack(distributions),
        "generation_density_m3": np.stack(densities),
        "completed_generation_index": len(distributions) - 1,
    }
