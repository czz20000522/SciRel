"""Independent Biot-Savart quadrature reference for the axisymmetric ring field.

Why this is a second source and not the same backend under another name
-----------------------------------------------------------------------
Every ``field`` asset in this batch is a composition around one relation: the
magnetic field of an ideal circular current filament.  The maintained
implementation evaluates that relation in closed form.  ``scirel.electromagnetism.
greens.compute_greens`` selects a small-modulus hypergeometric branch
(``scipy.special.hyp2f1``) below ``m = 0.5``, the complementary elliptic branch
(``scipy.special.ellipkm1`` and ``ellipe``) above it, and threads a separate
binary exponent through Dekker-split compensated products.  The maintained
oracle in ``tests/field/test_filament_coil_green.py`` recomputes the *same*
closed form with ``mpmath`` at 50 digits: that is a second implementation of the
same derivation, so it can be wrong in the same way.

Nothing in this module uses an elliptic integral, a hypergeometric series, or
the stream-function closed form.  Every quantity is obtained by direct
high-precision quadrature of the Biot-Savart law over the loop parameter, which
is the definition the closed form is derived *from*:

    A(r)   = (mu0 I / 4 pi) * closed-integral of dl' / |r - r'|
    B(r)   = (mu0 I / 4 pi) * closed-integral of dl' x (r - r') / |r - r'|^3

For an observation point at cylindrical ``(R, 0, Z)`` and a loop of radius ``a``
at height ``z0`` parameterised by ``phi``, the four ingredients are

    r'      = (a cos phi, a sin phi, z0)
    dl'     = (-a sin phi, a cos phi, 0) dphi
    |r-r'|^2 = R^2 + a^2 - 2 R a cos phi + dz^2,        dz = Z - z0
    dl' x (r-r') = ( a cos phi dz,  a sin phi dz,  a^2 - a R cos phi )

The middle Cartesian component integrates to zero over a full turn (it is odd
about ``phi = 0``), so the field is purely poloidal and the three nonzero
outputs are

    psi = R * A_phi = R * (mu0 I / 4 pi) * integral a cos phi / |r-r'| dphi
    B_R = (mu0 I / 4 pi) * integral a cos phi dz / |r-r'|^3 dphi
    B_Z = (mu0 I / 4 pi) * integral (a^2 - a R cos phi) / |r-r'|^3 dphi

and ``mu0 / 4 pi = 1e-7`` exactly (``mu0 = 4 pi 1e-7``), so the prefactor carries
no transcendental constant of its own.

Sign and unit convention, checked against the physical setup rather than against
the implementation
--------------------------------------------------------------------------
- A positive current flows in the ``+phi`` direction.  Then ``B_Z`` on the axis
  above the loop is positive, which the ``B_Z`` integrand reproduces because
  ``(a^2 - a R cos phi) > 0`` for ``R < a``.
- ``psi = R A_phi`` in Wb/rad per ampere, so ``B_R = -(1/R) dpsi/dZ`` and
  ``B_Z = (1/R) dpsi/dR``.  The module therefore also offers ``dpsi_dz`` and
  ``dpsi_dr``, obtained by high-precision differentiation of the *quadrature*
  result rather than by evaluating the implementation's analytic derivative
  combination.  That is what makes the stream-function identities an independent
  check instead of a restatement.

Precision budget and where it comes from
----------------------------------------
Three separate questions, each with its own bound fixed before any comparison
against the implementation was run.

1. **Is the quadrature itself converged?**  ``mp.quad`` defaults to tanh-sinh
   and refines until its own working precision is exhausted.  Rather than trust
   that, every call is made at two working precisions (30 and 60 decimal digits)
   with the integrand split at twelve fixed breakpoints of ``[0, 2 pi]``.

   The two runs are compared **against the integrand scale, not against the
   answer**, because the ``A_phi`` and ``B_R`` integrals are themselves
   cancellation-reduced: the ``O(1)`` part of the ``a cos phi / |r-r'|``
   integrand is odd about ``phi = 0`` and integrates to zero, so their value
   falls like ``R^2`` and ``R`` on the axis while the integrand stays ``O(1)``.
   A relative certificate would therefore punish the reference for a property
   of the integral rather than of the quadrature.  ``_integrand_scale`` bounds
   ``integral |integrand| dphi`` from above by ``2 pi`` times the largest
   integrand magnitude, which is at most ``a / d_min`` for ``A_phi`` and
   ``(a^2 + a R) / d_min^3`` for ``B_Z`` with ``d_min = sqrt((R-a)^2 + dz^2)``;
   a quadrature rule at ``D`` decimal digits has error at most about
   ``10^-D * scale`` for these analytic integrands.  The certificate requires
   ``|weak - strong| <= 1e-25 * scale``, which the 30-digit run can satisfy with
   five digits of margin, and which then certifies the 60-digit value used as
   the reference to ``1e-25 * scale`` absolute.  Even at ``R = 1e-12 a``, where
   ``psi`` is ``~1e-24`` of the integrand scale, that leaves the reference
   correct to better than ``1e-13`` relative — one order above the binary64
   budget below, and the tests restrict relative comparisons to
   ``R >= _MIN_RADIUS_RATIO * a`` where the reference keeps far more margin than
   that.

2. **How large a relative deviation from a binary64 closed form is expected?**
   ``_RELATIVE_BUDGET = 64 * eps`` with ``eps = 2**-52`` (``1.4e-14`` relative).
   Derivation: the closed form evaluates a chain of roughly 30 floating-point
   operations (two geometry squares, one square root, a modulus ratio, two
   elliptic evaluations, two products, one subtraction), and the summation and
   product path is compensated, so the leading error is the ordinary
   ``N * eps`` accumulation for ``N`` in the low tens.  ``64 * eps`` is that
   allowance rounded up to a power of two, not a value fitted to an observed
   difference.  It is an **observed budget for the sampled grid**, not a proven
   continuous bound: the maximum over a finite grid is not a bound over the
   interval between grid points.

3. **Where does the budget stop applying?**  Two geometries break the
   convergence premise of (1) rather than the correctness of anything:

   - a target within ``1e-2 * a`` of the wire, where the ``|r-r'|^-3`` integrand
     is too sharply peaked for a fixed-breakpoint tanh-sinh rule to reach
     ``1e-25``;
   - a target with ``R`` below ``1e-6 * a``, where ``psi`` and ``B_R`` tend to
     zero like ``R^2`` and ``R``, so a *relative* comparison of ``psi`` loses
     resolution faster than the certified absolute error of the reference
     grows.  The suite compares ``psi`` and ``B_R`` relatively only above that
     ratio and, below it, uses absolute differences against the integrand
     scale stated in (1).

   ``_MIN_SEPARATION_RATIO`` encodes the first limit inside the reference, and
   ``_MIN_RADIUS_RATIO`` is the ratio above which the suite makes *relative*
   statements; both are stated in the contract's evidence ceiling rather than
   pretended away.
"""

from __future__ import annotations

import mpmath as mp

MU0_OVER_4PI = mp.mpf("1e-7")
_STRONG_DPS = 60
_WEAK_DPS = 30
_CROSS_PRECISION = mp.mpf("1e-25")
_RELATIVE_BUDGET = 64.0 * 2.0**-52
_MIN_SEPARATION_RATIO = mp.mpf("1e-2")
_MIN_RADIUS_RATIO = mp.mpf("1e-6")
_TAU = 2 * mp.pi


class QuadratureNotConverged(RuntimeError):
    """Raised when the 30- and 60-digit quadratures disagree beyond tolerance."""


def _breakpoints():
    """Return the fixed twelve-fold split of ``[0, 2 pi]`` used for every call."""
    return [mp.pi * index / 6 for index in range(13)]


def _separation_squared(radius, coil_radius, dz, phi):
    """Return ``|r - r'|^2`` for a loop parameter ``phi``."""
    return radius**2 + coil_radius**2 - 2 * radius * coil_radius * mp.cos(phi) + dz**2


def _loop_integrals(radius, coil_radius, dz):
    """Integrate the three Biot-Savart kernels of one loop at one working precision."""
    a, R = mp.mpf(coil_radius), mp.mpf(radius)
    points = _breakpoints()

    def a_phi(phi):
        return a * mp.cos(phi) / mp.sqrt(_separation_squared(R, a, dz, phi))

    def b_r(phi):
        inverse_cubed = _separation_squared(R, a, dz, phi) ** mp.mpf("-1.5")
        return a * mp.cos(phi) * dz * inverse_cubed

    def b_z(phi):
        inverse_cubed = _separation_squared(R, a, dz, phi) ** mp.mpf("-1.5")
        return (a**2 - a * R * mp.cos(phi)) * inverse_cubed

    return mp.quad(a_phi, points), mp.quad(b_r, points), mp.quad(b_z, points)


def _integrand_scale(radius, coil_radius, dz):
    """Return the three integrand bounds ``2 pi * max|integrand|`` of one loop.

    ``|r - r'|`` is smallest at ``cos phi = 1``, so
    ``d_min = sqrt((R - a)^2 + dz^2)`` bounds every ``1/|r-r'|`` factor from
    above.  Multiplying the resulting pointwise bound by the ``2 pi`` measure
    gives the scale a ``D``-digit quadrature rule controls, as opposed to the
    (possibly much smaller) value of the cancellation-reduced integral.
    """
    a, r = mp.mpf(coil_radius), mp.mpf(radius)
    d_min = mp.sqrt((r - a) ** 2 + dz**2)
    return (
        _TAU * a / d_min,
        _TAU * a * abs(dz) / d_min**3,
        _TAU * (a**2 + a * r) / d_min**3,
    )


def _quadrature_at(dps, radius, coil_radius, dz):
    """Return the three raw loop integrals and their integrand scales at ``dps``."""
    with mp.workdps(dps):
        radius_mp, coil_radius_mp, dz_mp = (
            mp.mpf(radius),
            mp.mpf(coil_radius),
            mp.mpf(dz),
        )
        if radius_mp < 0:
            raise ValueError("the reference is defined for nonnegative target radius")
        if radius_mp > 0:
            separation = mp.sqrt((radius_mp - coil_radius_mp) ** 2 + dz_mp**2)
            if separation < _MIN_SEPARATION_RATIO * coil_radius_mp:
                raise ValueError(
                    "target too close to the wire for a fixed-breakpoint quadrature"
                )
        scale = _integrand_scale(radius_mp, coil_radius_mp, dz_mp)
        if radius_mp == 0:
            # Closed limits on the axis, reached from the same integrands: A_phi
            # is an odd integrand there and B_R carries dz as a factor, so both
            # vanish identically, while B_Z stays an ordinary smooth integral.
            return (mp.mpf(0), mp.mpf(0), _loop_integrals(radius_mp, coil_radius_mp, dz_mp)[2]), scale
        return _loop_integrals(radius_mp, coil_radius_mp, dz_mp), scale


def ring_field(radius, z, coil_radius, coil_z, current=1.0):
    """Return ``(psi, B_R, B_Z)`` per drive of one ring as floats.

    The value returned is the 60-digit quadrature, after the 30-digit run has
    been shown to agree with it to ``1e-25`` of the integrand scale.  The
    certificate is what makes the returned value usable as a reference: a
    half-converged integral fails here instead of being compared against the
    implementation as if it were truth.
    """
    dz = mp.mpf(z) - mp.mpf(coil_z)
    weak, scale = _quadrature_at(_WEAK_DPS, radius, coil_radius, dz)
    strong, _unused_strong_scale = _quadrature_at(_STRONG_DPS, radius, coil_radius, dz)
    prefactor = MU0_OVER_4PI * mp.mpf(current)
    radius_mp = mp.mpf(radius)
    psi = radius_mp * prefactor * strong[0]
    for name, weak_value, strong_value, integrand_scale in zip(
        ("psi", "B_R", "B_Z"),
        (radius_mp * prefactor * weak[0], prefactor * weak[1], prefactor * weak[2]),
        (psi, prefactor * strong[1], prefactor * strong[2]),
        (
            abs(radius_mp) * abs(prefactor) * scale[0],
            abs(prefactor) * scale[1],
            abs(prefactor) * scale[2],
        ),
        strict=True,
    ):
        if abs(weak_value - strong_value) > _CROSS_PRECISION * integrand_scale:
            raise QuadratureNotConverged(
                f"the {_WEAK_DPS}- and {_STRONG_DPS}-digit {name} quadratures disagree by "
                f"{mp.nstr(abs(weak_value - strong_value), 5)} against an integrand scale of "
                f"{mp.nstr(integrand_scale, 5)}"
            )
    return psi, prefactor * strong[1], prefactor * strong[2]


def _single_field(filaments, radius, z, dps):
    """Sum the quadrature response of a ring set at one working precision.

    No cross-precision certificate is attached, because the caller needs this
    inside an outer quadrature or a central difference where a second
    quadrature per evaluation would multiply the cost.  The certificate for the
    same geometry is supplied by :func:`ring_field`, and the 60-digit value used
    here keeps at least 30 digits of margin over the ``1e-25 * scale`` bound
    that certificate establishes.
    """
    with mp.workdps(dps):
        radius_mp, height_mp = mp.mpf(radius), mp.mpf(z)
        psi = b_r = b_z = mp.mpf(0)
        for coil_radius, coil_z, weight in filaments:
            weight_mp, coil_radius_mp = mp.mpf(weight), mp.mpf(coil_radius)
            if weight_mp == 0 or coil_radius_mp == 0:
                continue
            dz = height_mp - mp.mpf(coil_z)
            if radius_mp > 0:
                separation = mp.sqrt((radius_mp - coil_radius_mp) ** 2 + dz**2)
                if separation < _MIN_SEPARATION_RATIO * coil_radius_mp:
                    raise ValueError("target too close to the wire for the reference")
            a_phi, radial, axial = _loop_integrals(radius_mp, coil_radius_mp, dz)
            prefactor = MU0_OVER_4PI * weight_mp
            psi += radius_mp * prefactor * a_phi
            b_r += prefactor * radial
            b_z += prefactor * axial
        return psi, b_r, b_z


def filament_field(filaments, radius, z):
    """Return the certified superposed ``(psi, B_R, B_Z)`` of weighted rings.

    ``filaments`` is a sequence of ``(R_m, Z_m, weight)`` rows; the weight plays
    the role of the drive current, so the returned values are per unit of the
    third column, exactly as the implementation's ``rzw`` third column is.
    """
    psi = b_r = b_z = mp.mpf(0)
    for coil_radius, coil_z, weight in filaments:
        if mp.mpf(weight) == 0 or mp.mpf(coil_radius) == 0:
            continue
        row_psi, row_b_r, row_b_z = ring_field(radius, z, coil_radius, coil_z, weight)
        psi, b_r, b_z = psi + row_psi, b_r + row_b_r, b_z + row_b_z
    return psi, b_r, b_z


def axial_field(radius, z, filaments):
    """Return only the axial field of a weighted loop set as a float."""
    return filament_field(filaments, radius, z)[2]


def dpsi_dz(radius, z, filaments, step=None):
    """Return ``dpsi/dZ`` of the quadrature stream function.

    Differentiating the *quadrature* value, not the closed form, is what makes
    ``B_R = -(1/R) dpsi/dZ`` an independent statement: the implementation
    obtains ``B_R`` from an analytic derivative combination, while this route
    only knows the integral definition of ``psi``.  With ``60`` digits and a
    central step of ``1e-15`` the truncation error is ``h^2`` times the third
    derivative of ``psi`` and the cancellation costs about fifteen digits, so the
    difference numerator is still good to roughly ``30`` digits.
    """
    step = mp.mpf("1e-15") if step is None else mp.mpf(step)
    up = _single_field(filaments, mp.mpf(radius), mp.mpf(z) + step, _STRONG_DPS)[0]
    down = _single_field(filaments, mp.mpf(radius), mp.mpf(z) - step, _STRONG_DPS)[0]
    return (up - down) / (2 * step)


def dpsi_dr(radius, z, filaments, step=None):
    """Return ``dpsi/dR`` of the quadrature stream function."""
    step = mp.mpf("1e-15") if step is None else mp.mpf(step)
    up = _single_field(filaments, mp.mpf(radius) + step, mp.mpf(z), _STRONG_DPS)[0]
    down = _single_field(filaments, mp.mpf(radius) - step, mp.mpf(z), _STRONG_DPS)[0]
    return (up - down) / (2 * step)


def psi_by_radial_integration(radius, z, filaments, start_radius):
    """Return ``integral from start_radius to radius of R' B_Z(R', Z) dR'``.

    This is the definition the implementation's cumulative trapezoid
    approximates, not the approximation itself: ``dpsi/dR = R B_Z`` holds for
    ``psi = R A_phi``, so the radial integral of ``R' B_Z`` recovers the flux up
    to the reference value at ``start_radius``.  The outer integral is itself run
    at two working precisions with the same certificate style as
    :func:`ring_field`, so the reference does not silently carry a
    half-converged nested quadrature.
    """
    target, start = mp.mpf(radius), mp.mpf(start_radius)
    if target == start:
        return mp.mpf(0)

    def integral(dps):
        def integrand(radial):
            return radial * _single_field(filaments, radial, z, dps)[2]

        with mp.workdps(dps):
            return mp.quad(integrand, [mp.mpf(start), mp.mpf(target)])

    weak = integral(_WEAK_DPS)
    strong = integral(_STRONG_DPS)
    if abs(weak - strong) > _CROSS_PRECISION * max(abs(strong), mp.mpf("1e-300")):
        raise QuadratureNotConverged(
            f"the nested {_WEAK_DPS}- and {_STRONG_DPS}-digit radial integrals disagree: "
            f"{mp.nstr(weak, 20)} vs {mp.nstr(strong, 20)}"
        )
    return strong


__all__ = [
    "MU0_OVER_4PI",
    "QuadratureNotConverged",
    "axial_field",
    "dpsi_dr",
    "dpsi_dz",
    "filament_field",
    "psi_by_radial_integration",
    "ring_field",
]
