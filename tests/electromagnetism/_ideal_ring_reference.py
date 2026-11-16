"""Independent reference for the axisymmetric ideal circular-filament response.

Why this is a second source and not the same backend under another name
-----------------------------------------------------------------------
``scirel.electromagnetism.greens`` evaluates one relation: the poloidal flux
``psi = R A_phi`` and the poloidal field ``(B_R, B_Z)`` of a single ideal
circular current filament.  It selects two branches on the elliptic parameter
``m = 4 R a / ((R + a)^2 + (Z - z0)^2)``.  Below ``m = 0.5`` it uses the
Gauss hypergeometric series ``hyp2f1(1.5, 1.5; 3; m)``; at and above ``m = 0.5``
it uses ``scipy.special.ellipkm1(q)`` with ``q = 1 - m`` and
``scipy.special.ellipe(1 - q)``.  ``B_R`` and ``B_Z`` are then supplied by
explicitly differentiated combinations of the same functions.

Every route in this module uses a different algorithm on every one of those
points:

1. **Definition-level flux.**  ``psi`` is obtained by direct quadrature of its
   Biot-Savart definition,
   ``psi = 1e-7 R * integral a cos(phi) / |r - r'| dphi``, which uses no
   elliptic integral and no hypergeometric series.
2. **Complement-free closed form.**  For larger ``m`` the flux is evaluated as
   ``1e-7 d ((2 - m) K(m) - 2 E(m))`` with ``d = |(R + a, Z - z0)|``, using
   ``mpmath.ellipk(m)`` and ``mpmath.ellipe(m)``, which take the *parameter*
   ``m`` directly and are AgM-based.  ``scipy.special.ellipkm1`` instead
   consumes the complement ``q = 1 - m`` and reconstructs the modulus from it;
   feeding ``m`` rather than ``1 - m`` therefore exercises a numerically
   different regime and can disagree when the complement is where the
   cancellation lives.
3. **Derivative route.**  ``B_R`` and ``B_Z`` come from differentiating the
   *flux* through ``B_R = -(1/R) dpsi/dZ`` and ``B_Z = (1/R) dpsi/dR`` with a
   high-order finite difference at 40 decimal digits.  The implementation never
   takes this route: it evaluates the analytically differentiated combinations
   directly, so agreement of ``B_R``/``B_Z`` here is a statement about the
   derivative identities, not a restatement of the same formula.

The module certifies itself before its values are used: (2) is compared against
(1) wherever both are available, and each derivative is recomputed at two
steps and Richardson-extrapolated.  A half-converged reference raises instead
of being compared against the implementation as if it were truth.

Sign, unit and orientation convention, established from the physical statement
-----------------------------------------------------------------------------
- ``psi`` is ``R A_phi`` in ``Wb/rad`` per ampere; the reference integrand is
  ``R a cos(phi) / |r - r'|`` with no extra factor, which is what makes
  ``B_R = -(1/R) dpsi/dZ`` and ``B_Z = (1/R) dpsi/dR`` the correct pair of
  identities rather than their transpose.  A response that swapped ``B_R`` and
  ``B_Z``, or dropped one ``1/R``, cannot satisfy both identities through a
  flux obtained by quadrature.
- ``mu0 / (4 pi) = 1e-7`` exactly, since ``mu0 = 4 pi 1e-7``; ``1e-7`` is the
  only constant in the reference, so a response that used ``mu0`` itself, or
  ``mu0 / (2 pi)``, is off by ``4 pi`` or ``2 pi`` and fails at the first
  comparison.
- ``d = sqrt((R + a)^2 + (Z - z0)^2)`` is formed from the *sum* of the radii and
  the *signed* height difference ``Z - z0``, so ``psi`` is even and ``B_R`` odd
  under ``Z -> 2 z0 - Z``.  ``m`` uses ``4 R a``, not ``4 R^2``.

Precision budget and where each number comes from
-------------------------------------------------
Fixed before any comparison against the implementation was run.

1. **Reference quadrature.** Every quadrature is evaluated at 40 decimal digits
   with the integrand split at twelve fixed breakpoints of ``[0, 2 pi]``.  For
   these analytic integrands a rule working at ``D`` digits controls the
   absolute error to about ``10^-D`` times ``2 pi * max|integrand|``.  At
   ``D = 40`` that is ``1e-38 * scale``, i.e. ``1e-24`` relative to a value of
   order ``1e-14 * scale`` (the smallest ``psi`` used in a relative assertion,
   at ``R = 1e-6 a``).  The cross-certificate below is therefore set at
   ``1e-22`` relative, not at the full working precision.

2. **Derivative certificate.** ``B_R``/``B_Z`` use a fourth-order central
   difference in ``h``; the truncation is ``O((h/L)^4)`` with ``L`` the length
   scale ``psi`` varies on, and the cancellation costs
   ``-log10(h * B / psi)`` digits.  ``h = 1e-6 L`` puts the truncation at
   ``1e-24`` far from the wire, but ``L`` is not the ring radius alone: close
   to the wire the logarithmic structure of ``K`` shrinks the effective scale
   to the wire distance, which at ``0.02 a`` gives ``(h/0.02 a)^4 = 6e-18``.
   The certificate is therefore set by what it has to prove rather than by a
   single step's residual: the extrapolated value must be stable to
   ``_DERIVATIVE_CERTIFICATE = 1e-17`` relative, three orders below the
   ``1.4e-14`` response budget the derivatives are compared against, and the
   step is chosen small enough to reach that where the reference is used.  The
   stability is measured between the extrapolations of ``(h, h/2)`` and
   ``(h/2, h/4)``, not between one difference and its extrapolation: the
   latter carries the first difference's own truncation and cannot certify
   anything below it.

3. **Response budget used by the tests.** The implementation's elliptic branch
   combines five denominator factors and a three-term difference
   ``-q K + (ar^2 + rr^2 + hr^2) E``, where the terms are of opposite sign and
   partly cancel; its hypergeometric branch multiplies five factors and sums
   two hypergeometric evaluations.  Counting low tens of rounding operations
   plus that cancellation, the relative allowance is
   ``128 eps = 2.8e-14`` for ``(B_R, B_Z)`` and ``64 eps = 1.4e-14`` for
   ``psi``, whose branch contains fewer operations.  The reference
   contributes at most ``1e-22`` relative and is negligible against both.
   These are **observed budgets for the sampled grids**, not proven
   continuous error bounds: a maximum over a finite grid does not bound the
   interval between grid points.

Where the reference stops applying
----------------------------------
- Targets within ``1e-2`` of the wire radius in the ``(R, Z)`` plane: the
  ``|r - r'|^-3`` integrand becomes too sharply peaked for a fixed-breakpoint
  rule, and the ideal-filament response itself diverges.  ``MIN_SEPARATION``
  rejects them instead of returning a number the implementation would have no
  obligation to match.
- ``R`` below ``1e-8 a``: ``psi`` and ``B_R`` vanish like ``R^2`` and ``R``, so
  a *relative* statement loses resolution faster than the certified absolute
  error of the reference grows.  The tests make relative statements only above
  that ratio and otherwise use absolute differences against the integrand
  scale.
"""

from __future__ import annotations

import mpmath as mp

MU0_OVER_4PI = mp.mpf("1e-7")
DPS = 40
MIN_SEPARATION = mp.mpf("1e-2")
MIN_RADIUS_RATIO = mp.mpf("1e-8")
SERIES_CUTOFF = mp.mpf("1e-2")

# Response budgets, derived in the module docstring from the operation count
# and the cancellation each branch carries.  Fixed before measurement.
PSI_BUDGET = 64.0 * 2.0**-52
FIELD_BUDGET = 128.0 * 2.0**-52

_QUADRATURE_CERTIFICATE = mp.mpf("1e-22")
_DERIVATIVE_CERTIFICATE = mp.mpf("1e-17")


def _breakpoints():
    """Return the twelve-fold split of ``[0, 2 pi]`` at the working precision.

    The breakpoints must be formed *inside* the working-precision block.  A
    module-level list would be built at the default 15-digit precision and
    would then cap the quadrature at about one unit of binary64 rounding no
    matter how many digits the rule works at -- a defect this module hit and
    that the cross-certificate below now catches instead of reporting as an
    implementation disagreement.
    """
    return [mp.pi * index / 6 for index in range(13)]


class ReferenceNotConverged(RuntimeError):
    """Raised when the reference disagrees with itself beyond its certificate."""


def _separation_squared(radius, coil_radius, dz, phi):
    """Return ``|r - r'|^2`` at loop parameter ``phi``."""
    return radius**2 + coil_radius**2 - 2 * radius * coil_radius * mp.cos(phi) + dz**2


def _quadrature_psi(radius, coil_radius, dz):
    """Return ``psi`` from the Biot-Savart definition at the working precision."""

    def integrand(phi):
        return (
            coil_radius * mp.cos(phi) / mp.sqrt(_separation_squared(radius, coil_radius, dz, phi))
        )

    return MU0_OVER_4PI * radius * mp.quad(integrand, _breakpoints())


def _closed_psi(radius, coil_radius, dz):
    """Return ``psi`` from the complement-free AgM elliptic evaluation."""
    distance = mp.sqrt((radius + coil_radius) ** 2 + dz**2)
    parameter = 4 * radius * coil_radius / distance**2
    return (
        MU0_OVER_4PI
        * distance
        * ((2 - parameter) * mp.ellipk(parameter) - 2 * mp.ellipe(parameter))
    )


def _check_input(radius, coil_radius, dz):
    """Reject geometry the reference does not attempt to resolve."""
    if radius < 0 or coil_radius <= 0:
        raise ValueError("the reference needs a positive source radius and a nonnegative target")
    if radius > 0:
        separation = mp.sqrt((radius - coil_radius) ** 2 + dz**2)
        if separation < MIN_SEPARATION * coil_radius:
            raise ValueError("target too close to the wire for this reference")


def flux_psi(radius, z, coil_radius, coil_z, weight=1):
    """Return the quadrature-certified ``psi`` of one weighted ring as ``mpf``.

    Below ``m = SERIES_CUTOFF`` the complement-based closed form would subtract
    two ``O(1)`` elliptic values to leave an ``O(m^2)`` difference, so the
    definition-level quadrature is used instead.  Above it both routes are
    available and are compared against each other; the closed form is returned
    only when that comparison holds.
    """
    with mp.workdps(DPS):
        radius_mp, coil_radius_mp = mp.mpf(radius), mp.mpf(coil_radius)
        dz = mp.mpf(z) - mp.mpf(coil_z)
        _check_input(radius_mp, coil_radius_mp, dz)
        prefactor = mp.mpf(weight) * MU0_OVER_4PI
        if radius_mp == 0:
            # psi = R A_phi carries an explicit R factor, and A_phi is finite on
            # the axis, so the flux is exactly zero there.
            return mp.mpf(0)
        distance_squared = (radius_mp + coil_radius_mp) ** 2 + dz**2
        parameter = 4 * radius_mp * coil_radius_mp / distance_squared
        quadrature = _quadrature_psi(radius_mp, coil_radius_mp, dz)
        if parameter < SERIES_CUTOFF:
            return prefactor * quadrature / MU0_OVER_4PI
        closed = _closed_psi(radius_mp, coil_radius_mp, dz)
        scale = abs(quadrature) + abs(closed) + MU0_OVER_4PI * abs(radius_mp) * abs(coil_radius_mp)
        if abs(closed - quadrature) > _QUADRATURE_CERTIFICATE * scale:
            raise ReferenceNotConverged(
                "the quadrature and the complement-free elliptic flux disagree by "
                f"{mp.nstr(abs(closed - quadrature), 5)} at R={mp.nstr(radius_mp, 8)} "
                f"Z-Z0={mp.nstr(dz, 8)} a={mp.nstr(coil_radius_mp, 8)}"
            )
        return prefactor * closed / MU0_OVER_4PI


def _derivative_steps(radius, z, coil_radius, coil_z):
    """Return the ``(d/dZ, d/dR)`` steps of the two central differences.

    The ``R`` step is scaled by ``min(R, a)``: below the ring radius the flux
    varies on the ``R`` scale itself (``psi ~ R^2``), above it on the ring
    scale, so this keeps ``h`` small against whichever scale is active while
    staying strictly inside the positive half-line.  The ``Z`` step is scaled
    by the larger of the ring radius and the height offset, which are the two
    scales ``psi`` varies on in ``Z``.
    """
    dz = mp.mpf(z) - mp.mpf(coil_z)
    coil_radius_mp = mp.mpf(coil_radius)
    height_step = mp.mpf("1e-6") * max(coil_radius_mp, abs(dz))
    radius_step = mp.mpf("1e-6") * min(mp.mpf(radius), coil_radius_mp)
    return height_step, radius_step


def _centred_derivative(radius, z, coil_radius, coil_z, axis, step, weight):
    """Return a fourth-order central difference of the weighted flux.

    The weight must be carried here as well: differentiating an unweighted flux
    would return an unweighted field while the flux itself carries the weight,
    which is a defect this module had and the weighted matrix comparison
    caught.
    """

    def shifted(delta):
        if axis == "z":
            return flux_psi(radius, z + delta, coil_radius, coil_z, weight)
        return flux_psi(radius + delta, z, coil_radius, coil_z, weight)

    return (8 * (shifted(step) - shifted(-step)) - (shifted(2 * step) - shifted(-2 * step))) / (
        12 * step
    )


def _richardson(first, second):
    """Return the fourth-order extrapolation of two halved-step differences."""
    return (16 * second - first) / 15


def response(radius, z, coil_radius, coil_z, weight=1):
    """Return ``(psi, B_R, B_Z)`` of one weighted ring as ``mpf`` values.

    ``B_R = -(1/R) dpsi/dZ`` and ``B_Z = (1/R) dpsi/dR``, evaluated by
    differentiating the certified flux, so the implementation's analytic
    derivative combination is never reused.  Both derivatives are computed at
    ``h`` and ``h/2`` and must agree after Richardson extrapolation to
    ``_DERIVATIVE_CERTIFICATE`` relative, which is the module's own
    convergence certificate.
    """
    with mp.workdps(DPS):
        radius_mp = mp.mpf(radius)
        psi = flux_psi(radius, z, coil_radius, coil_z, weight)
        if radius_mp == 0:
            # The two field components are the finite limits of dpsi/dZ / R and
            # dpsi/dR / R; evalBsavart on the axis gives B_R = 0 and
            # B_Z = 1e-7 * weight * 2 pi a^2 / (a^2 + dz^2)^{3/2}.
            coil_radius_mp = mp.mpf(coil_radius)
            dz = mp.mpf(z) - mp.mpf(coil_z)
            axial = (
                mp.mpf(weight)
                * MU0_OVER_4PI
                * 2
                * mp.pi
                * coil_radius_mp**2
                / (coil_radius_mp**2 + dz**2) ** mp.mpf("1.5")
            )
            return psi, mp.mpf(0), axial
        height_step, radius_step = _derivative_steps(radius_mp, z, coil_radius, coil_z)
        derivatives = {}
        for axis, step in (("r", radius_step), ("z", height_step)):
            differences = [
                _centred_derivative(
                    radius_mp, mp.mpf(z), coil_radius, coil_z, axis, step / divisor, weight
                )
                for divisor in (1, 2, 4)
            ]
            first = _richardson(differences[0], differences[1])
            second = _richardson(differences[1], differences[2])
            if abs(first - second) > _DERIVATIVE_CERTIFICATE * abs(second):
                raise ReferenceNotConverged(
                    f"the d/d{axis} central differences do not converge at R="
                    f"{mp.nstr(radius_mp, 8)}: extrapolations {mp.nstr(first, 8)} and "
                    f"{mp.nstr(second, 8)} differ by {mp.nstr(abs(first - second), 5)}"
                )
            derivatives[axis] = second
        return psi, -derivatives["z"] / radius_mp, derivatives["r"] / radius_mp


def superpose(filaments, radius, z):
    """Return the exact-precision ``(psi, B_R, B_Z)`` of weighted rings.

    ``filaments`` holds ``(R_m, Z_m, weight)`` rows; zero radius and zero weight
    rows are inactive, matching the implementation's declared skip rule.
    """
    with mp.workdps(DPS):
        psi = radial = axial = mp.mpf(0)
        for coil_radius, coil_z, weight in filaments:
            if mp.mpf(coil_radius) == 0 or mp.mpf(weight) == 0:
                continue
            row = response(radius, z, coil_radius, coil_z, weight)
            psi, radial, axial = psi + row[0], radial + row[1], axial + row[2]
        return psi, radial, axial


def integrand_scale(radius, z, coil_radius, coil_z):
    """Return the three ``2 pi * max|integrand|`` bounds of one loop.

    This is the scale a fixed-breakpoint rule controls, used for the absolute
    statements the tests make below ``MIN_RADIUS_RATIO``.
    """
    with mp.workdps(DPS):
        radius_mp, coil_radius_mp = mp.mpf(radius), mp.mpf(coil_radius)
        dz = mp.mpf(z) - mp.mpf(coil_z)
        separation = mp.sqrt((radius_mp - coil_radius_mp) ** 2 + dz**2)
        return (
            2 * mp.pi * coil_radius_mp / separation,
            2 * mp.pi * coil_radius_mp * abs(dz) / separation**3,
            2 * mp.pi * (coil_radius_mp**2 + coil_radius_mp * radius_mp) / separation**3,
        )


__all__ = [
    "FIELD_BUDGET",
    "MIN_RADIUS_RATIO",
    "MU0_OVER_4PI",
    "PSI_BUDGET",
    "ReferenceNotConverged",
    "flux_psi",
    "integrand_scale",
    "response",
    "superpose",
]
