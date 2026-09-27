"""Atomic scattered source sum on one velocity and spatial mesh."""

from __future__ import annotations

import numpy as np


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


def reduce_atomic_scattered_sources(
    charge_exchange_source_distribution, elastic_source_distribution
):
    """Return source-order ``Beta_CX + OmegaM`` with signed cells retained."""
    charge_exchange = _real_array(
        charge_exchange_source_distribution, "charge_exchange_source_distribution"
    )
    elastic = _real_array(elastic_source_distribution, "elastic_source_distribution")
    if charge_exchange.ndim != 3 or elastic.shape != charge_exchange.shape:
        raise ValueError("charge-exchange and elastic sources must be finite aligned 3-D fields")
    with np.errstate(over="ignore", invalid="ignore"):
        total = charge_exchange + elastic
    if not np.all(np.isfinite(total)):
        raise ValueError("the aggregated scattered source must be finite")
    return total
