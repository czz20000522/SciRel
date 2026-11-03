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
            and any(isinstance(item, (bool, np.bool_)) for item in np.asarray(value, dtype=object).flat)
        ):
            raise ValueError
        result = np.asarray(raw, dtype=float)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be a finite real array") from exc
    if not np.all(np.isfinite(result)):
        raise ValueError(f"{name} must be a finite real array")
    return result


def aggregate_elastic_regeneration_source(frequencies_m_inv, regenerated_distributions):
    """Return ``sum_q Omega_q[x] * M_q[vr,vx,x]`` in F/m.

    Each Omega=nu/Vth has units m^-1, and each regenerated M has distribution
    units F, on the same dimensionless u=v/Vth grid. Physical F/s sources
    require a separate multiplication by the caller's common Vth.
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
            distribution = _real_array(
                regenerated_distributions[key], "regenerated_distributions"
            )
            if (
                omega.ndim != 1
                or distribution.ndim != 3
                or distribution.shape[2] != omega.size
                or np.any(omega < 0)
                or np.any(distribution < 0)
            ):
                raise ValueError("elastic channels must be nonnegative and aligned (nx)/(nvr,nvx,nx)")
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
