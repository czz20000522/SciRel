"""Closed-form identities for the angular primitives, the wavevector projection and the flux-surface reductions.

Assets: ``scirel.geometry.theta-chord``, ``scirel.geometry.spherical-r-chord``,
``scirel.geometry.planar-wavevector-projection``,
``scirel.geometry.flux-surface-profile``,
``scirel.geometry.flux-surface-inverse-field-average``.

The *independent basis* is, per asset, one of four kinds and never a restatement
of the code:

1. **Analytic identity.** For the two angular chords the identity is
   Pythagoras, ``R**2 + Z**2 == r**2``, which any correct spherical-to-cylindrical
   map satisfies for every angle and radius, and which a swapped axis, a wrong
   trigonometric pairing, a wrong unit or a missing factor all break.  The 3-4-5
   triple ``(r, R, Z) = (5, 3, 4)`` is the exact case: ``hypot(3, 4) = 5`` by
   definition of a Pythagorean triple, so the identity is required to hold
   bitwise there rather than within a tolerance.
2. **Closed form of the projection.** ``k = hypot(kx, kz)`` and
   ``(kx, kz) = (k sin t, k cos t)`` compose to ``k`` itself, so the polar mode
   followed by the Cartesian mode is an identity on the magnitude; with
   ``t = atan2(3, 4)`` the composition returns ``5`` exactly.
3. **Exact rational recomputation.** The two chords are ``R = r s`` and
   ``Z = r c`` for the *rounded* ``s`` and ``c``; recomputing those two products
   in ``fractions.Fraction`` tests the products and their axis assignment with no
   rounding at all.  The linear flux profile is reproduced by the closed form
   ``y0 + (y1 - y0) (t - x0) / (x1 - x0)``, which is exact on dyadic data; the
   test evaluates it in ``Fraction`` and compares bitwise.
4. **Integral identity (linearity).** The inverse-field reduction is a ratio of
   two trapezoidal integrals, ``Integral(q/B) / Integral(1/B)``.  For a constant
   field both integrals reduce to ``L / B`` and the ratio to the plain mean of
   ``q`` along the path, and the map is affine in ``q``: ``q -> q + c`` shifts the
   mean by ``c`` and ``q -> a q`` scales it by ``a``.  Those scaling laws are
   consequences of linearity, not regularities that happened to appear in a run,
   so they are asserted as identities.

Precision budgets, fixed before measurement (``eps = 2.22e-16``):

* Each chord coordinate is one rounded sine or cosine times one rounded product,
  so its distance from the exact rational value is at most ``eps * |r|``; the
  measured residual is quoted in the test rather than folded into the bound.
* Pythagoras on a non-Pythagorean case admits ``8 * eps * r**2`` (two products
  plus one sum, both operands from a map that is itself 1 ulp from the exact
  sine and cosine).  On the 3-4-5 case it is required to be exact.
* The projection admits ``4 * eps * k`` per component (one transcendental, one
  product) and ``8 * eps * k`` for the composed magnitude (``hypot`` is
  documented within 1 ulp).  The 3-4-5 case is exact.
* The linear profile admits ``4 * eps * scale`` with ``scale`` the larger of
  ``|y|`` and the sample range; dyadic cases are required to be bitwise.
* ``dl_B`` admits ``8 * eps * L / B`` over ``n - 1`` segment lengths and
  ``n - 2`` trapezoid terms; the weighted mean inherits that plus one division.

The matrix covers normal rows, boundaries (``theta = 0`` and ``180``,
``k = 0``, the endpoint policy, the first and last knot), degenerate rows (a
single angle, two knots, a quantity that is constant), asymmetric rows (an
unequal ``nr``/``nz`` grid, a path with unequal segments, a duplicated flux
coordinate) and one rejection per declared failure channel.
"""

from __future__ import annotations

import math
from fractions import Fraction

import numpy as np
import pytest

from scirel.geometry import SphericalRChord, ThetaChord
from scirel.geometry.flux_surface_inverse_field_average import (
    compute_flux_surface_inverse_field_average,
)
from scirel.geometry.flux_surface_profile import evaluate_flux_surface_profile
from scirel.geometry.planar_wavevector import project_planar_wavevector

EPS = np.finfo(float).eps


def _exact(value):
    """Exact rational value of the binary64 number ``value``."""
    return Fraction(float(value))


# --------------------------------------------------------------------------- #
# theta-chord and spherical-r-chord: Pythagoras and the exact-rational product
# --------------------------------------------------------------------------- #


def test_the_pythagorean_triple_is_reproduced_bitwise():
    """(r, R, Z) = (5, 3, 4): hypot(3, 4) is exactly 5, so the map must be exact."""
    angle = math.atan2(3.0, 4.0)
    chord = SphericalRChord([5.0], angle)
    assert chord.R[0] == 3.0 and chord.Z[0] == 4.0
    assert chord.R[0] ** 2 + chord.Z[0] ** 2 == 25.0


def test_pythagoras_holds_across_angles_and_radii():
    """R**2 + Z**2 = r**2 at five angles, including the axis and its opposite."""
    radii = np.array([0.5, 1.0, 2.0])
    for angle in (0.0, 17.0, 45.0, 90.0, 180.0):
        chord = SphericalRChord(radii, math.radians(angle))
        residual = chord.R**2 + chord.Z**2 - radii**2
        assert np.all(np.abs(residual) <= 8 * EPS * radii**2), angle
        assert np.all(chord.R >= 0.0), angle


def test_chord_products_match_an_exact_rational_recomputation():
    """R = r s and Z = r c for the rounded s and c, with no rounding left over."""
    radius, angle = 2.5, math.radians(37.0)
    sine = math.sin(angle)
    cosine = math.cos(angle)
    chord = SphericalRChord([radius], angle)
    assert abs(_exact(chord.R[0]) - _exact(radius) * _exact(sine)) <= EPS * radius
    assert abs(_exact(chord.Z[0]) - _exact(radius) * _exact(cosine)) <= EPS * radius
    # The measured residual is one ulp of the radius on R and zero on Z, i.e. the
    # products themselves are exact and only the one rounding of ``s`` shows.
    assert _exact(chord.R[0]) - _exact(radius) * _exact(sine) == Fraction(1, 2**53)
    assert _exact(chord.Z[0]) - _exact(radius) * _exact(cosine) == 0


def test_the_two_chord_families_agree_bitwise():
    """ThetaChord(r0, t) is SphericalRChord(r0, t) with the radius held fixed."""
    for angle in (0.0, 30.0, 60.0, 90.0, 135.0, 180.0):
        by_angle = ThetaChord([math.radians(angle)], 1.5)
        by_radius = SphericalRChord([1.5], math.radians(angle))
        assert np.array_equal(by_angle.R, by_radius.R), angle
        assert np.array_equal(by_angle.Z, by_radius.Z), angle


def test_angular_chord_boundaries_and_rejections():
    """The axis, its opposite, a degenerate single radius, and every failure channel."""
    on_axis = SphericalRChord([2.0], 0.0)
    assert on_axis.R[0] == 0.0 and on_axis.Z[0] == 2.0
    opposite = SphericalRChord([2.0], math.pi)
    assert opposite.Z[0] == -2.0
    assert abs(opposite.R[0]) <= 8 * EPS * 2.0
    quarter = SphericalRChord([2.0], math.pi / 2)
    assert quarter.R[0] == 2.0
    # The residual on Z at 90 degrees is exactly the documented cosine rounding.
    assert _exact(quarter.Z[0]) == _exact(2.0) * _exact(math.cos(math.pi / 2))

    with pytest.raises(ValueError, match="non-negative"):
        SphericalRChord([-1.0], math.pi / 2)
    with pytest.raises(ValueError, match="finite"):
        SphericalRChord([np.nan], 0.0)
    with pytest.raises(ValueError, match="non-negative"):
        ThetaChord([math.pi / 2], -1.0)
    # The declared -0.0 note: a signed zero radius passes the generated-R check.
    allowed = SphericalRChord([-0.0], 0.0)
    assert allowed.R[0] == 0.0


# --------------------------------------------------------------------------- #
# planar-wavevector-projection: the closed form and the round trip on k
# --------------------------------------------------------------------------- #


def test_the_projection_composes_back_to_the_magnitude():
    """polar -> Cartesian returns k itself; the 3-4-5 triple is exact."""
    exact_triple = project_planar_wavevector(kx_grid=[3.0], kz_grid=[4.0])
    assert exact_triple["k"][0] == 5.0

    magnitudes = np.array([5.0, 2.0, 0.3, 1e6])
    angle = math.atan2(3.0, 4.0)
    polar = project_planar_wavevector(k_grid=magnitudes, theta_rad=angle)
    assert np.all(np.abs(polar["kx"] - 0.6 * magnitudes) <= 4 * EPS * magnitudes)
    assert np.all(np.abs(polar["kz"] - 0.8 * magnitudes) <= 4 * EPS * magnitudes)
    cartesian = project_planar_wavevector(kx_grid=polar["kx"], kz_grid=polar["kz"])
    assert np.all(np.abs(cartesian["k"] - magnitudes) <= 8 * EPS * magnitudes)
    # The magnitude is carried, not recomputed, in polar mode: this is exact.
    assert np.array_equal(polar["k"], magnitudes)


def test_the_projection_keeps_the_declared_boundaries():
    """Zero magnitude keeps its angle; Cartesian mode declares no angle."""
    zero = project_planar_wavevector(k_grid=[0.0], theta_rad=0.7)
    assert zero["kx"][0] == 0.0 and zero["kz"][0] == 0.0
    assert zero["theta_rad"] == 0.7
    assert zero["projection_mode"] == "polar"
    cartesian = project_planar_wavevector(kx_grid=[3.0, -3.0], kz_grid=[4.0, 4.0])
    assert cartesian["theta_rad"] is None
    assert cartesian["projection_mode"] == "cartesian"
    # An asymmetric pair (one negative component) keeps its sign through the mode.
    assert np.array_equal(cartesian["kx"], np.array([3.0, -3.0]))
    assert np.all(cartesian["k"] == 5.0)


def test_the_projection_rejects_each_declared_channel():
    """One executable assertion per ``failure_semantics`` entry of the projection."""
    with pytest.raises(ValueError, match="choose a magnitude sweep"):
        project_planar_wavevector(k_grid=[1.0], kx_grid=[1.0], kz_grid=[1.0])
    with pytest.raises(ValueError, match="both component grids are required"):
        project_planar_wavevector(kx_grid=[1.0])
    with pytest.raises(ValueError, match="nonnegative"):
        project_planar_wavevector(k_grid=[-1.0])
    with pytest.raises(ValueError, match="nonempty finite real vector"):
        project_planar_wavevector(k_grid=[1.0, True])
    with pytest.raises(ValueError, match="theta_rad must be a finite real scalar"):
        project_planar_wavevector(k_grid=[1.0], theta_rad=np.inf)
    with pytest.raises(ValueError, match="paired nonempty vectors"):
        project_planar_wavevector(kx_grid=[1.0, 2.0], kz_grid=[1.0])
    with pytest.raises(ValueError, match="exceeds the finite numeric domain"):
        project_planar_wavevector(kx_grid=[1.7e308], kz_grid=[1.7e308])


# --------------------------------------------------------------------------- #
# flux-surface-profile: the linear closed form, evaluated exactly
# --------------------------------------------------------------------------- #


def test_a_linear_profile_is_reproduced_by_its_exact_rational_closed_form():
    """y(t) = y0 + (y1 - y0)(t - x0)/(x1 - x0), evaluated in ``Fraction``.

    Dyadic samples and dyadic targets keep every step of that expression exact,
    so the comparison is bitwise; no tolerance is needed or used.
    """
    coordinates = [0.0, 0.125, 1.0, 8.0]
    values = [0.0, 0.25, 2.0, 16.0]  # y = 2 x at every knot
    targets = [0.0625, 0.5, 3.0, 4.0]
    result = evaluate_flux_surface_profile(psi_samples=coordinates, values=values, target=targets)
    for target, got in zip(targets, result["values"]):
        exact = _exact(0.0) + _exact(2.0) * (_exact(target) - _exact(0.0))
        assert _exact(got) == exact, target


def test_the_profile_identity_is_independent_of_the_sample_order():
    """Permuting the (coordinate, value) pairs leaves the interpolant unchanged."""
    coordinates = np.array([2.0, 0.0, 1.0, 0.5])
    values = np.array([4.0, 0.0, 2.0, 1.0])
    targets = np.array([0.25, 0.75, 1.5])
    forward = evaluate_flux_surface_profile(psi_samples=coordinates, values=values, target=targets)
    shuffled = evaluate_flux_surface_profile(
        psi_samples=coordinates[[2, 0, 3, 1]], values=values[[2, 0, 3, 1]], target=targets
    )
    assert np.array_equal(forward["values"], shuffled["values"])
    assert np.array_equal(forward["psi"], shuffled["psi"])


def test_the_profile_boundaries_degeneracies_and_rejections():
    """Knots, endpoint policy, a duplicated coordinate and both rejection channels."""
    res = evaluate_flux_surface_profile(
        psi_samples=[2.0, 0.0, 1.0, 1.0],
        values=[4.0, 0.0, 2.0, 3.0],
        target=[0.0, 1.0, 2.0, -1.0, 3.0],
        left=-7.0,
        right=9.0,
    )
    # The first and last knots are exact and the duplicate keeps its first value.
    assert np.array_equal(res["values"], np.array([0.0, 2.0, 4.0, -7.0, 9.0]))
    assert np.array_equal(res["psi"], np.array([0.0, 1.0, 2.0]))
    assert np.array_equal(res["profile_values"], np.array([0.0, 2.0, 4.0]))
    # Default endpoint values are the first and last retained samples.
    defaulted = evaluate_flux_surface_profile(
        psi_samples=[0.0, 1.0], values=[1.5, 2.5], target=[-2.0, 2.0]
    )
    assert np.array_equal(defaulted["values"], np.array([1.5, 2.5]))

    with pytest.raises(ValueError, match="at least two paired samples"):
        evaluate_flux_surface_profile(psi_samples=[0.0], values=[0.0], target=[0.0])
    with pytest.raises(ValueError, match="do not span a usable interval"):
        evaluate_flux_surface_profile(psi_samples=[1.0, 1.0], values=[0.0, 2.0], target=[1.0])
    with pytest.raises(ValueError, match="must be finite"):
        evaluate_flux_surface_profile(psi_samples=[0.0, 1.0], values=[0.0, np.nan], target=[0.5])
    with pytest.raises(ValueError, match="endpoint values must be finite"):
        evaluate_flux_surface_profile(
            psi_samples=[0.0, 1.0], values=[0.0, 1.0], target=[0.5], left=np.inf
        )


# --------------------------------------------------------------------------- #
# flux-surface-inverse-field-average: the ratio-of-integrals identities
# --------------------------------------------------------------------------- #


def _constant_field_grid(nr=5, nz=4, field=2.0):
    """A rectilinear R-Z grid with an unequal (nz, nr) shape and a constant field."""
    r_grid, z_grid = np.meshgrid(np.linspace(0.1, 1.0, nr), np.linspace(-1.0, 1.0, nz))
    return r_grid, z_grid, np.full_like(r_grid, field)


def test_a_constant_field_reduces_both_integrals_to_length_over_field():
    """Integral(1/B) = L/B and the mean of a constant quantity is that quantity."""
    r_grid, z_grid, field = _constant_field_grid()
    line = np.array([[0.2, -0.5], [0.4, 0.0], [0.6, 0.5]])
    length = float(np.linalg.norm(np.diff(line, axis=0), axis=1).sum())

    measured = compute_flux_surface_inverse_field_average(r_grid, z_grid, field, line)
    assert abs(measured["dl_B"] - length / 2.0) <= 8 * EPS * length / 2.0
    assert "flux_surface_average" not in measured

    quantity = np.full_like(r_grid, 3.0)
    weighted = compute_flux_surface_inverse_field_average(r_grid, z_grid, field, line, quantity)
    assert abs(weighted["flux_surface_average"] - 3.0) <= 8 * EPS * 3.0


def test_the_weighted_mean_is_the_plain_mean_of_a_field_linear_along_the_path():
    """Along a straight radial path R is linear in arclength, so the trapezoid is exact.

    With B constant the weight ``dl/B`` is uniform, so the ratio of integrals is
    the unweighted mean of R over the segment, ``(R_first + R_last) / 2``.  That
    is the analytic value, not a value read from the run.
    """
    r_grid, z_grid, field = _constant_field_grid()
    line = np.array([[0.2, 0.0], [0.5, 0.0], [1.0, 0.0]])
    quantity = r_grid.copy()
    measured = compute_flux_surface_inverse_field_average(r_grid, z_grid, field, line, quantity)
    assert abs(measured["flux_surface_average"] - 0.6) <= 8 * EPS * 1.0


def test_the_weighted_mean_obeys_the_two_affine_scaling_laws():
    """q -> q + c shifts the mean by c; q -> a q scales it by a; B -> a B halves dl_B.

    Both follow from the integral being linear in ``q`` and homogeneous of degree
    -1 in ``B``; they are identities of the reduction, not coincidences.
    """
    r_grid, z_grid, field = _constant_field_grid()
    line = np.array([[0.2, -0.5], [0.4, 0.0], [0.6, 0.5]])
    base = r_grid + 0.25 * z_grid

    plain = compute_flux_surface_inverse_field_average(r_grid, z_grid, field, line, base)[
        "flux_surface_average"
    ]
    shifted = compute_flux_surface_inverse_field_average(r_grid, z_grid, field, line, base + 1.5)[
        "flux_surface_average"
    ]
    scaled = compute_flux_surface_inverse_field_average(r_grid, z_grid, field, line, -3.0 * base)[
        "flux_surface_average"
    ]
    assert abs(shifted - (plain + 1.5)) <= 8 * EPS * (abs(plain) + 1.5)
    assert abs(scaled - (-3.0 * plain)) <= 8 * EPS * 3.0 * abs(plain)

    doubled = compute_flux_surface_inverse_field_average(r_grid, z_grid, 2.0 * field, line)["dl_B"]
    single = compute_flux_surface_inverse_field_average(r_grid, z_grid, field, line)["dl_B"]
    assert abs(doubled - single / 2.0) <= 8 * EPS * single


def test_the_inverse_field_reduction_rejects_each_declared_channel():
    """One executable assertion per ``failure_semantics`` entry of the reduction."""
    r_grid, z_grid, field = _constant_field_grid()
    line = np.array([[0.2, 0.0], [0.6, 0.0]])
    with pytest.raises(ValueError, match="equal-shape 2-D grids"):
        compute_flux_surface_inverse_field_average(r_grid[0], z_grid, field, line)
    with pytest.raises(ValueError, match="must match the R-Z grid"):
        compute_flux_surface_inverse_field_average(r_grid, z_grid, field, line, r_grid[0])
    with pytest.raises(ValueError, match="must contain only finite values"):
        compute_flux_surface_inverse_field_average(
            r_grid, z_grid, np.where(r_grid > 0.5, np.nan, field), line
        )
    with pytest.raises(ValueError, match="strictly positive"):
        compute_flux_surface_inverse_field_average(r_grid, z_grid, np.zeros_like(field), line)
    with pytest.raises(ValueError, match="inside the R-Z grid"):
        compute_flux_surface_inverse_field_average(
            r_grid, z_grid, field, np.array([[5.0, 0.0], [0.6, 0.0]])
        )
    with pytest.raises(ValueError, match="nondegenerate polyline"):
        compute_flux_surface_inverse_field_average(
            r_grid, z_grid, field, np.array([[0.2, 0.0], [0.2, 0.0]])
        )
    with pytest.raises(ValueError, match="at least four points per axis"):
        small_r, small_z = np.meshgrid(np.linspace(0.2, 0.8, 3), np.linspace(-1.0, 1.0, 4))
        compute_flux_surface_inverse_field_average(
            small_r, small_z, np.full_like(small_r, 2.0), line
        )
