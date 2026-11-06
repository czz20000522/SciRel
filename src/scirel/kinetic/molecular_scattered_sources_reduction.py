"""Molecular scattered source sum on one velocity and spatial mesh."""

from __future__ import annotations

import numpy as np

__all__ = ["reduce_molecular_scattered_sources"]


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


def reduce_molecular_scattered_sources(
    wall_source_distribution, charge_exchange_source_distribution, elastic_source_distribution
):
    r"""The source-order sum Swall + Beta_CX + OmegaM of the molecular wall, charge-exchange and elastic scattered-generation normalized spatial source distributions (Q/Vth, in F/m) on one velocity-space mesh, preserving signed values.

    Parameters
    ----------
    wall_source_distribution : real array-like, shape [nvr,nvx,nx]
        The wall scattered source. [m^-4 (F/m)].
        Constraints: A finite three-dimensional field; signed values preserved.
    charge_exchange_source_distribution : real array-like, shape [nvr,nvx,nx]
        The CX scattered source. [m^-4 (F/m)].
        Constraints: A finite three-dimensional field aligned to the wall field.
    elastic_source_distribution : real array-like, shape [nvr,nvx,nx]
        The elastic scattered source. [m^-4 (F/m)].
        Constraints: A finite three-dimensional field aligned to the wall field.

    Returns
    -------
    total_source : float64 array, shape [nvr,nvx,nx]
        The aggregated scattered source. [m^-4 (F/m)].
        Constraints: The pointwise sum in the declared order; finite; signed values preserved.

    Raises
    ------
    ValueError
        Raises ValueError for non-real/boolean/string/complex or nonfinite source values, or when the three sources are not aligned 3-D arrays. Raises ValueError when the signed aggregate is not finite; no clipping, channel drop or fallback is applied. Not applicable; the reduction is a direct pointwise sum. Never returned; a rejected call produces no partial array.

    See Also
    --------
    scirel.kinetic.reduce_atomic_scattered_sources : Related neutral-transport operation.

    Notes
    -----
        Plain pointwise addition in the order wall, CX, elastic; no clamping of signed values
    three finite aligned three-dimensional fields; signed values preserved

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.kinetic import reduce_molecular_scattered_sources
    >>> rng = np.random.default_rng(31)
    >>> wall, cx, elastic = (rng.random((2, 3, 4)) for _ in range(3))
    >>> result = reduce_molecular_scattered_sources(wall, cx, elastic)
    >>> np.testing.assert_array_equal(result, wall + cx + elastic)
    >>> try:
    ...     reduce_molecular_scattered_sources(wall, cx, np.ones((2, 3, 5)))
    ... except ValueError as error:
    ...     assert 'finite aligned 3-D' in str(error)
    ... else:
    ...     raise AssertionError('a misaligned field must be rejected')
    """
    fields = (
        ("wall_source_distribution", wall_source_distribution),
        ("charge_exchange_source_distribution", charge_exchange_source_distribution),
        ("elastic_source_distribution", elastic_source_distribution),
    )
    sources = [_real_array(value, name) for name, value in fields]
    if sources[0].ndim != 3 or any(source.shape != sources[0].shape for source in sources):
        raise ValueError(
            "wall, charge-exchange, and elastic sources must be finite aligned 3-D fields"
        )
    with np.errstate(over="ignore", invalid="ignore"):
        total = (sources[0] + sources[1]) + sources[2]
    if not np.all(np.isfinite(total)):
        raise ValueError("the aggregated scattered source must be finite")
    return total
