"""KN1DPy finite-generation neutral accumulation state update."""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np

__all__ = ["update_neutral_generation_accumulation"]


def _finite_real_array(value, name):
    try:
        if isinstance(value, (list, tuple)) and any(
            isinstance(item, (bool, np.bool_)) for item in np.asarray(value, dtype=object).flat
        ):
            raise ValueError
        raw = np.asarray(value)
        if raw.dtype.kind not in "iuf":
            raise ValueError
        result = np.asarray(raw, dtype=float)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be a finite real array") from exc
    if not np.all(np.isfinite(result)):
        raise ValueError(f"{name} must be a finite real array")
    return result


def _validated_state(state, distribution_shape):
    keys = {
        "generation_distributions", "generation_density_m3",
        "total_distribution", "total_density_m3", "completed_generation_index",
    }
    if not isinstance(state, Mapping) or not keys.issubset(state):
        raise ValueError("state must contain the complete accumulation fields")
    distributions = _finite_real_array(state["generation_distributions"], "state.generation_distributions")
    densities = _finite_real_array(state["generation_density_m3"], "state.generation_density_m3")
    total_distribution = _finite_real_array(state["total_distribution"], "state.total_distribution")
    total_density = _finite_real_array(state["total_density_m3"], "state.total_density_m3")
    index = state["completed_generation_index"]
    count = distributions.shape[0] if distributions.ndim == 4 else 0
    if (
        count < 1
        or distributions.shape[1:] != distribution_shape
        or densities.shape != (count, distribution_shape[2])
        or total_distribution.shape != distribution_shape
        or total_density.shape != (distribution_shape[2],)
        or np.any(densities < 0.0)
        or np.any(total_density < 0.0)
        or isinstance(index, (bool, np.bool_))
        or not isinstance(index, (int, np.integer))
        or int(index) != count - 1
    ):
        raise ValueError("state has inconsistent shapes, densities or generation index")
    expected_distribution = distributions[0].copy()
    expected_density = densities[0].copy()
    with np.errstate(over="ignore", invalid="ignore"):
        for generation, generation_density in zip(distributions[1:], densities[1:]):
            expected_distribution += generation
            expected_density += generation_density
    if (
        not np.all(np.isfinite(expected_distribution))
        or not np.all(np.isfinite(expected_density))
        or not np.array_equal(total_distribution, expected_distribution)
        or not np.array_equal(total_density, expected_density)
    ):
        raise ValueError("state totals must match the ordered generation stacks")
    return distributions, densities, total_distribution, total_density


def update_neutral_generation_accumulation(state, generation_distribution, generation_density_m3):
    """Append one source-order generation and preserve source-defined signed fields.

    Moment-compensated Maxwellian fields are allowed to contain signed cells in
    the source contract.  The independently reduced density remains the
    physical nonnegative quantity used by the generation stopping rule.
    """
    distribution = _finite_real_array(generation_distribution, "generation_distribution")
    density = _finite_real_array(generation_density_m3, "generation_density_m3")
    if distribution.ndim != 3 or density.shape != (distribution.shape[2],) or np.any(density < 0.0):
        raise ValueError("generation distribution must be finite and density must be finite nonnegative aligned fields")
    if state is None:
        distributions, densities = distribution[None].copy(), density[None].copy()
        total_distribution, total_density = distribution.copy(), density.copy()
    else:
        prior_distributions, prior_densities, prior_total_distribution, prior_total_density = _validated_state(
            state, distribution.shape,
        )
        with np.errstate(over="ignore", invalid="ignore"):
            total_distribution = prior_total_distribution + distribution
            total_density = prior_total_density + density
        if not np.all(np.isfinite(total_distribution)) or not np.all(np.isfinite(total_density)):
            raise ValueError("accumulated totals must be finite")
        distributions = np.concatenate((prior_distributions, distribution[None]))
        densities = np.concatenate((prior_densities, density[None]))
    return {
        "total_distribution": total_distribution,
        "total_density_m3": total_density,
        "generation_distributions": distributions,
        "generation_density_m3": densities,
        "completed_generation_index": distributions.shape[0] - 1,
    }
