"""Pointwise sum of the three elastic collision-frequency channels.

One leaf recovered from the saved KN1DPy ``弹性频率通道求和`` package (source
anchors ``KN1DPy/kinetic_h.py:1297-1317`` and ``kinetic_h2.py:1258-1297``,
the Omega-channel total of the atomic and molecular generation graphs, as
recorded by the saved bundle's own provenance), integrated as
:func:`sum_elastic_frequency_channels`:

the pointwise sum of exactly three already-normalized elastic collision
frequency channels (e.g. the species-pair Omega evaluations upstream) into
the transport total elastic frequency in ``s^-1``.

**No repair is claimed for the saved arithmetic; one declared narrowing is
recorded.**  The saved formal implementation enforces its declared contract
(exactly three channels, non-empty finite equal-shape arrays) and the sum is
reproduced bit for bit on the declared domain, messages included.  The saved
arm does not gate the sum's finiteness: three near-maximum finite channels
(e.g. ``1e308`` each) overflow to ``inf`` and are returned.  This asset
fail-closes on a non-finite total instead, per its exact document's finite-
output contract; the divergence is pinned by a regression test and the
saved-arm behavior is preserved as evidence.

Evidence ceiling: this module establishes the sum against independent
recomputation, the channel/shape contracts, and -- in the environment-gated
replay test -- exact agreement with the saved KN1DPy implementation.  The
saved bundle's strict D1 qualification has been withdrawn; that replay is
historical development evidence, not qualified-L1 provenance.
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "sum_elastic_frequency_channels",
]


def sum_elastic_frequency_channels(frequency_profiles):
    """Return the pointwise sum of exactly three frequency profiles.

    Parameters
    ----------
    frequency_profiles
        A sequence of exactly three finite, non-empty, equal-shape
        array-like frequency profiles in ``s^-1``, in caller order.

    Returns
    -------
    dict
        ``{'elastic_frequency_s_inv': ndarray}`` with the pointwise sum.

    Raises
    ------
    ValueError
        If the channel count, emptiness, shapes, or finiteness contract is
        violated.
    """
    if not isinstance(frequency_profiles, (list, tuple)) or len(frequency_profiles) != 3:
        raise ValueError("frequency_profiles must contain exactly three channels")
    arrays = [np.asarray(profile, dtype=float) for profile in frequency_profiles]
    if any(array.ndim == 0 or array.size == 0 for array in arrays):
        raise ValueError("frequency channels must be non-empty arrays")
    shape = arrays[0].shape
    if any(array.shape != shape for array in arrays):
        raise ValueError("frequency channels must have identical shapes")
    if any(not np.all(np.isfinite(array)) for array in arrays):
        raise ValueError("frequency channels must be finite")
    with np.errstate(over="ignore"):
        total = arrays[0] + arrays[1] + arrays[2]
    # Declared narrowing (r60 pre-review): the saved arm returns the overflow
    # value; this asset fail-closes on the non-finite total instead, matching
    # the exact document's runtime_failure contract.
    if not np.all(np.isfinite(total)):
        raise ValueError("the summed elastic frequency is not finite for the supplied channels")
    return {"elastic_frequency_s_inv": total}
