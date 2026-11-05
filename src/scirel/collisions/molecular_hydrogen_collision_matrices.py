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
- ``SIG_H2_H2`` : ``v_v2 * (H_MASS*mu*Vth2/Q)`` with ``3/8`` and ``vis=1``
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


import numpy as np

from .molecular_hydrogen_charge_exchange_cross_section import (
    evaluate_molecular_hydrogen_charge_exchange_cross_section,
)
from .hydrogen_h2_elastic_cross_section import evaluate_hydrogen_h2_elastic_cross_section
from .hydrogen2_proton_elastic_cross_section import evaluate_hydrogen2_proton_elastic_cross_section
from .hydrogen2_hydrogen2_elastic_cross_section import (
    evaluate_hydrogen2_hydrogen2_elastic_cross_section,
)
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
def assemble_molecular_hydrogen_collision_matrices(
    vr, vx, Vr2pidVr, dVx, Tnorm, mu=1.0, *, n_theta=5
):
    """Assemble the molecular-H2 four-family collision matrices.

    Parameters
    ----------
    vr : real array-like
        Radial normalized velocity nodes. [v/Vth] Shape: ``[nvr]``. The array must
        be nonempty, finite, strictly positive and strictly increasing.
    vx : real array-like
        Axial normalized velocity nodes. [v/Vth] Shape: ``[nvx]``. The array must
        be nonempty, finite and strictly increasing. A common axial shift is
        allowed; the axis is not required to cross zero.
    Vr2pidVr : real array-like
        Cylindrical radial integration measure. [dimensionless normalized
        radial-area measure] Shape: ``[nvr]``. The value must be finite and
        nonnegative and must align with ``vr``.
    dVx : real array-like
        Axial cell widths. [dimensionless normalized axial-speed increment] Shape:
        ``[nvx]``. The value must be finite and strictly positive and align with
        ``vx``.
    Tnorm : real scalar
        Velocity-normalization energy. [eV] Shape: ``scalar``. The value must be
        finite and strictly positive; arrays, booleans and strings are rejected.
    mu : real scalar, optional
        Colliding-species mass factor. [multiples of 1.6726231e-27 kg] Shape:
        ``scalar``. The default is ``1.0``. The value must be finite and strictly
        positive. Physical checks cover H=1 and D=2.
    n_theta : int, optional
        Midpoint azimuth count, keyword-only. [dimensionless] Shape: ``scalar``.
        The default is ``5``. The value must be a positive integer; booleans are
        rejected.

    Returns
    -------
    SIG_CX, SIG_H2_H, SIG_H2_P, SIG_H2_H2 : numpy.ndarray
        Molecular charge-exchange and three elastic collision kernels, flattened
        with Fortran velocity ordering. [m^2 in normalized kernel convention]
        Shape: ``[nvr*nvx, nvr*nvx]``. ``SIG_CX`` is finite and nonnegative; the
        elastic matrices are finite and may contain positive, negative or zero
        entries.
    v_v2, vr2_vx2 : numpy.ndarray
        Relative-speed squared and signed stress-geometry factors. [(v/Vth)^2]
        Shape: ``[nvr, nvx, nvr, nvx, n_theta]``. All values are finite;
        ``vr2_vx2`` retains its sign.
    v_v : numpy.ndarray
        Relative normalized speed used as a quadrature factor. [v/Vth] Shape:
        ``[nvr, nvx, nvr, nvx, n_theta]``. All values are finite and nonnegative.
    vx_vx : numpy.ndarray
        Signed axial relative velocity. [v/Vth] Shape:
        ``[nvr, nvx, nvr, nvx]``. All values are finite and may carry either sign.
    Vr2pidVrdVx : numpy.ndarray
        Broadcast target-column velocity measure. [dimensionless normalized
        volume measure] Shape: ``[nvr, nvx, nvr, nvx]``. All values are finite and
        nonnegative.
    Vth2 : numpy.ndarray
        Square of the thermal speed normalization. [m^2/s^2] Shape: ``[1]``. The
        value is finite and strictly positive.

    Raises
    ------
    ValueError
        If an array is not real numeric or finite, axes or weights violate their
        shape and ordering rules, ``Tnorm`` or ``mu`` is invalid, ``n_theta`` is
        not a positive integer, or a thermal speed, cross section or matrix is not
        representable as a finite value.

    See Also
    --------
    assemble_molecular_hydrogen_omega_frequencies : Reduces a molecular velocity
        distribution with these matrices.
    assemble_atomic_hydrogen_collision_matrices : The atomic-H four-family
        counterpart.
    evaluate_molecular_hydrogen_charge_exchange_cross_section : Charge-exchange
        fit used by ``SIG_CX``.

    Notes
    -----
    The relation assembles axisymmetric velocity-space kernels on a cylindrical
    grid. The molecular charge-exchange fit uses twice the atomic projectile mass;
    the H-H2 and proton-H2 momentum-transfer fits use the H projectile mass.
    ``SIG_H2_H2`` uses the molecular momentum-transfer fit as a documented
    viscosity surrogate. The default five-angle midpoint rule is an approximation;
    increase ``n_theta`` for the caller's convergence study. Elastic kernels keep
    their signed geometry. The self-stress kernel uses the Boltzmann prefactor
    ``3/8``, three times the self-collision value in KN1D Appendix B under that
    report's different normalization. H (``mu=1``) and D (``mu=2``) are the
    physically checked cases; other positive mass factors are algebraic extensions.

    References
    ----------
    .. [1] B. LaBombard, "KN1D: A 1-D Space, 2-D Velocity, Kinetic Transport
       Algorithm for Atomic and Molecular Hydrogen in an Ionizing Plasma",
       MIT report PSFC/RR-01-3, 2001, Appendix B.
    .. [2] S. Chapman and T. G. Cowling, "The Mathematical Theory of Non-uniform
       Gases", Cambridge University Press.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.collisions import assemble_molecular_hydrogen_collision_matrices
    >>> r = assemble_molecular_hydrogen_collision_matrices(
    ...     vr=np.array([0.5, 1.0]), vx=np.array([-1.0, 1.0]),
    ...     Vr2pidVr=np.array([1.0, 2.0]), dVx=np.array([2.0, 2.0]), Tnorm=1.0,
    ... )
    >>> assert r['SIG_CX'].shape == (4, 4)
    >>> assert r['v_v2'].shape == (2, 2, 2, 2, 5)
    >>> assert np.isfinite(r['SIG_H2_H2']).all()
    >>> assert (r['SIG_H2_H2'] < 0).any()
    >>> assert r['Vth2'].shape == (1,)
    """
    try:
        carriers = (vr, vx, Vr2pidVr, dVx)
        raw_arrays = tuple(np.asarray(value) for value in carriers)
        if any(value.dtype.kind not in "iuf" for value in raw_arrays) or any(
            isinstance(value, (list, tuple))
            and any(
                isinstance(item, (bool, np.bool_)) for item in np.asarray(value, dtype=object).flat
            )
            for value in carriers
        ):
            raise ValueError("carrier arrays must have real numeric dtypes")
        vr, vx, Vr2pidVr, dVx = (np.asarray(value, dtype=float) for value in raw_arrays)
        temperature = np.asarray(Tnorm)
        mass = np.asarray(mu)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("invalid velocity-space carrier for molecular SIG assembly") from exc
    if (
        vr.ndim != 1
        or vx.ndim != 1
        or Vr2pidVr.ndim != 1
        or dVx.ndim != 1
        or vr.size < 1
        or vx.size < 1
        or vr.size != Vr2pidVr.size
        or vx.size != dVx.size
        or not np.all(np.isfinite(vr))
        or not np.all(np.isfinite(vx))
        or not np.all(np.isfinite(Vr2pidVr))
        or not np.all(np.isfinite(dVx))
        or np.any(vr <= 0.0)
        or not np.all(np.diff(vr) > 0.0)
        or not np.all(np.diff(vx) > 0.0)
        or np.any(Vr2pidVr < 0.0)
        or np.any(dVx <= 0.0)
        or temperature.ndim != 0
        or mass.ndim != 0
        or temperature.dtype.kind not in "iuf"
        or mass.dtype.kind not in "iuf"
        or not np.isfinite(temperature)
        or float(temperature) <= 0.0
        or not np.isfinite(mass)
        or float(mass) <= 0.0
    ):
        raise ValueError("invalid velocity-space carrier for molecular SIG assembly")
    if (
        isinstance(n_theta, (bool, np.bool_))
        or not isinstance(n_theta, (int, np.integer))
        or n_theta < 1
    ):
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

    v_v2, v_v, vr2_vx2, vx_vx, Vr2pidVrdVx = _build_predecessor_state(
        vr, vx, Vr2pidVr, dVx, n_theta
    )

    # Energy factors (verbatim, source kinetic_h2.py:1045,1061,1078,1108).
    ecx = H_MASS * Vth2 / Q
    e_half = 0.5 * H_MASS * Vth2 / Q
    eh2 = H_MASS * mu * Vth2 / Q

    sig = {}

    # SIG_CX (source kinetic_h2.py:1044-1049)
    sig["SIG_CX"] = averaged_matrix(
        v_v * evaluate_molecular_hydrogen_charge_exchange_cross_section(v_v2 * ecx),
        Vr2pidVrdVx,
        angular_weights,
        nsig,
    )

    # SIG_H2_H (source kinetic_h2.py:1060-1066)
    sig["SIG_H2_H"] = averaged_matrix(
        v_v * evaluate_hydrogen_h2_elastic_cross_section(v_v2 * e_half),
        Vr2pidVrdVx * vx_vx,
        angular_weights,
        nsig,
    )

    # SIG_H2_P (source kinetic_h2.py:1077-1091)
    sig["SIG_H2_P"] = averaged_matrix(
        v_v * evaluate_hydrogen2_proton_elastic_cross_section(v_v2 * e_half),
        Vr2pidVrdVx * vx_vx,
        angular_weights,
        nsig,
    )

    # Self-collision stress kernel. For equal masses a collision changes v_x^2 by
    # Q(g)/8 sin^2(chi), with Q(g) = g_perp^2 - 2 g_x^2. Energy conservation makes the BGK
    # change of Q three times that of v_x^2 with opposite sign, so the frequency that matches
    # the stress relaxation carries 3/8. The KN1D report's Appendix B equates the BGK integral
    # of (2 v_x^2 - v_r^2) to the v_x^2 rate and so has 1/8, three times too low; this library
    # uses the Boltzmann value, which reproduces the Chapman-Enskog hard-sphere viscosity.
    sig["SIG_H2_H2"] = averaged_matrix(
        vr2_vx2
        * v_v
        * evaluate_hydrogen2_hydrogen2_elastic_cross_section(v_v2 * eh2, viscosity=True)
        * 3.0
        / 8.0,
        Vr2pidVrdVx,
        angular_weights,
        nsig,
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
