"""Source-free assembly of the molecular H2 four-family SIG collision matrices.

Reproduces the double-velocity-space (``vr,vx``) x (``vr',vx'``) collision-operator
assembly of KN1DPy ``kinetic_h2.py:1036-1125`` for the molecular four families:

- ``SIG_CX``   : H2 + H2+ charge exchange, weight ``Vr2pidVrdVx``
- ``SIG_H2_H`` : H2-H     elastic,          weight ``Vr2pidVrdVx * vx_vx``
- ``SIG_H2_P`` : H2-H+    elastic,          weight ``Vr2pidVrdVx * vx_vx``
- ``SIG_H2_H2``: H2-H2    elastic (viscosity), weight ``Vr2pidVrdVx``

All reshapes are performed in Fortran order (``order='F'``) as the source
legacy ``Work`` buffer does. The four fits are bound to SciRel cross-section
operators, while the theta quadrature remains local. Bounded negative cells
in the elastic families are intrinsic (signed
``vr2_vx2`` / ``vx_vx`` factors) and are reproduced as-is, never clamped.

Source-exact energy factors (verbatim from ``kinetic_h2.py:1045,1061,1078,1108``):

- ``SIG_CX``    : ``v_v2 * (H_MASS*Vth2/Q)``            -- NOTE: no 0.5, and no mu.
- ``SIG_H2_H``  : ``v_v2 * (0.5*H_MASS*Vth2/Q)``       -- tabulated as H -> H2.
- ``SIG_H2_P``  : ``v_v2 * (0.5*H_MASS*Vth2/Q)``       -- tabulated as p -> H2.
- ``SIG_H2_H2`` : ``v_v2 * (H_MASS*mu*Vth2/Q)`` with ``/8.0`` and ``vis=1``
  (kinetic_h2.py:1108, ``sigma_el_hh_hh`` called with ``vis=1``).

The ``SIG_CX`` factor is deliberately different from the atomic-side ``0.5``
(atomic ``kinetic_h.py`` SIG_CX uses ``0.5*H_MASS*Vth2/Q``); this molecular
quirk is preserved verbatim and flagged for expert review.
"""
from __future__ import annotations

import numpy as np

from .molecular_hydrogen_charge_exchange_cross_section import evaluate_molecular_hydrogen_charge_exchange_cross_section
from .hydrogen_h2_elastic_cross_section import evaluate_hydrogen_h2_elastic_cross_section
from .hydrogen2_proton_elastic_cross_section import evaluate_hydrogen2_proton_elastic_cross_section
from .hydrogen2_hydrogen2_elastic_cross_section import evaluate_hydrogen2_hydrogen2_elastic_cross_section

__all__ = ["assemble_molecular_hydrogen_collision_matrices"]

# Source constants (CONST.H_MASS, CONST.Q) verbatim.
H_MASS = 1.6726231e-27
Q = 1.602177e-19

# Fixed theta quadrature used by the source (kinetic_h2.py, same as atomic).
NTHETA = 5
D_THETA = np.ones(NTHETA) / NTHETA
THETA = np.pi * (np.arange(NTHETA) / NTHETA + 0.5 / NTHETA)
COS_THETA = np.cos(THETA)


# --------------------------------------------------------------------------- #
# Double-velocity-space predecessor geometry (source kinetic_h2.py:997-1034).  #
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
def assemble_molecular_hydrogen_collision_matrices(vr, vx, Vr2pidVr, dVx, Tnorm, mu=1.0):
    """Assemble the molecular H2 four-family SIG collision matrices.

    Parameters
    ----------
    vr : (nvr,) array, strictly increasing, positive, ``v/vth``.
    vx : (nvx,) array, strictly increasing and crossing zero, ``v/vth``.
    Vr2pidVr : (nvr,) array, cylindrical radial integration weight (source
        ``make_dvr_dvx`` output).
    dVx : (nvx,) array, axial cell widths (source ``make_dvr_dvx`` output).
    Tnorm : float, normalization energy (eV); ``Vth = sqrt(2*Q*Tnorm/(mu*H_MASS))``.
    mu : float, normalized mass flag (source: 1 = hydrogen, 2 = deuterium;
        default 1.0).

    Returns
    -------
    dict with ``SIG_CX``, ``SIG_H2_H``, ``SIG_H2_P``, ``SIG_H2_H2``, each
    ``(nvr*nvx, nvr*nvx)``, plus the captured predecessor state ``v_v2``,
    ``v_v``, ``vr2_vx2``, ``vx_vx``, ``Vr2pidVrdVx`` and the thermal
    normalization ``Vth2`` for forensic parity checks.
    """
    try:
        carriers = (vr, vx, Vr2pidVr, dVx)
        raw_arrays = tuple(np.asarray(value) for value in carriers)
        if any(value.dtype.kind not in "iuf" for value in raw_arrays) or any(
            isinstance(value, (list, tuple))
            and any(isinstance(item, (bool, np.bool_)) for item in np.asarray(value, dtype=object).flat)
            for value in carriers
        ):
            raise ValueError("carrier arrays must have real numeric dtypes")
        vr, vx, Vr2pidVr, dVx = (np.asarray(value, dtype=float) for value in raw_arrays)
        temperature = np.asarray(Tnorm)
        mass = np.asarray(mu)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("invalid velocity-space carrier for molecular SIG assembly") from exc
    if (
        vr.ndim != 1 or vx.ndim != 1 or Vr2pidVr.ndim != 1 or dVx.ndim != 1
        or vr.size < 1 or vx.size < 1
        or vr.size != Vr2pidVr.size or vx.size != dVx.size
        or not np.all(np.isfinite(vr)) or not np.all(np.isfinite(vx))
        or not np.all(np.isfinite(Vr2pidVr)) or not np.all(np.isfinite(dVx))
        or np.any(vr <= 0.0) or not np.all(np.diff(vr) > 0.0)
        or not np.all(np.diff(vx) > 0.0)
        or not np.any(vx > 0.0) or not np.any(vx < 0.0)
        or np.any(Vr2pidVr < 0.0) or np.any(dVx <= 0.0)
        or temperature.ndim != 0 or mass.ndim != 0
        or temperature.dtype.kind not in "iuf" or mass.dtype.kind not in "iuf"
        or not np.isfinite(temperature) or float(temperature) <= 0.0
        or not np.isfinite(mass) or float(mass) <= 0.0
    ):
        raise ValueError("invalid velocity-space carrier for molecular SIG assembly")
    Tnorm = float(temperature)
    mu = float(mass)

    nvr = vr.size
    nvx = vx.size
    nsig = nvr * nvx

    # Thermal normalization (source kinetic_h2.py:656).
    mass_kg = mu * H_MASS
    if mass_kg == 0.0:
        raise ValueError("thermal normalization is not representable")
    Vth = np.sqrt((2 * Q * Tnorm) / mass_kg)
    Vth2 = Vth * Vth
    if not np.isfinite(Vth2) or Vth2 <= 0.0:
        raise ValueError("thermal normalization is not representable")

    v_v2, v_v, vr2_vx2, vx_vx, Vr2pidVrdVx = _build_predecessor_state(vr, vx, Vr2pidVr, dVx)

    # Energy factors (verbatim, source kinetic_h2.py:1045,1061,1078,1108).
    ecx = H_MASS * Vth2 / Q
    e_half = 0.5 * H_MASS * Vth2 / Q
    eh2 = H_MASS * mu * Vth2 / Q

    sig = {}

    # SIG_CX (source kinetic_h2.py:1044-1049)
    _sig = np.zeros((nsig * nsig, NTHETA))
    _sig[:] = (v_v * evaluate_molecular_hydrogen_charge_exchange_cross_section(v_v2 * ecx)).reshape(_sig.shape, order="F")
    sig_cx = np.zeros((nsig, nsig))
    sig_cx[:] = (
        Vr2pidVrdVx * ((_sig @ D_THETA).reshape(Vr2pidVrdVx.shape, order="F"))
    ).reshape(sig_cx.shape, order="F")
    sig["SIG_CX"] = sig_cx

    # SIG_H2_H (source kinetic_h2.py:1060-1066)
    _sig = np.zeros((nsig * nsig, NTHETA))
    _sig[:] = (v_v * evaluate_hydrogen_h2_elastic_cross_section(v_v2 * e_half)[0]).reshape(_sig.shape, order="F")
    sig_h2h = np.zeros((nsig, nsig))
    sig_h2h[:] = (
        Vr2pidVrdVx * vx_vx * ((_sig @ D_THETA).reshape(vx_vx.shape, order="F"))
    ).reshape(sig_h2h.shape, order="F")
    sig["SIG_H2_H"] = sig_h2h

    # SIG_H2_P (source kinetic_h2.py:1077-1091)
    _sig = np.zeros((nsig * nsig, NTHETA))
    _sig[:] = (v_v * evaluate_hydrogen2_proton_elastic_cross_section(v_v2 * e_half)).reshape(_sig.shape, order="F")
    sig_h2p = np.zeros((nsig, nsig))
    sig_h2p[:] = (
        Vr2pidVrdVx * vx_vx * ((_sig @ D_THETA).reshape(vx_vx.shape, order="F"))
    ).reshape(sig_h2p.shape, order="F")
    sig["SIG_H2_P"] = sig_h2p

    # SIG_H2_H2 (source kinetic_h2.py:1107-1120)
    _sig = np.zeros((nsig * nsig, NTHETA))
    _sig[:] = (vr2_vx2 * v_v * evaluate_hydrogen2_hydrogen2_elastic_cross_section(v_v2 * eh2, viscosity=True) / 8.0).reshape(_sig.shape, order="F")
    sig_h2h2 = np.zeros((nsig, nsig))
    sig_h2h2[:] = (
        Vr2pidVrdVx * ((_sig @ D_THETA).reshape(Vr2pidVrdVx.shape, order="F"))
    ).reshape(sig_h2h2.shape, order="F")
    sig["SIG_H2_H2"] = sig_h2h2

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
