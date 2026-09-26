"""Elastic regeneration-source aggregation over named channels.

One leaf recovered from the saved KN1DPy ``弹性重生散射源聚合`` package
(source anchors ``KN1DPy/kinetic_h.py:1340-1398`` and
``kinetic_h2.py:1468-1538``, as recorded by the saved bundle's own
provenance), integrated as
:func:`aggregate_elastic_regeneration_source`:

the channel-keyed elastic regeneration sum ``sum_q Omega_q[x] * M_q(vr,vx,x)``
where each named channel contributes its one-dimensional elastic frequency
profile multiplied into its three-dimensional regenerated distribution.

**No repair is claimed.**  The saved formal implementation enforces its
declared contract (frequency and distribution channel key sets must match
exactly, at least one channel, frequencies one-dimensional finite nonnegative
aligned to the distribution's spatial axis, distributions three-dimensional
finite nonnegative) and is reproduced bit for bit, messages included.  The
channel keys are caller-declared identifiers (e.g. species-pair names); the
saved iteration order over a dict is preserved, and dict-like iteration
order therefore affects float summation order exactly as in the saved arm.

Evidence ceiling: this module establishes the aggregation against independent
recomputation, the key/shape/alignment contracts, and -- in the
environment-gated replay test -- exact agreement with the saved KN1DPy
implementation.  The saved bundle's strict D1 qualification has been
withdrawn; that replay is historical development evidence, not qualified-L1
provenance.
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "aggregate_elastic_regeneration_source",
]


def aggregate_elastic_regeneration_source(frequencies_s_inv, regenerated_distributions):
    """Return ``sum_q Omega_q[x] * M_q(vr,vx,x)`` over named channels.

    Parameters
    ----------
    frequencies_s_inv
        A mapping from channel name to a finite nonnegative ``(nx,)``
        frequency profile in ``s^-1``.
    regenerated_distributions
        A mapping from the same channel names to finite nonnegative
        ``(nvr, nvx, nx)`` regenerated distributions; ``nx`` must match the
        frequency profiles.

    Returns
    -------
    numpy.ndarray
        The summed regeneration source, shape ``(nvr, nvx, nx)``.

    Raises
    ------
    ValueError
        If the key sets do not match, no channel is present, or any field
        violates the finiteness, nonnegativity, or alignment contract.
    """
    if set(frequencies_s_inv) != set(regenerated_distributions):
        raise ValueError("frequency and regenerated-distribution channel keys must match")
    result = None
    for key in frequencies_s_inv:
        omega = np.asarray(frequencies_s_inv[key], float)
        distribution = np.asarray(regenerated_distributions[key], float)
        if (
            omega.ndim != 1
            or distribution.ndim != 3
            or distribution.shape[2] != omega.size
            or not np.all(np.isfinite(omega))
            or not np.all(np.isfinite(distribution))
            or np.any(omega < 0)
            or np.any(distribution < 0)
        ):
            raise ValueError(
                "elastic channels must be finite, nonnegative, and (nx)/(nvr,nvx,nx)"
            )
        term = distribution * omega[None, None, :]
        result = term if result is None else result + term
    if result is None:
        raise ValueError("at least one elastic channel is required")
    # Declared r60 pre-review tightening: the saved arm does not gate the sum;
    # extreme-but-valid channels can overflow to non-finite totals.  This
    # asset fail-closes on a non-finite result, per the exact document.
    if not np.all(np.isfinite(result)):
        raise ValueError("the aggregated regeneration source is not finite for the supplied inputs")
    return result
