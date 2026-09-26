"""Atomic scattered-generation source aggregation (CX + elastic).

One leaf recovered from the saved KN1DPy ``原子双通道散射源归约`` package
(source anchor ``KN1DPy/kinetic_h.py:1297-1317``, the atomic scattered-source
aggregation, as recorded by the saved bundle's own provenance), integrated as
:func:`reduce_atomic_scattered_sources`:

the source-order sum ``Beta_CX + OmegaM`` of the charge-exchange and elastic
scattered-generation source distributions on one atomic velocity-space mesh,
in the caller's ``(nvr, nvx, nx)`` layout.

**No repair is claimed.**  The saved formal implementation enforces its
declared contract (finite aligned 3-D fields) and is reproduced bit for bit,
messages included.  Signed values are preserved: the inputs are source
distributions that may carry negative entries from upstream normalizations,
and the sum is their plain pointwise addition without clamping.

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
    "reduce_atomic_scattered_sources",
]


def reduce_atomic_scattered_sources(
    charge_exchange_source_distribution, elastic_source_distribution
):
    """Return source-order ``Beta_CX + OmegaM`` on one atomic velocity mesh.

    Parameters
    ----------
    charge_exchange_source_distribution, elastic_source_distribution
        The two scattered-generation source distributions as finite aligned
        ``(nvr, nvx, nx)`` fields; signed values are preserved.

    Returns
    -------
    numpy.ndarray
        Their pointwise sum, same shape.

    Raises
    ------
    ValueError
        If the fields are not finite aligned 3-D arrays.
    """
    charge_exchange = np.asarray(charge_exchange_source_distribution, dtype=float)
    elastic = np.asarray(elastic_source_distribution, dtype=float)
    if (
        charge_exchange.ndim != 3
        or elastic.shape != charge_exchange.shape
        or not np.all(np.isfinite(charge_exchange))
        or not np.all(np.isfinite(elastic))
    ):
        raise ValueError(
            "charge-exchange and elastic sources must be finite aligned 3-D fields"
        )
    total = charge_exchange + elastic
    # Declared r60 pre-review tightening: the saved arm does not gate the sum;
    # extreme-but-valid fields can overflow to non-finite totals.  This asset
    # fail-closes on a non-finite result, per the exact document.
    if not np.all(np.isfinite(total)):
        raise ValueError("the aggregated scattered source is not finite for the supplied inputs")
    return total
