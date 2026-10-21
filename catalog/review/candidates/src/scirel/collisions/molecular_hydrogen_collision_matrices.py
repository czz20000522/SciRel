"""Source-free assembly of the molecular H2 four-family SIG collision matrices.

Reproduces the double-velocity-space (``vr,vx``) x (``vr',vx'``) collision-operator
assembly of the neutral-transport formulation ``kinetic_h2.py:1036-1125`` for the molecular four families:

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

Energy is projectile laboratory energy for a stationary target, not a generic
center-of-mass energy. H2+ charge exchange therefore uses twice the atomic
proton mass. Mixed H/H2 and p/H2 fits use the H projectile mass, even when the
molecule is the test particle. For deuterium the neutral-transport formulation section 2.1.2.6 uses the H
momentum-transfer fit at E_D/2, but the viscosity fit at E_D (same laboratory
energy for equal-mass collisions). The self molecular viscosity cross section
is the source's momentum-transfer surrogate, not measured independent viscosity.
The default five-angle midpoint rule is approximate; n_theta permits explicit
convergence studies. These model assumptions are retained, not hidden quirks.
"""
from __future__ import annotations

# HELD: human-review exposure guard
from scirel._hold import require_review_import
require_review_import(__name__)




import numpy as np

from .molecular_hydrogen_charge_exchange_cross_section import evaluate_molecular_hydrogen_charge_exchange_cross_section
from .hydrogen_h2_elastic_cross_section import evaluate_hydrogen_h2_elastic_cross_section
from .hydrogen2_proton_elastic_cross_section import evaluate_hydrogen2_proton_elastic_cross_section
from .hydrogen2_hydrogen2_elastic_cross_section import evaluate_hydrogen2_hydrogen2_elastic_cross_section
from ._velocity_geometry import averaged_matrix, predecessor_state

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
def _build_predecessor_state(vr, vx, Vr2pidVr, dVx, n_theta=5):
    """Return (v_v2, v_v, vr2_vx2, vx_vx, Vr2pidVrdVx) on the source shape layout.

    Shapes: ``v_v2, v_v, vr2_vx2`` are ``(nvr,nvx,nvr,nvx,ntheta)``;
    ``vx_vx`` and ``Vr2pidVrdVx`` are ``(nvr,nvx,nvr,nvx)``.
    """
    return predecessor_state(vr, vx, Vr2pidVr, dVx, n_theta)


# --------------------------------------------------------------------------- #
# Public operator.                                                             #
# --------------------------------------------------------------------------- #
def assemble_molecular_hydrogen_collision_matrices(vr, vx, Vr2pidVr, dVx, Tnorm, mu=1.0, *, n_theta=5):
    """Assemble the molecular H2 four-family SIG collision matrices.

    Parameters
    ----------
    vr : (nvr,) array, strictly increasing, positive, ``v/vth``.
    vx : (nvx,) array, strictly increasing; arbitrary common axial boost allowed, ``v/vth``.
    Vr2pidVr : (nvr,) array, cylindrical radial integration weight (source
        ``make_dvr_dvx`` output).
    dVx : (nvx,) array, axial cell widths (source ``make_dvr_dvx`` output).
    Tnorm : float, normalization energy (eV); ``Vth = sqrt(2*Q*Tnorm/(mu*H_MASS))``.
    mu : float, normalized mass flag (source: 1 = hydrogen, 2 = deuterium;
        default 1.0).

    n_theta : int, keyword-only
        Positive midpoint azimuth count; default 5 retains the neutral-transport formulation rule.
        Increase and verify convergence for the caller's velocity grid.

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
        or np.any(Vr2pidVr < 0.0) or np.any(dVx <= 0.0)
        or temperature.ndim != 0 or mass.ndim != 0
        or temperature.dtype.kind not in "iuf" or mass.dtype.kind not in "iuf"
        or not np.isfinite(temperature) or float(temperature) <= 0.0
        or not np.isfinite(mass) or float(mass) <= 0.0
    ):
        raise ValueError("invalid velocity-space carrier for molecular SIG assembly")
    if isinstance(n_theta, (bool, np.bool_)) or not isinstance(n_theta, (int, np.integer)) or n_theta < 1:
        raise ValueError("n_theta must be a positive integer")
    angular_weights = np.ones(n_theta) / n_theta
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

    v_v2, v_v, vr2_vx2, vx_vx, Vr2pidVrdVx = _build_predecessor_state(vr, vx, Vr2pidVr, dVx, n_theta)

    # Energy factors (verbatim, source kinetic_h2.py:1045,1061,1078,1108).
    ecx = H_MASS * Vth2 / Q
    e_half = 0.5 * H_MASS * Vth2 / Q
    eh2 = H_MASS * mu * Vth2 / Q

    sig = {}

    # SIG_CX (source kinetic_h2.py:1044-1049)
    sig["SIG_CX"] = averaged_matrix(
        v_v * evaluate_molecular_hydrogen_charge_exchange_cross_section(v_v2 * ecx),
        Vr2pidVrdVx, angular_weights, nsig,
    )

    # SIG_H2_H (source kinetic_h2.py:1060-1066)
    sig["SIG_H2_H"] = averaged_matrix(
        v_v * evaluate_hydrogen_h2_elastic_cross_section(v_v2 * e_half)[0],
        Vr2pidVrdVx * vx_vx, angular_weights, nsig,
    )

    # SIG_H2_P (source kinetic_h2.py:1077-1091)
    sig["SIG_H2_P"] = averaged_matrix(
        v_v * evaluate_hydrogen2_proton_elastic_cross_section(v_v2 * e_half),
        Vr2pidVrdVx * vx_vx, angular_weights, nsig,
    )

    # SIG_H2_H2 (source kinetic_h2.py:1107-1120)
    sig["SIG_H2_H2"] = averaged_matrix(
        vr2_vx2 * v_v * evaluate_hydrogen2_hydrogen2_elastic_cross_section(v_v2 * eh2, viscosity=True) / 8.0,
        Vr2pidVrdVx, angular_weights, nsig,
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
