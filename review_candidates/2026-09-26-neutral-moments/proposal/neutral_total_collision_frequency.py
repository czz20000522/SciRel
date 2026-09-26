"""Neutral total-loss collision frequency assembly.

One leaf recovered from the saved KN1DPy ``中性总损失碰撞频率组装`` package
(source anchors ``KN1DPy/kinetic_h.py:1089-1095`` and
``kinetic_h2.py:1151-1157``, as recorded by the saved bundle's own
provenance), integrated as :func:`assemble_neutral_total_collision_frequency`:

the total neutral-loss frequency ``alpha_c`` used by the source's spatial
advance, assembled from an optional charge-exchange field, the base
ionization/dissociation loss profile, the elastic frequency profile, and the
finite-pipe-diameter wall loss ``2 vr / D`` broadcast over the
``(nvr, nvx, nx)`` grid.

**No repair is claimed.**  The saved formal implementation enforces its
declared contract (one-dimensional finite axes with positive radial nodes,
finite base/elastic/diameter profiles of one common spatial shape with
nonnegative values, and -- when charge exchange is enabled -- a finite
nonnegative ``(nvr, nvx, nx)`` charge-exchange field) and is reproduced bit
for bit, messages included.  Two saved behaviors are preserved exactly:

- a zero pipe diameter yields zero wall loss in those spatial cells (no
  repair to an infinite-pipe limit), and
- ``charge_exchange_enabled=True`` with a missing field fails closed
  (``ValueError``); ``charge_exchange_enabled=False`` skips the field even
  when one is supplied.

Evidence ceiling: this module establishes the assembly against independent
recomputation, the wall-loss broadcast, and -- in the environment-gated
replay test -- exact agreement with the saved KN1DPy implementation.  The
saved bundle's strict D1 qualification has been withdrawn; that replay is
historical development evidence, not qualified-L1 provenance.
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "assemble_neutral_total_collision_frequency",
]


def assemble_neutral_total_collision_frequency(
    vr,
    vx,
    base_loss_frequency_s_inv,
    elastic_frequency_s_inv,
    pipe_diameter_m,
    charge_exchange_frequency_s_inv=None,
    charge_exchange_enabled=True,
):
    """Return alpha_c = optional Alpha_CX + base loss + Omega_EL + wall loss.

    Parameters
    ----------
    vr, vx
        The radial and axial velocity axes: finite one-dimensional arrays;
        radial nodes must be positive.
    base_loss_frequency_s_inv, elastic_frequency_s_inv, pipe_diameter_m
        Finite one-dimensional profiles of one common spatial shape ``(nx,)``;
        base loss, elastic frequency, and pipe diameter (``s^-1``, ``s^-1``,
        ``m``), all nonnegative.
    charge_exchange_frequency_s_inv
        The charge-exchange frequency field, shape ``(nvr, nvx, nx)``;
        required (and must be finite and nonnegative) exactly when
        ``charge_exchange_enabled`` is true.
    charge_exchange_enabled
        Whether the charge-exchange contribution is included.

    Returns
    -------
    numpy.ndarray
        The total loss frequency, shape ``(nvr, nvx, nx)``.

    Raises
    ------
    ValueError
        If any contract above is violated.
    """
    radial = np.asarray(vr, dtype=float)
    axial = np.asarray(vx, dtype=float)
    base = np.asarray(base_loss_frequency_s_inv, dtype=float)
    elastic = np.asarray(elastic_frequency_s_inv, dtype=float)
    diameter = np.asarray(pipe_diameter_m, dtype=float)
    if (
        radial.ndim != 1
        or axial.ndim != 1
        or base.ndim != 1
        or elastic.shape != base.shape
        or diameter.shape != base.shape
        or radial.size == 0
        or axial.size == 0
        or not np.all(np.isfinite(radial))
        or not np.all(np.isfinite(axial))
        or not np.all(np.isfinite(base))
        or not np.all(np.isfinite(elastic))
        or not np.all(np.isfinite(diameter))
        or np.any(radial <= 0.0)
        or np.any(base < 0.0)
        or np.any(elastic < 0.0)
        or np.any(diameter < 0.0)
    ):
        raise ValueError("velocity axes and base/elastic/pipe profiles are invalid")
    shape = (radial.size, axial.size, base.size)
    wall = np.zeros(shape, dtype=float)
    positive_diameter = diameter > 0.0
    wall[:, :, positive_diameter] = (
        2.0 * radial[:, None, None] / diameter[None, None, positive_diameter]
    )
    total = base[None, None, :] + elastic[None, None, :] + wall
    if charge_exchange_enabled:
        if charge_exchange_frequency_s_inv is None:
            raise ValueError("enabled charge exchange needs its explicit frequency field")
        charge_exchange = np.asarray(charge_exchange_frequency_s_inv, dtype=float)
        if (
            charge_exchange.shape != shape
            or not np.all(np.isfinite(charge_exchange))
            or np.any(charge_exchange < 0.0)
        ):
            raise ValueError(
                "charge-exchange frequency must be finite, nonnegative, and (nvr,nvx,nx)"
            )
        total = total + charge_exchange
    # Declared r60 pre-review tightening: the saved arm does not gate the
    # total; an extreme vr/Diameter ratio can overflow the wall loss to inf.
    # This asset fail-closes on a non-finite total, per the exact document.
    if not np.all(np.isfinite(total)):
        raise ValueError("the assembled total loss frequency is not finite for the supplied inputs")
    return total
