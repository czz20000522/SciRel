"""the neutral-transport formulation finite-generation neutral accumulation state update."""

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
        "generation_distributions",
        "generation_density_m3",
        "total_distribution",
        "total_density_m3",
        "completed_generation_index",
    }
    if not isinstance(state, Mapping) or not keys.issubset(state):
        raise ValueError("state must contain the complete accumulation fields")
    distributions = _finite_real_array(
        state["generation_distributions"], "state.generation_distributions"
    )
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
    expected_distribution, expected_density = _ordered_totals(distributions, densities)
    if (
        not np.all(np.isfinite(expected_distribution))
        or not np.all(np.isfinite(expected_density))
        or not np.array_equal(total_distribution, expected_distribution)
        or not np.array_equal(total_density, expected_density)
    ):
        raise ValueError("state totals must match the ordered generation stacks")
    return distributions, densities, total_distribution, total_density


def _ordered_totals(distributions, densities):
    """Accumulate generation stacks in source order for reproducible sums."""
    total_distribution = distributions[0].copy()
    total_density = densities[0].copy()
    with np.errstate(over="ignore", invalid="ignore"):
        for generation, generation_density in zip(distributions[1:], densities[1:]):
            total_distribution += generation
            total_density += generation_density
    return total_distribution, total_density


def update_neutral_generation_accumulation(state, generation_distribution, generation_density_m3):
    r"""Append one generation to the accumulated state: accumulates distribution, density, per-generation stacks, and the completed generation index.

    Parameters
    ----------
    state : mapping of arrays and an integer, shape mapping or None
        The previous accumulation state (or None for first call). [source-discrete].
        Constraints: When supplied, must contain generation_distributions [ngen,nvr,nvx,nx], generation_density_m3 [ngen,nx], total_distribution [nvr,nvx,nx], total_density_m3 [nx], and a zero-based integer completed_generation_index equal to ngen-1. Arrays must be finite and aligned; densities nonnegative; totals must equal the ordered sum of their stacks.
    generation_distribution : real array-like, shape [nvr,nvx,nx]
        The current generation distribution. [source-discrete].
        Constraints: A finite three-dimensional array.
    generation_density_m3 : real array-like, shape [nx]
        The current generation density profile. [m^-3].
        Constraints: A finite nonnegative one-dimensional array aligned to the distribution spatial axis.

    Returns
    -------
    result : mapping of arrays and an integer, shape mapping
        A mapping with total_distribution, total_density_m3, generation_distributions (stacked), generation_density_m3 (stacked), and completed_generation_index. [source-discrete].
        Constraints: All arrays finite; total_distribution and total_density_m3 equal ordered sums of their generation stacks; density arrays nonnegative; completed_generation_index is the 0-based index of the last appended generation.

    Raises
    ------
    ValueError
        Raises ValueError for non-real, non-finite or misaligned generation fields, negative density, or an incomplete or internally inconsistent supplied state. Raises ValueError if adding finite generations overflows an accumulated total. Not applicable; this relation appends one generation and does not iterate. Never returned; a rejected call produces no result.

    See Also
    --------
    scirel.kinetic.propagate_neutral_generation : Related neutral-transport operation.

    Notes
    -----
        Append one generation to the accumulated state: accumulates distribution, density, per-generation stacks, and the completed generation index.
    finite real 3-D generation distribution (signed cells allowed), aligned finite nonnegative 1-D generation density, and either None or a complete finite internally consistent prior accumulation state

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.kinetic import update_neutral_generation_accumulation
    >>> dist1 = np.ones((1, 1, 2))
    >>> dens1 = np.array([1.0, 2.0])
    >>> state1 = update_neutral_generation_accumulation(None, dist1, dens1)
    >>> assert state1['completed_generation_index'] == 0
    >>> dist2 = np.ones((1, 1, 2)) * 2
    >>> dens2 = np.array([2.0, 4.0])
    >>> state2 = update_neutral_generation_accumulation(state1, dist2, dens2)
    >>> assert state2['completed_generation_index'] == 1
    >>> np.testing.assert_array_equal(state2['total_distribution'], dist1 + dist2)
    >>> np.testing.assert_array_equal(state2['total_density_m3'], dens1 + dens2)
    """
    distribution = _finite_real_array(generation_distribution, "generation_distribution")
    density = _finite_real_array(generation_density_m3, "generation_density_m3")
    if distribution.ndim != 3 or density.shape != (distribution.shape[2],) or np.any(density < 0.0):
        raise ValueError(
            "generation distribution must be finite and density must be finite nonnegative aligned fields"
        )
    if state is None:
        distributions, densities = distribution[None].copy(), density[None].copy()
        total_distribution, total_density = distribution.copy(), density.copy()
    else:
        prior_distributions, prior_densities, prior_total_distribution, prior_total_density = (
            _validated_state(
                state,
                distribution.shape,
            )
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
