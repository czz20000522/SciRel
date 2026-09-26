"""Source-free atomic collision-matrix assembly (SIG four-family).

Reproduces the double-velocity-space (``vr,vx``) x (``vr',vx'``) collision-operator
assembly of KN1DPy ``kinetic_h.py:888-1018`` for the atomic four families:

- ``SIG_CX``   : H + H+  charge exchange,    weight ``Vr2pidVrdVx``
- ``SIG_H_H``  : H-H     elastic, viscosity  weight ``Vr2pidVrdVx``
- ``SIG_H_H2`` : H-H2    elastic,            weight ``Vr2pidVrdVx * vx_vx``
- ``SIG_H_P``  : H-H+    elastic,            weight ``Vr2pidVrdVx * vx_vx``

All reshapes are performed in Fortran order (``order='F'``) exactly as the source
legacy ``Work`` buffer does.  The cross-section fits are reused from the
integrated ``scirel.collisions`` leaves (coefficient- and clip-identical).  On a
200,011-point energy probe spanning the union of the declared fit domains
(including every clip endpoint, the H-P 10 eV branch boundary and E = 0) the
three elastic families of this arm match the source-embedded fits bit for bit,
while the arm's charge-exchange family differs by at most a 2.22e-15 relative
deviation -- root-caused to the standardized ``np.exp`` evaluation versus the
source's ``np.e **`` (a 1,000,001-point log-grid root-cause probe observes up
to 17 double-precision ulp by ``np.spacing``); this is sampled evidence, not a
bound over the continuous domain.  The predecessor geometry, theta quadrature,
weights and Fortran-order reshapes are ported verbatim.  Bounded negative cells
in the elastic families are intrinsic (signed ``vr2_vx2`` / ``vx_vx`` factors)
and are reproduced as-is, never clamped.
"""
from __future__ import annotations

import numpy as np

from scirel.collisions.atomic_hydrogen_charge_exchange_cross_section import (
    evaluate_atomic_hydrogen_charge_exchange_cross_section,
)
from scirel.collisions.atomic_hydrogen_elastic_cross_section import (
    evaluate_atomic_hydrogen_elastic_cross_section,
)
from scirel.collisions.hydrogen_h2_elastic_cross_section import (
    evaluate_hydrogen_h2_elastic_cross_section,
)
from scirel.collisions.hydrogen_proton_elastic_cross_section import (
    evaluate_hydrogen_proton_elastic_cross_section,
)

__all__ = ["assemble_atomic_hydrogen_collision_matrices"]

# Source constants (CONST.H_MASS, CONST.Q) verbatim.
H_MASS = 1.6726231e-27
Q = 1.602177e-19

# Fixed theta quadrature used by the source (kinetic_h.py:600-604).
NTHETA = 5
D_THETA = np.ones(NTHETA) / NTHETA
THETA = np.pi * (np.arange(NTHETA) / NTHETA + 0.5 / NTHETA)
COS_THETA = np.cos(THETA)


def _sigma(energy_ev, evaluator, **branch):
    """Evaluate an integrated cross-section leaf on an array carrier.

    The integrated leaves follow two declared output conventions: some wrap
    the result in one extra leading singleton axis (the saved source's
    ``np.array([E])`` convention, e.g. the H-H2 and H-P leaves) and some
    return the carrier's own shape.  The result is normalized to the
    carrier's shape; any other shape fails closed.
    """
    carrier_shape = np.shape(energy_ev)
    result = np.asarray(evaluator(energy_ev, **branch))
    if result.shape == (1,) + carrier_shape:
        return result[0]
    if result.shape != carrier_shape:
        raise ValueError("cross-section leaf returned an unexpected shape")
    return result


# --------------------------------------------------------------------------- #
# Double-velocity-space predecessor geometry (source kinetic_h.py:888-927).    #
# --------------------------------------------------------------------------- #
def _build_predecessor_state(vr, vx, Vr2pidVr, dVx):
    """Return (v_v2, v_v, vr2_vx2, vx_vx, Vr2pidVrdVx) on the source shape layout.

    Shapes: ``v_v2, v_v, vr2_vx2`` are ``(nvr,nvx,nvr,nvx,ntheta)``;
    ``vx_vx`` and ``Vr2pidVrdVx`` are ``(nvr,nvx,nvr,nvx)``.
    """
    nvr = vr.size
    nvx = vx.size
    v_v2 = np.zeros((nvr, nvx, nvr, nvx, NTHETA))
    vr2_vx2 = np.zeros((nvr, nvx, nvr, nvx, NTHETA))
    for m in range(NTHETA):
        for l in range(nvx):
            for k in range(nvr):
                for i in range(nvr):
                    v_starter = vr[i] ** 2 + vr[k] ** 2 - 2 * vr[i] * vr[k] * COS_THETA[m]
                    v_v2[i, :, k, l, m] = v_starter + (vx[:] - vx[l]) ** 2
                    vr2_vx2[i, :, k, l, m] = v_starter - 2 * (vx[:] - vx[l]) ** 2
    v_v = np.sqrt(v_v2)

    vx_vx = np.zeros((nvr, nvx, nvr, nvx))
    for j in range(nvx):
        for l in range(nvx):
            vx_vx[:, j, :, l] = vx[j] - vx[l]

    Vr2pidVrdVx = np.zeros((nvr, nvx, nvr, nvx))
    for k in range(nvr):
        Vr2pidVrdVx[:, :, k, :] = Vr2pidVr[k]
    for l in range(nvx):
        Vr2pidVrdVx[:, :, :, l] = Vr2pidVrdVx[:, :, :, l] * dVx[l]
    return v_v2, v_v, vr2_vx2, vx_vx, Vr2pidVrdVx


# --------------------------------------------------------------------------- #
# Public operator.                                                             #
# --------------------------------------------------------------------------- #
def assemble_atomic_hydrogen_collision_matrices(vr, vx, Vr2pidVr, dVx, Tnorm, mu=1.0):
    """Assemble the atomic four-family SIG collision matrices.

    Parameters
    ----------
    vr : (nvr,) array, positive entries ``v/vth`` (the validation rejects
        non-positive values; no monotonicity gate is applied).
    vx : (nvx,) array, strictly increasing with at least one positive and one
        negative entry (the validation does not require exact symmetry
        about zero).
    Vr2pidVr : (nvr,) array, cylindrical radial integration weight (source
        ``make_dvr_dvx`` output).
    dVx : (nvx,) array, axial cell widths (source ``make_dvr_dvx`` output).
    Tnorm : float, normalization temperature in eV; ``Vth = sqrt(2*Q*Tnorm/(mu*H_MASS))``
        with ``Q = 1.602177e-19`` J/eV (the same eV convention as the
        integrated thermal-speed-scale relation).
    mu : float, normalized mass of the colliding species (default 1.0 = H).

    Returns
    -------
    dict with ``SIG_CX``, ``SIG_H_H``, ``SIG_H_H2``, ``SIG_H_P``, each
    ``(nvr*nvx, nvr*nvx)``, plus the captured predecessor state ``v_v2``,
    ``v_v``, ``vr2_vx2``, ``vx_vx``, ``Vr2pidVrdVx`` and the thermal
    normalization ``Vth2`` for forensic parity checks.
    """
    vr = np.asarray(vr, dtype=float)
    vx = np.asarray(vx, dtype=float)
    Vr2pidVr = np.asarray(Vr2pidVr, dtype=float)
    dVx = np.asarray(dVx, dtype=float)
    if (
        vr.ndim != 1 or vx.ndim != 1 or Vr2pidVr.ndim != 1 or dVx.ndim != 1
        or vr.size < 1 or vx.size < 1
        or vr.size != Vr2pidVr.size or vx.size != dVx.size
        or not np.all(np.isfinite(vr)) or not np.all(np.isfinite(vx))
        or not np.all(np.isfinite(Vr2pidVr)) or not np.all(np.isfinite(dVx))
        or np.any(vr <= 0.0)
        or not np.all(np.diff(vx) > 0.0)
        or not np.any(vx > 0.0) or not np.any(vx < 0.0)
        or np.any(Vr2pidVr < 0.0) or np.any(dVx <= 0.0)
        or np.ndim(Tnorm) != 0 or np.ndim(mu) != 0
        or not np.isfinite(Tnorm) or float(Tnorm) <= 0.0
        or not np.isfinite(mu) or float(mu) <= 0.0
    ):
        raise ValueError("invalid velocity-space carrier for SIG assembly")

    nvr = vr.size
    nvx = vx.size
    nsig = nvr * nvx

    # Thermal normalization (source kinetic_h.py:551-552).
    Vth = np.sqrt((2 * Q * Tnorm) / (mu * H_MASS))
    Vth2 = Vth * Vth

    v_v2, v_v, vr2_vx2, vx_vx, Vr2pidVrdVx = _build_predecessor_state(vr, vx, Vr2pidVr, dVx)

    # Energy factor shared by SIG_CX / SIG_H_H2 / SIG_H_P (0.5*H_MASS*Vth2/Q).
    # SIG_H_H uses the mu-scaled factor 0.5*H_MASS*mu*Vth2/Q (source kinetic_h.py:957).
    ecx = 0.5 * H_MASS * Vth2 / Q
    ehh = 0.5 * H_MASS * mu * Vth2 / Q

    sig = {}

    # SIG_CX (source kinetic_h.py:939-945)
    _sig = np.zeros((nsig * nsig, NTHETA))
    _sig[:] = (v_v * _sigma(v_v2 * ecx, evaluate_atomic_hydrogen_charge_exchange_cross_section)).reshape(_sig.shape, order="F")
    sig_cx = np.zeros((nsig, nsig))
    sig_cx[:] = (
        Vr2pidVrdVx * ((_sig @ D_THETA).reshape(Vr2pidVrdVx.shape, order="F"))
    ).reshape(sig_cx.shape, order="F")
    sig["SIG_CX"] = sig_cx

    # SIG_H_H (source kinetic_h.py:956-965)
    _sig = np.zeros((nsig * nsig, NTHETA))
    _sig[:] = (vr2_vx2 * v_v * _sigma(v_v2 * ehh, evaluate_atomic_hydrogen_elastic_cross_section, viscosity=True) / 8).reshape(_sig.shape, order="F")
    sig_hh = np.zeros((nsig, nsig))
    sig_hh[:] = (
        Vr2pidVrdVx * ((_sig @ D_THETA).reshape(Vr2pidVrdVx.shape, order="F"))
    ).reshape(sig_hh.shape, order="F")
    sig["SIG_H_H"] = sig_hh

    # SIG_H_H2 (source kinetic_h.py:979-988)
    _sig = np.zeros((nsig * nsig, NTHETA))
    _sig[:] = (v_v * _sigma(v_v2 * ecx, evaluate_hydrogen_h2_elastic_cross_section)).reshape(_sig.shape, order="F")
    sig_hh2 = np.zeros((nsig, nsig))
    sig_hh2[:] = (
        Vr2pidVrdVx * vx_vx * ((_sig @ D_THETA).reshape(Vr2pidVrdVx.shape, order="F"))
    ).reshape(sig_hh2.shape, order="F")
    sig["SIG_H_H2"] = sig_hh2

    # SIG_H_P (source kinetic_h.py:1004-1011)
    _sig = np.zeros((nsig * nsig, NTHETA))
    _sig[:] = (v_v * _sigma(v_v2 * ecx, evaluate_hydrogen_proton_elastic_cross_section)).reshape(_sig.shape, order="F")
    sig_hp = np.zeros((nsig, nsig))
    sig_hp[:] = (
        Vr2pidVrdVx * vx_vx * ((_sig @ D_THETA).reshape(Vr2pidVrdVx.shape, order="F"))
    ).reshape(sig_hp.shape, order="F")
    sig["SIG_H_P"] = sig_hp

    for key, value in sig.items():
        if not np.all(np.isfinite(value)):
            raise ValueError(f"{key} assembly produced a non-finite matrix")

    sig["v_v2"] = v_v2
    sig["v_v"] = v_v
    sig["vr2_vx2"] = vr2_vx2
    sig["vx_vx"] = vx_vx
    sig["Vr2pidVrdVx"] = Vr2pidVrdVx
    sig["Vth2"] = np.array([Vth2])
    return sig
