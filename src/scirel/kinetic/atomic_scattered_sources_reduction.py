"""Atomic scattered source sum on one velocity and spatial mesh."""

from __future__ import annotations

import numpy as np

__all__ = ["reduce_atomic_scattered_sources"]


def _real_array(value, name):
    try:
        raw = np.asarray(value)
        if raw.dtype.kind not in "iuf" or (
            isinstance(value, (list, tuple))
            and any(
                isinstance(item, (bool, np.bool_)) for item in np.asarray(value, dtype=object).flat
            )
        ):
            raise ValueError
        result = np.asarray(raw, dtype=float)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be a finite real array") from exc
    if not np.all(np.isfinite(result)):
        raise ValueError(f"{name} must be a finite real array")
    return result


def _sum_source_channels(charge_exchange, elastic):
    """Add the two signed source channels in their declared order."""
    return charge_exchange + elastic


def reduce_atomic_scattered_sources(
    charge_exchange_source_distribution, elastic_source_distribution
):
    r"""The pointwise sum Beta_CX + OmegaM of the atomic charge-exchange and elastic scattered-generation normalized spatial source distributions (Q/Vth, in F/m) on one velocity-space mesh, preserving signed values.

    Parameters
    ----------
    charge_exchange_source_distribution : real array-like, shape [nvr,nvx,nx]
        The CX scattered source. [m^-4 (F/m)].
        Constraints: A finite three-dimensional field; signed values preserved.
    elastic_source_distribution : real array-like, shape [nvr,nvx,nx]
        The elastic scattered source. [m^-4 (F/m)].
        Constraints: A finite three-dimensional field aligned to the CX field; signed values preserved.

    Returns
    -------
    total_source : float64 array, shape [nvr,nvx,nx]
        The aggregated scattered source. [m^-4 (F/m)].
        Constraints: The pointwise sum; finite; signed values preserved.

    Raises
    ------
    ValueError
        Raises ValueError for non-real/boolean/string/complex or nonfinite source values, or when the two sources are not aligned 3-D arrays. Raises ValueError when the pointwise sum is not finite; no clipping or fallback is applied. Not applicable; the reduction is a direct pointwise sum. Never returned; a rejected call produces no partial array.

    See Also
    --------
    scirel.kinetic.assemble_simple_charge_exchange_source : Related neutral-transport operation.

    Notes
    -----
        Plain pointwise addition; no clamping of signed values
    two finite aligned three-dimensional fields; signed values preserved

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.kinetic import reduce_atomic_scattered_sources
    >>> source = np.ones((1, 2, 3))
    >>> np.testing.assert_allclose(reduce_atomic_scattered_sources(source, 2 * source), 3 * source)
    >>> np.testing.assert_allclose(reduce_atomic_scattered_sources(source, -source), np.zeros_like(source))
    >>> try:
    ...     reduce_atomic_scattered_sources(source, np.ones((1, 2, 4)))
    ... except ValueError as error:
    ...     assert 'finite aligned 3-D' in str(error)
    ... else:
    ...     raise AssertionError('a misaligned field must be rejected')
    """
    charge_exchange = _real_array(
        charge_exchange_source_distribution, "charge_exchange_source_distribution"
    )
    elastic = _real_array(elastic_source_distribution, "elastic_source_distribution")
    if charge_exchange.ndim != 3 or elastic.shape != charge_exchange.shape:
        raise ValueError("charge-exchange and elastic sources must be finite aligned 3-D fields")
    with np.errstate(over="ignore", invalid="ignore"):
        total = _sum_source_channels(charge_exchange, elastic)
    if not np.all(np.isfinite(total)):
        raise ValueError("the aggregated scattered source must be finite")
    return total
