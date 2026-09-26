"""Simple charge-exchange scattered-generation source.

One leaf recovered from the saved KN1DPy ``简化电荷交换散射源`` package (source
anchors ``KN1DPy/kinetic_h.py:1297-1317`` and ``kinetic_h2.py:1444-1461``,
the ``Simple_CX`` scattered-generation construction, as recorded by the saved
bundle's own provenance), integrated as
:func:`assemble_simple_charge_exchange_source`:

the cell-local charge-exchange source ``target * rate`` where the rate is
the quadrature contraction of the charge-exchange frequency field with the
previous generation's distribution,
``rate[x] = sum over (vr, vx) of weight * alpha * previous * dvx``, and the
result reproduces the target distribution's shape scaled per spatial cell.

**No repair is claimed.**  The saved formal implementation enforces its
declared contract (finite aligned 3-D target/frequency/previous fields, a
two-dimensional cylindrical weight aligned to the leading axes, a
one-dimensional nonnegative ``dvx`` aligned to the velocity axis, nonnegative
frequency, weight and ``dvx``) and is reproduced bit for bit, messages
included.  The reduction is cell-local: no cross-cell transport enters here,
matching the saved source's per-generation scattering step.

Evidence ceiling: this module establishes the construction against
independent recomputation of the quadrature contraction, the alignment
contracts, and -- in the environment-gated replay test -- exact agreement
with the saved KN1DPy implementation.  The saved bundle's strict D1
qualification has been withdrawn; that replay is historical development
evidence, not qualified-L1 provenance.
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "assemble_simple_charge_exchange_source",
]


def assemble_simple_charge_exchange_source(
    target_distribution,
    charge_exchange_frequency_s_inv,
    previous_generation_distribution,
    cylindrical_weight,
    dvx,
):
    """Return the cell-local ``target * sum(weight * alpha * previous * dvx)``.

    Parameters
    ----------
    target_distribution
        The target distribution as a finite ``(nvr, nvx, nx)`` array.
    charge_exchange_frequency_s_inv
        The charge-exchange frequency field, finite nonnegative, shape
        ``(nvr, nvx, nx)``.
    previous_generation_distribution
        The previous generation's distribution, finite, shape
        ``(nvr, nvx, nx)``.
    cylindrical_weight
        The cylindrical quadrature weight, finite nonnegative, shape
        ``(nvr, nvx)``.
    dvx
        The axial cell sizes, finite nonnegative, shape ``(nvx,)``.

    Returns
    -------
    numpy.ndarray
        The scattered-generation source, shape ``(nvr, nvx, nx)``.

    Raises
    ------
    ValueError
        If any field is non-finite or the alignment/nonnegativity contract
        is violated.
    """
    target = np.asarray(target_distribution, float)
    alpha = np.asarray(charge_exchange_frequency_s_inv, float)
    previous = np.asarray(previous_generation_distribution, float)
    weight = np.asarray(cylindrical_weight, float)
    dvx = np.asarray(dvx, float)
    if (
        target.ndim != 3
        or alpha.shape != target.shape
        or previous.shape != target.shape
        or weight.shape != target.shape[:2]
        or dvx.shape != (target.shape[1],)
        or not all(np.all(np.isfinite(x)) for x in (target, alpha, previous, weight, dvx))
        or np.any(alpha < 0)
        or np.any(weight < 0)
        or np.any(dvx < 0)
    ):
        raise ValueError(
            "Simple_CX fields must be finite and aligned; rates and quadrature must be nonnegative"
        )
    rate = np.sum(weight[:, :, None] * alpha * previous * dvx[None, :, None], axis=(0, 1))
    result = target * rate[None, None, :]
    # Declared r60 pre-review tightening: the saved arm does not gate the
    # product; extreme-but-valid inputs can overflow to non-finite sources.
    # This asset fail-closes on a non-finite result, per the exact document.
    if not np.all(np.isfinite(result)):
        raise ValueError("the assembled scattered source is not finite for the supplied inputs")
    return result
