"""Source-free assembly of the atomic four-family SIG collision matrices.

Reproduces the double-velocity-space (``vr,vx``) x (``vr',vx'``) collision-operator
assembly of KN1DPy ``kinetic_h.py:888-1018`` for the atomic four families:

- ``SIG_CX``   : H + H+  charge exchange,    weight ``Vr2pidVrdVx``
- ``SIG_H_H``  : H-H     elastic, viscosity  weight ``Vr2pidVrdVx``
- ``SIG_H_H2`` : H-H2    elastic,            weight ``Vr2pidVrdVx * vx_vx``
- ``SIG_H_P``  : H-H+    elastic,            weight ``Vr2pidVrdVx * vx_vx``

All reshapes are performed in Fortran order (``order='F'``) as the source
legacy ``Work`` buffer does. The four fits are bound to SciRel cross-section
operators, while the theta quadrature remains local. Bounded negative cells
in the elastic families are intrinsic (signed
``vr2_vx2`` / ``vx_vx`` factors) and are reproduced as-is, never clamped.

Physical energy convention: the input to each fit is the equivalent hydrogen
projectile laboratory energy with a stationary target. For H/D momentum
transfer KN1D section 2.1.2.6 maps E_D to E_D/2; for viscosity it maps E_D to
E_D. Thus mixed/CX factors are Tnorm/mu and self viscosity is Tnorm.
Default five-angle midpoint integration is approximate. n_theta enables an
explicit angular convergence study; fit fidelity is not universal accuracy.
"""
from __future__ import annotations

import numpy as np

from .atomic_hydrogen_charge_exchange_cross_section import evaluate_atomic_hydrogen_charge_exchange_cross_section
from .atomic_hydrogen_elastic_cross_section import evaluate_atomic_hydrogen_elastic_cross_section
from .hydrogen_h2_elastic_cross_section import evaluate_hydrogen_h2_elastic_cross_section
from .hydrogen_proton_elastic_cross_section import evaluate_hydrogen_proton_elastic_cross_section
from ._velocity_geometry import averaged_matrix, predecessor_state

__all__ = ["assemble_atomic_hydrogen_collision_matrices"]

# Source constants (CONST.H_MASS, CONST.Q) verbatim.
H_MASS = 1.6726231e-27
Q = 1.602177e-19

# Fixed theta quadrature used by the source (kinetic_h.py:600-604).
NTHETA = 5
D_THETA = np.ones(NTHETA) / NTHETA
THETA = np.pi * (np.arange(NTHETA) / NTHETA + 0.5 / NTHETA)
COS_THETA = np.cos(THETA)


# --------------------------------------------------------------------------- #
# Double-velocity-space predecessor geometry (source kinetic_h.py:888-927).    #
# --------------------------------------------------------------------------- #
def _build_predecessor_state(vr, vx, Vr2pidVr, dVx, n_theta=5):
    """Return (v_v2, v_v, vr2_vx2, vx_vx, Vr2pidVrdVx) on the source shape layout.

    Shapes: ``v_v2, v_v, vr2_vx2`` are ``(nvr,nvx,nvr,nvx,ntheta)``;
    ``vx_vx`` and ``Vr2pidVrdVx`` are ``(nvr,nvx,nvr,nvx)``.
    """
    return predecessor_state(vr, vx, Vr2pidVr, dVx, n_theta)


# --------------------------------------------------------------------------- #
# Public operator.                                                             #
# --------------------------------------------------------------------------- #
def assemble_atomic_hydrogen_collision_matrices(vr, vx, Vr2pidVr, dVx, Tnorm, mu=1.0, *, n_theta=5):
    """Assemble the atomic four-family SIG collision matrices.

    Parameters
    ----------
    vr : (nvr,) array, strictly increasing, positive, ``v/vth``.
    vx : (nvx,) array, strictly increasing; arbitrary common axial boost allowed, ``v/vth``.
    Vr2pidVr : (nvr,) array, cylindrical radial integration weight (source
        ``make_dvr_dvx`` output).
    dVx : (nvx,) array, axial cell widths (source ``make_dvr_dvx`` output).
    Tnorm : float, normalization energy (eV); ``Vth = sqrt(2*Q*Tnorm/(mu*H_MASS))``.
    mu : float, normalized mass of the colliding species (default 1.0 = H).

    n_theta : int, keyword-only
        Positive midpoint azimuth count; default 5 retains the KN1D rule.
        Increase and verify convergence for the caller's velocity grid.

    Returns
    -------
    dict with ``SIG_CX``, ``SIG_H_H``, ``SIG_H_H2``, ``SIG_H_P``, each
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
        raise ValueError("invalid velocity-space carrier for SIG assembly") from exc
    if (
        vr.ndim != 1 or vx.ndim != 1 or Vr2pidVr.ndim != 1 or dVx.ndim != 1
        or vr.size < 1 or vx.size < 1
        or vr.size != Vr2pidVr.size or vx.size != dVx.size
        or not np.all(np.isfinite(vr)) or not np.all(np.isfinite(vx))
        or not np.all(np.isfinite(Vr2pidVr)) or not np.all(np.isfinite(dVx))
        or np.any(vr <= 0.0) or not np.all(np.diff(vr) > 0.0)
        or not np.all(np.diff(vx) > 0.0)
        or np.any(Vr2pidVr < 0.0) or np.any(dVx <= 0.0)
        or temperature.ndim != 0 or mass.ndim != 0
        or temperature.dtype.kind not in "iuf" or mass.dtype.kind not in "iuf"
        or not np.isfinite(temperature) or float(temperature) <= 0.0
        or not np.isfinite(mass) or float(mass) <= 0.0
    ):
        raise ValueError("invalid velocity-space carrier for SIG assembly")
    if isinstance(n_theta, (bool, np.bool_)) or not isinstance(n_theta, (int, np.integer)) or n_theta < 1:
        raise ValueError("n_theta must be a positive integer")
    angular_weights = np.ones(n_theta) / n_theta
    Tnorm = float(temperature)
    mu = float(mass)

    nvr = vr.size
    nvx = vx.size
    nsig = nvr * nvx

    # Thermal normalization (source kinetic_h.py:551-552).
    mass_kg = mu * H_MASS
    if mass_kg == 0.0:
        raise ValueError("thermal normalization is not representable")
    Vth = np.sqrt((2 * Q * Tnorm) / mass_kg)
    Vth2 = Vth * Vth
    if not np.isfinite(Vth2) or Vth2 <= 0.0:
        raise ValueError("thermal normalization is not representable")

    v_v2, v_v, vr2_vx2, vx_vx, Vr2pidVrdVx = _build_predecessor_state(vr, vx, Vr2pidVr, dVx, n_theta)

    # Energy factor shared by SIG_CX / SIG_H_H2 / SIG_H_P (0.5*H_MASS*Vth2/Q).
    # SIG_H_H uses the mu-scaled factor 0.5*H_MASS*mu*Vth2/Q (source kinetic_h.py:957).
    ecx = 0.5 * H_MASS * Vth2 / Q
    ehh = 0.5 * H_MASS * mu * Vth2 / Q

    sig = {}

    # SIG_CX (source kinetic_h.py:939-945)
    sig["SIG_CX"] = averaged_matrix(
        v_v * evaluate_atomic_hydrogen_charge_exchange_cross_section(v_v2 * ecx),
        Vr2pidVrdVx, angular_weights, nsig,
    )

    # SIG_H_H (source kinetic_h.py:956-965)
    sig["SIG_H_H"] = averaged_matrix(
        vr2_vx2 * v_v * evaluate_atomic_hydrogen_elastic_cross_section(v_v2 * ehh, viscosity=True) / 8,
        Vr2pidVrdVx, angular_weights, nsig,
    )

    # SIG_H_H2 (source kinetic_h.py:979-988)
    sig["SIG_H_H2"] = averaged_matrix(
        v_v * evaluate_hydrogen_h2_elastic_cross_section(v_v2 * ecx)[0],
        Vr2pidVrdVx * vx_vx, angular_weights, nsig,
    )

    # SIG_H_P (source kinetic_h.py:1004-1011)
    sig["SIG_H_P"] = averaged_matrix(
        v_v * evaluate_hydrogen_proton_elastic_cross_section(v_v2 * ecx)[0],
        Vr2pidVrdVx * vx_vx, angular_weights, nsig,
    )

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
