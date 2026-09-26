"""Molecular scattered-generation source aggregation (wall + CX + elastic).

One leaf recovered from the saved KN1DPy ``分子三通道散射源归约`` package
(source anchor ``KN1DPy/kinetic_h2.py:1422-1546``, the molecular
scattered-source aggregation, as recorded by the saved bundle's own
provenance), integrated as :func:`reduce_molecular_scattered_sources`:

the source-order sum ``Swall + Beta_CX + OmegaM`` of the wall, charge-exchange
and elastic scattered-generation source distributions on one molecular
velocity-space mesh, in the caller's ``(nvr, nvx, nx)`` layout.

**No repair is claimed.**  The saved formal implementation enforces its
declared contract (finite aligned 3-D fields) and is reproduced bit for bit,
messages included.  Signed values are preserved; the three-channel form is
the molecular sibling of the atomic two-channel reduction and is kept as a
separate asset because the wall-source channel exists only on the molecular
side of the saved source.

Evidence ceiling: this module establishes the sum against independent
recomputation, the alignment and signed-value contracts, and -- in the
environment-gated replay test -- exact agreement with the saved KN1DPy
implementation.  The saved bundle's strict D1 qualification has been
withdrawn; that replay is historical development evidence, not qualified-L1
provenance.
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "reduce_molecular_scattered_sources",
]


def reduce_molecular_scattered_sources(
    wall_source_distribution, charge_exchange_source_distribution, elastic_source_distribution
):
    """Return source-order ``Swall + Beta_CX + OmegaM`` on one velocity mesh.

    Parameters
    ----------
    wall_source_distribution, charge_exchange_source_distribution, elastic_source_distribution
        The three scattered-generation source distributions as finite aligned
        ``(nvr, nvx, nx)`` fields; signed values are preserved.

    Returns
    -------
    numpy.ndarray
        Their pointwise sum in the saved source order, same shape.

    Raises
    ------
    ValueError
        If the fields are not finite aligned 3-D arrays.
    """
    sources = [
        np.asarray(source, dtype=float)
        for source in (
            wall_source_distribution,
            charge_exchange_source_distribution,
            elastic_source_distribution,
        )
    ]
    if any(
        source.ndim != 3 or source.shape != sources[0].shape or not np.all(np.isfinite(source))
        for source in sources
    ):
        raise ValueError(
            "wall, charge-exchange, and elastic sources must be finite aligned 3-D fields"
        )
    total = sources[0] + sources[1] + sources[2]
    # Declared r60 pre-review tightening: the saved arm does not gate the sum;
    # extreme-but-valid fields can overflow to non-finite totals.  This asset
    # fail-closes on a non-finite result, per the exact document.
    if not np.all(np.isfinite(total)):
        raise ValueError("the aggregated scattered source is not finite for the supplied inputs")
    return total
