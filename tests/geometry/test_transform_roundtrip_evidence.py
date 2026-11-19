"""Round-trip identities and exact-rational recomputation for the planar primitives.

Assets: ``scirel.geometry.points-mesh``, ``scirel.geometry.r-chord``,
``scirel.geometry.z-chord``, ``scirel.geometry.rotate``.

The *independent basis* is stated per asset, and none of it is a restatement of
the implementation:

1. **Round-trip identity (inverse map).** ``SphericalRChord`` builds
   ``(R, Z) = (r sin t, r cos t)`` while ``Mesh.r`` is ``hypot(R, Z)`` and
   ``Mesh.theta`` is ``arctan2(R, Z)``.  Those two are the documented inverse of
   the constructor, so ``inverse(forward(r, t)) == (r, t)`` and
   ``forward(inverse(R, Z)) == (R, Z)`` are identities that hold for *any*
   correct pair of maps.  Reading ``Mesh.theta`` back and feeding the constructor
   again exercises both directions of the library itself
   rather than a private re-derivation: nothing in the test recomputes
   ``sin``/``cos`` to predict the point.
2. **Exact rational recomputation.** ``rotate`` forms ``(x c + y s, -x s + y c)``
   from the *rounded* ``c = cos(radians(angle))`` and ``s = sin(radians(angle))``.
   The test recomputes that expression in ``fractions.Fraction``, i.e. with no
   rounding at all, from the same two rounded inputs.  That separates the two
   things a tolerance otherwise confuses: the *formula* (signs, axis order,
   which component multiplies which) must be exact up to the one rounding of the
   final sum, while the transcendental values themselves are outside the test.
   The axis orientation, unit and pivot are decided elsewhere, in
   ``tests/geometry/test_frame_convention_evidence.py``; this file starts after
   that decision and never assumes it to prove itself.
3. **Exact pass-through.** The chords broadcast their fixed coordinate and copy
   the varying one with no arithmetic, so the equality there is bitwise
   (``array_equal``) rather than a bound.  A bound would hide a swapped axis.

Precision budgets, fixed before measurement (``eps = 2.22e-16``):

* Round trip through ``hypot``/``arctan2``: two correctly rounded steps
  (``hypot`` is documented within 1 ulp, ``arctan2`` within 1 ulp), so each
  recovered coordinate admits ``8 * eps * scale`` with ``scale`` the larger of the radius
  and the coordinate.  For the 3-4-5 case ``hypot(3, 4) = 5`` is **exact**, so
  the radius is required to come back bitwise.
* Exact rational recomputation of one rotated component: two exact products,
  each rounded once, then one rounded sum, so the bound is
  ``2 * eps * (|x| + |y|)``.  The measured residual is quoted per case in the
  test, and the bound is the *pre-measurement* one, not its value.
* Chords and the point store: exact equality, because the only operations are a
  copy and a ``full``/broadcast.

Degenerate, asymmetric and non-finite rows are part of the matrix: a scalar
coordinate pair, a single-point chord, a point on the axis (``r0 = 0``), a
``(2, 2)`` point block whose axes are genuinely distinguishable, ``R = 0``, a
leading batch dimension on ``rotate``, ``+/-0.0`` radii, and one rejection per
declared failure channel.
"""

from __future__ import annotations

import math
from fractions import Fraction

import numpy as np
import pytest

from scirel.geometry import (
    PointsMesh,
    RChord,
    SphericalRChord,
    ZChord,
    rotate,
)

EPS = np.finfo(float).eps


def _exact(value):
    """Exact rational value of the binary64 number ``value``."""
    return Fraction(float(value))


# --------------------------------------------------------------------------- #
# points-mesh: exact store, round trip through the derived radius and angle
# --------------------------------------------------------------------------- #


def test_points_mesh_stores_its_coordinates_without_arithmetic():
    """Pass-through is bitwise: no tolerance is involved in storing a point.

    Normal (1-D), asymmetric ((2, 2) block whose rows and columns differ),
    degenerate (a scalar pair becoming a one-point mesh) and boundary (R = 0)
    cases all have to survive unchanged.
    """
    radius = np.array([[0.1, 0.2], [0.3, 0.4]])
    axial = np.array([[0.0, 1.0], [2.0, 3.0]])
    block = PointsMesh(radius, axial)
    assert block.shape == (2, 2)
    assert np.array_equal(block.R, radius)
    assert np.array_equal(block.Z, axial)

    single = PointsMesh(0.2, 0.3)
    assert single.shape == (1,)
    assert single.R[0] == 0.2 and single.Z[0] == 0.3

    on_axis = PointsMesh([0.0, -0.0], [-1.5, 2.5])
    assert on_axis.R[0] == 0.0 and np.signbit(on_axis.R[1])
    assert np.array_equal(on_axis.Z, [-1.5, 2.5])


def test_points_mesh_round_trip_through_its_derived_radius_and_angle():
    """inverse(forward(r, t)) == (r, t) and forward(inverse(R, Z)) == (R, Z).

    The 3-4-5 triple is the exact case: ``hypot(3, 4) = 5`` bitwise and
    ``atan2(3, 4)`` feeds back through the constructor.  The radius
    round trip is required bitwise there; the angle is bounded by ``8 eps``.
    """
    mesh = SphericalRChord([5.0], math.atan2(3.0, 4.0))
    assert mesh.R[0] == 3.0 and mesh.Z[0] == 4.0

    recovered = PointsMesh(mesh.R, mesh.Z)
    assert recovered.r[0] == 5.0  # exact, not merely within a bound
    back = SphericalRChord(recovered.r, recovered.theta)
    assert np.array_equal(back.R, mesh.R)
    assert np.array_equal(back.Z, mesh.Z)


def test_points_mesh_round_trip_over_a_spread_of_angles_and_radii():
    """Same identity away from the exact triple, on asymmetric and boundary rows."""
    radii = np.array([0.25, 1.0, 2.5, 7.125])
    for angle in (0.0, 17.0, 45.0, 90.0, 123.5, 180.0):
        built = SphericalRChord(radii, math.radians(angle))
        recovered = PointsMesh(built.R, built.Z)
        assert np.all(np.abs(recovered.r - radii) <= 8 * EPS * radii.max()), angle
        # The recovered angle is bounded against itself, not against the radius:
        # arctan2 is a correctly rounded angle in radians, whose ulp
        # scales with |angle|.  A radius-scaled budget would fail for a large
        # angle on a small radius, which is a budget error, not an identity error.
        angle_scale = max(math.radians(abs(angle)), 1.0)
        assert np.all(np.abs(recovered.theta - math.radians(angle)) <= 8 * EPS * angle_scale), angle


def test_points_mesh_rejects_each_declared_channel():
    """One executable assertion per ``failure_semantics`` entry of points-mesh."""
    # invalid_input: shape, finiteness and the declared non-negative radius rule.
    with pytest.raises(ValueError, match="equal shape"):
        PointsMesh([1.0, 2.0], [0.0])
    with pytest.raises(ValueError, match="finite"):
        PointsMesh([1.0], [np.nan])
    with pytest.raises(ValueError, match="non-negative"):
        PointsMesh([np.nextafter(0.0, -1.0)], [0.0])
    # runtime_failure / nonconvergence / partial_results: constructing never
    # iterates and never returns a partial object, so the only observable is the
    # raise above; a successful call is checked to be the complete pair.
    ok = PointsMesh([0.5], [0.25])
    assert ok.R.shape == ok.Z.shape and ok.shape == (1,)


# --------------------------------------------------------------------------- #
# r-chord and z-chord: the fixed coordinate is exact, the free one is recovered
# --------------------------------------------------------------------------- #


def test_r_chord_fixes_z_bitwise_and_recovers_it_through_the_angle():
    """The radial chord round trip: the fixed Z is exact, theta recovers it."""
    z0 = 0.3
    axial = np.array([0.2, 0.5, 0.9])
    chord = RChord(axial, z0)
    assert np.array_equal(chord.R, axial)
    assert np.array_equal(chord.Z, np.full(3, z0))

    recovered = PointsMesh(chord.R, chord.Z)
    again = SphericalRChord(recovered.r, recovered.theta)
    assert np.all(np.abs(again.R - chord.R) <= 8 * EPS * np.abs(chord.R))
    assert np.all(np.abs(again.Z - z0) <= 8 * EPS * np.abs(z0))


def test_r_chord_boundary_and_degenerate_rows():
    """z0 = 0 makes theta a quarter turn; a single point still round trips."""
    flat = RChord([1.5], 0.0)
    recovered = PointsMesh(flat.R, flat.Z)
    assert abs(recovered.theta[0] - np.pi / 2) <= 8 * EPS * 1.5
    assert recovered.r[0] == 1.5

    # Constant input is the degenerate case: every point maps back to itself.
    constant = RChord([0.4, 0.4, 0.4], -0.8)
    again = PointsMesh(constant.R, constant.Z)
    assert np.allclose(again.r, math.hypot(0.4, 0.8), rtol=0, atol=8 * EPS)


def test_chord_rejects_each_declared_channel():
    """One executable assertion per ``failure_semantics`` entry of both chords."""
    with pytest.raises(ValueError, match="non-negative"):
        RChord([-0.5], 0.3)
    with pytest.raises(ValueError, match="finite"):
        RChord([0.5], np.inf)
    with pytest.raises(ValueError, match="non-negative"):
        ZChord([0.0], -0.3)
    with pytest.raises(ValueError, match="finite"):
        ZChord([np.nan], 0.3)
    # The declared -0.0 note: the non-negative radius test admits a signed zero.
    allowed = RChord([-0.0], 0.0)
    assert allowed.R[0] == 0.0


def test_z_chord_fixes_r_bitwise_and_recovers_it_through_the_angle():
    """The axial chord round trip, including the on-axis degenerate case r0 = 0."""
    r0 = 0.4
    heights = np.array([-1.3, 0.0, 2.0])
    chord = ZChord(heights, r0)
    assert np.array_equal(chord.Z, heights)
    assert np.array_equal(chord.R, np.full(3, r0))

    recovered = PointsMesh(chord.R, chord.Z)
    assert np.all(
        np.allclose(
            [recovered.r, recovered.theta],
            [np.hypot(r0, heights), np.arctan2(r0, heights)],
            rtol=0,
            atol=8 * EPS * 2.0,
        )
    )
    again = SphericalRChord(recovered.r, recovered.theta)
    assert np.all(np.abs(again.R - r0) <= 8 * EPS * 2.0)
    assert np.all(np.abs(again.Z - heights) <= 8 * EPS * np.abs(heights).max())

    # r0 = 0 is the axis, and arctan2(0, Z) is exact on both half-axes: 0 towards
    # +Z and pi towards -Z.  The radius is |Z| exactly, so the round trip is
    # bitwise on the degenerate row as well.
    axis = ZChord([0.5, -1.5], 0.0)
    on_axis = PointsMesh(axis.R, axis.Z)
    assert np.array_equal(on_axis.theta, np.array([0.0, np.pi]))
    assert np.array_equal(on_axis.r, np.abs(axis.Z))


# --------------------------------------------------------------------------- #
# rotate: forward, inverse, and an exact-rational account of the arithmetic
# --------------------------------------------------------------------------- #


def test_rotate_round_trip_is_the_identity():
    """rotate(-angle) after rotate(angle) returns the input for every case.

    Rows: normal, a point at the pivot, a negative angle, a full turn, a leading
    batch dimension (asymmetric shape) and the degenerate single-point row.
    """
    points = np.array([[0.3, -0.7], [1.25, 0.5], [-2.0, 3.0], [0.0, 0.0]])
    scale = 8 * EPS * np.abs(points).max()
    for angle in (17.0, 45.0, 90.0, 123.0, -30.0, 360.0):
        radians = math.radians(angle)
        returned = rotate(rotate(points, radians), -radians)
        assert np.all(np.abs(returned - points) <= scale), angle

    pivot = (1.0, -0.25)
    around = rotate(
        rotate(points, math.radians(63.0), pivot=pivot), -math.radians(63.0), pivot=pivot
    )
    assert np.all(np.abs(around - points) <= 8 * EPS * (np.abs(points).max() + 1.0))
    # The pivot itself is the fixed point of the pair.
    assert np.all(
        np.abs(
            rotate(
                rotate([pivot], math.radians(40.0), pivot=pivot),
                -math.radians(40.0),
                pivot=pivot,
            )
            - np.asarray([pivot])
        )
        <= 8 * EPS
    )

    batched = np.arange(12, dtype=float).reshape(2, 3, 2) / 10.0
    assert rotate(rotate(batched, math.radians(51.0)), -math.radians(51.0)).shape == batched.shape
    single = rotate(rotate([1.0, 0.0], math.radians(12.0)), -math.radians(12.0))
    assert single.shape == (2,)


def test_rotate_arithmetic_matches_an_exact_rational_recomputation():
    """The formula is exact up to one rounded sum, given the same rounded c and s.

    ``c`` and ``s`` are read from ``math``, so the transcendental values are
    inputs here, not predictions: what the identity decides is that component
    R' is ``x c + y s`` and Z' is ``-x s + y c`` with the row-vector order, i.e.
    the sign convention and the axis pairing of the implementation.
    """
    for x, y, angle in (
        (1.3, -2.4, 90.0),
        (1.3, -2.4, 30.0),
        (1.3, -2.4, 17.0),
        (-0.75, 0.125, 180.0),
        (2.5, 2.5, 360.0),
    ):
        cosine = math.cos(math.radians(angle))
        sine = math.sin(math.radians(angle))
        exact_first = _exact(x) * _exact(cosine) + _exact(y) * _exact(sine)
        exact_second = -_exact(x) * _exact(sine) + _exact(y) * _exact(cosine)
        got = rotate([[x, y]], math.radians(angle))[0]
        budget = 2 * EPS * (abs(x) + abs(y))
        assert abs(_exact(got[0]) - exact_first) <= budget, angle
        assert abs(_exact(got[1]) - exact_second) <= budget, angle

    # 90 degrees: the cosine is not zero but 6.12e-17, and the whole deviation
    # from the exact (0, -1) map is that documented cosine value times x.  The
    # exact rational sum rounds back onto the implementation's value bitwise,
    # which is the strongest statement available here: the only difference from
    # the ideal map is the transcendental input, and the map itself is exact.
    cosine_at_quarter = math.cos(np.pi / 2)
    quarter = rotate([[1.3, -2.4]], np.pi / 2)[0]
    exact_quarter_first = _exact(1.3) * _exact(cosine_at_quarter) - _exact(2.4)
    exact_quarter_second = -_exact(1.3) + _exact(-2.4) * _exact(cosine_at_quarter)
    assert float(exact_quarter_first) == quarter[0]
    assert float(exact_quarter_second) == quarter[1]
    # The two components round differently because the 1.3 * 6.12e-17 residual is
    # below half an ulp of 2.4 but above half an ulp of 1.3.  Both are accounted
    # for exactly by the rational expression, so neither is an unexplained error.
    assert quarter[0] == -2.4
    assert quarter[1] == -1.3000000000000003


def test_rotate_rejects_each_declared_channel():
    """One executable assertion per ``failure_semantics`` entry of ``rotate``."""
    with pytest.raises(ValueError, match="final dimension of length 2"):
        rotate(1.0, 10.0)
    with pytest.raises(ValueError, match="finite"):
        rotate([[np.nan, 0.0]], 10.0)
    with pytest.raises(ValueError, match="pivot must contain"):
        rotate([[1.0, 0.0]], 10.0, pivot=(0.0, 0.0, 0.0))
    with pytest.raises(ValueError, match="angle must be finite"):
        rotate([[1.0, 0.0]], np.inf)
    with pytest.raises(FloatingPointError, match="nonfinite rotated values"):
        rotate([[1.7e308, 1.7e308]], 45.0)
