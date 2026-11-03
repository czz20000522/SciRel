"""Molecular scattered source sum on one velocity and spatial mesh."""

from __future__ import annotations

import numpy as np

__all__ = ["reduce_molecular_scattered_sources"]


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


def reduce_molecular_scattered_sources(
    wall_source_distribution, charge_exchange_source_distribution, elastic_source_distribution
):
    """Return normalized spatial ``Swall + Beta_CX + OmegaM`` in F/m.

    All inputs use one common dimensionless u=v/Vth velocity grid and are
    physical distribution-rate sources divided by that Vth. Signed cells
    and the declared addition order are retained.
    """
    fields = (
        ("wall_source_distribution", wall_source_distribution),
        ("charge_exchange_source_distribution", charge_exchange_source_distribution),
        ("elastic_source_distribution", elastic_source_distribution),
    )
    sources = [_real_array(value, name) for name, value in fields]
    if sources[0].ndim != 3 or any(source.shape != sources[0].shape for source in sources):
        raise ValueError("wall, charge-exchange, and elastic sources must be finite aligned 3-D fields")
    with np.errstate(over="ignore", invalid="ignore"):
        total = (sources[0] + sources[1]) + sources[2]
    if not np.all(np.isfinite(total)):
        raise ValueError("the aggregated scattered source must be finite")
    return total
