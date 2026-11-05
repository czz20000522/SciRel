"""Sum inverse-length elastic coefficients times distribution densities."""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np

__all__ = ["aggregate_elastic_regeneration_source"]


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


def aggregate_elastic_regeneration_source(frequencies_m_inv, regenerated_distributions):
    r"""Aggregate normalized elastic regeneration sources sum_q Omega_q[x]*M_q(u_r,u_x,x), with Omega_q=nu_q/Vth in m^-1 and caller distributions M_q in m^-3.

    Parameters
    ----------
    frequencies_m_inv : mapping of real array-like, shape mapping name->[nx]
        Per-channel inverse-length elastic coefficients Omega_q=nu_q/Vth, using one common Vth. [m^-1].
        Constraints: Finite and nonnegative; keys must match the distribution mapping exactly.
    regenerated_distributions : mapping of real array-like, shape mapping name->[nvr,nvx,nx]
        The per-channel regenerated distributions. [m^-3].
        Constraints: Finite and nonnegative; all channels use the same (nvr,nvx,nx) shape, and each spatial axis matches its frequency profile.

    Returns
    -------
    regeneration_source : float64 array, shape [nvr,nvx,nx]
        The aggregated regeneration source. [m^-4 (F/m)].
        Constraints: Finite and nonnegative; the channel sum in dict iteration order.

    Raises
    ------
    ValueError
        Raises ValueError for non-mapping, mismatched or empty channels; implicit boolean, string or complex conversion; negative or non-finite fields; or distributions that do not share one (nvr,nvx,nx) mesh. Raises ValueError when the evaluation produces a non-finite result where the contract demands finiteness; no fallback is selected. Not applicable. Never returned; a rejected call produces no result.

    See Also
    --------
    scirel.kinetic.reduce_atomic_scattered_sources : Related neutral-transport operation.

    Notes
    -----
        The frequency and distribution key sets must match exactly; each term multiplies the (nx,) profile into the last axis; the dict iteration order defines the float summation order
    matching nonempty key sets; finite nonnegative (nx,) frequencies; finite nonnegative (nvr,nvx,nx) distributions on one shared velocity and spatial mesh

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.kinetic import aggregate_elastic_regeneration_source
    >>> freqs = {'a': np.array([1.0, 2.0]), 'b': np.array([0.5, 1.0])}
    >>> dists = {'a': np.ones((1, 1, 2)), 'b': np.ones((1, 1, 2))}
    >>> result = aggregate_elastic_regeneration_source(freqs, dists)
    >>> np.testing.assert_array_equal(result, [[[1.5, 3.0]]])
    >>> try:
    ...     aggregate_elastic_regeneration_source(freqs, {'a': np.ones((1, 1, 2))})
    ... except ValueError as error:
    ...     assert 'channel keys must match' in str(error)
    ... else:
    ...     raise AssertionError('mismatched keys must be rejected')
    """
    if not isinstance(frequencies_m_inv, Mapping) or not isinstance(
        regenerated_distributions, Mapping
    ):
        raise ValueError("frequencies_m_inv and regenerated_distributions must be mappings")
    if set(frequencies_m_inv) != set(regenerated_distributions):
        raise ValueError("frequency and regenerated-distribution channel keys must match")
    if not frequencies_m_inv:
        raise ValueError("at least one elastic channel is required")
    terms = []
    common_shape = None
    with np.errstate(over="ignore", invalid="ignore"):
        for key in frequencies_m_inv:
            omega = _real_array(frequencies_m_inv[key], "frequencies_m_inv")
            distribution = _real_array(regenerated_distributions[key], "regenerated_distributions")
            if (
                omega.ndim != 1
                or distribution.ndim != 3
                or distribution.shape[2] != omega.size
                or np.any(omega < 0)
                or np.any(distribution < 0)
            ):
                raise ValueError(
                    "elastic channels must be nonnegative and aligned (nx)/(nvr,nvx,nx)"
                )
            if common_shape is None:
                common_shape = distribution.shape
            elif distribution.shape != common_shape:
                raise ValueError("regenerated distributions must share one velocity mesh")
            terms.append(distribution * omega[None, None, :])
    result = terms[0].copy()
    for term in terms[1:]:
        # Keep channel insertion order explicit: floating-point accumulation
        # is part of the reproducible source contract.
        result += term
    if not np.all(np.isfinite(result)):
        raise ValueError("the aggregated regeneration source must be finite")
    return result
