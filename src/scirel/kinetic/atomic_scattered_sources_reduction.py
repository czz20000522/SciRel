"""Atomic scattered source sum on one velocity and spatial mesh."""

from __future__ import annotations

import numpy as np

__all__ = ["reduce_atomic_scattered_sources"]


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


def _sum_source_channels(charge_exchange, elastic):
    """Add the two signed source channels in their declared order."""
    return charge_exchange + elastic


def reduce_atomic_scattered_sources(
    charge_exchange_source_distribution, elastic_source_distribution
):
    """Return normalized spatial ``Beta_CX + OmegaM`` in F/m.

    Both inputs use one common dimensionless u=v/Vth velocity grid and are
    physical distribution-rate sources divided by that Vth. Signed cells
    and the declared addition order are retained.
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
