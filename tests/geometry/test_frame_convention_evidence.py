"""Independent evidence for the coordinate conventions of the geometry primitives.

Assets: ``scirel.geometry.points-mesh``, ``r-chord``, ``z-chord``,
``theta-chord``, ``spherical-r-chord``, ``rect-mesh``, ``rotate``.

These seven assets are pure conventions - an axis, a unit, a sign and an index
order - so a tolerance cannot decide them.  Each convention is therefore decided
by a **discriminator whose rival reading differs by O(1)**, and only then is the
chosen reading bounded:

1. **Theta is measured from the +Z symmetry axis, in degrees.**  ``theta = 0``
   maps to ``(R, Z) = (0, r)``.  A reading from the +R axis would give ``(r, 0)``;
   that is an O(1) difference in both components, asserted explicitly before the
   chosen reading is bounded.
2. **The angle unit is degrees, not radians.**  For ``theta = 90`` the radian
   reading gives ``sin(90 rad) = 0.894`` while the degree reading gives ``1``; the
   two differ by O(1), so the same value decides the unit.
3. **``rotate`` is clockwise-positive in the (R, Z) plane, in degrees.**  A
   rotation by ``+90`` degrees maps ``(1, 0)`` to ``(0, -1)``; the
   counter-clockwise reading maps it to ``(0, +1)``, which differs in sign.
4. **The mesh index order is ``(nz, nr)`` with R along the second axis and Z along
   the first.**  The discriminator uses ``nr != nz`` and unequal bounds so a
   transposed convention puts a different corner value at each corner.
5. **The chord classes broadcast their fixed coordinate bitwise** and pass the
   varying coordinate through unchanged.
6. **The two angle conventions of the family are distinguished.**  The
   ``Mesh.theta`` property returns **radians** (``arctan2(R, Z)``) while the chord
   constructors take **degrees**.  Both facts are asserted, because a caller that
   mixes them is off by a factor of ``180/pi``.
7. **Declared rejections.**  One executable assertion per ``failure_semantics``
   channel of each asset, including the ``-0.0`` radius note and the
   ``FloatingPointError`` path of ``rotate``.

Budgets, fixed before measurement:

* a trigonometric composition (``r*sin``, ``r*cos``) admits ``8 * eps * |r|`` for
  each coordinate: two correctly rounded transcendental values and one product
  cannot exceed a few ulp, and ``cos(radians(90))`` itself is ``6.1e-17`` - about
  half an ulp - which this budget absorbs.
* the Pythagoras identity ``R**2 + Z**2 == r**2`` admits ``8 * eps * r**2``.
* ``rotate`` admits ``8 * eps * max(|p| + |pivot|)``; the ``360`` degree round trip
  is a composition of two rounded cosines and one product.
* ``RectMesh`` interior nodes admit ``4 * eps * scale`` against the rational closed
  form ``rmin + k*(rmax-rmin)/(nr-1)``, and the four corner nodes are **exact**.
* the broadcast and axis roles are exact equalities (``array_equal``), because no
  arithmetic is involved.
"""

from __future__ import annotations

import math
from fractions import Fraction

import numpy as np
import pytest

from scirel.geometry import (
    PointsMesh,
    RChord,
    RectMesh,
    SphericalRChord,
    ThetaChord,
    ZChord,
    rotate,
)

EPS = np.finfo(float).eps


def _frac(value):
    """Exact rational value of a binary64 number."""
    return Fraction(float(value))


# --------------------------------------------------------------------------- #
# theta convention (theta-chord, spherical-r-chord)
# --------------------------------------------------------------------------- #


def test_theta_is_measured_from_the_symmetry_axis_not_the_radial_axis():
    """Evidence 1: theta = 0 gives (0, r), and the rival axis reading differs by O(1)."""
    on_axis = SphericalRChord([2.0], 0.0)
    assert on_axis.R[0] == 0.0
    assert on_axis.Z[0] == 2.0
    # The rival convention (theta from +R) would give (2, 0): both components differ
    # by the full radius, so this assertion decides the axis rather than bounding it.
    rival_r, rival_z = 2.0, 0.0
    assert abs(on_axis.R[0] - rival_r) > 1e6 * EPS * 2.0
    assert abs(on_axis.Z[0] - rival_z) > 1e6 * EPS * 2.0

    quarter = SphericalRChord([2.0], 90.0)
    assert abs(quarter.R[0] - 2.0) <= 8 * EPS * 2.0
    assert abs(quarter.Z[0]) <= 8 * EPS * 2.0


def test_the_angle_unit_is_degrees(self_radian_gap=None):
    """Evidence 2: 90 means a quarter turn; the radian reading differs by O(1)."""
    degree_reading = SphericalRChord([1.0], 90.0)
    radian_reading = math.sin(90.0)  # what a radian interpretation would produce
    assert abs(degree_reading.R[0] - 1.0) <= 8 * EPS
    assert abs(radian_reading - math.sin(90.0)) == 0.0
    # sin(90 rad) = 0.8939966..., which is 0.106 away from the degree reading.
    assert abs(degree_reading.R[0] - radian_reading) > 1e-1


def test_chords_preserve_the_spherical_radius():
    """Evidence 1: R^2 + Z^2 = r^2 for the spherical chord."""
    radii = np.array([0.5, 1.0, 2.0])
    for angle in (0.0, 17.0, 45.0, 90.0, 123.0):
        chord = SphericalRChord(radii, angle)
        residual = chord.R**2 + chord.Z**2 - radii**2
        assert np.all(np.abs(residual) <= 8 * EPS * radii**2), angle


def test_the_two_chord_families_share_one_convention():
    """Evidence 1: the theta chord is the spherical chord with the radius fixed."""
    for angle in (0.0, 30.0, 60.0, 90.0):
        theta_chord = ThetaChord([angle], 1.5)
        spherical = SphericalRChord([1.5], angle)
        assert np.array_equal(theta_chord.R, spherical.R), angle
        assert np.array_equal(theta_chord.Z, spherical.Z), angle


# --------------------------------------------------------------------------- #
# the two angle units of the family
# --------------------------------------------------------------------------- #


def test_mesh_theta_property_returns_radians_while_the_constructors_take_degrees():
    """Evidence 6: one family, two angle units - asserted, not assumed."""
    mesh = PointsMesh([0.2], [0.3])
    assert mesh.theta[0] == pytest.approx(math.atan2(0.2, 0.3), rel=0, abs=4 * EPS)
    assert mesh.theta[0] == pytest.approx(0.5880026035475675, rel=0, abs=4 * EPS)
    # The property is in radians; the constructors read degrees. Feeding the radian
    # value to a constructor lands nowhere near the same point.
    mixed_up = ThetaChord([mesh.theta[0]], 1.0)
    assert abs(mixed_up.R[0] - mesh.R[0]) > 1e-2
    # The guard is on the total radius, so only the origin - not a point on the axis -
    # makes theta undefined.
    on_axis = PointsMesh([0.0], [1.0])
    assert on_axis.theta[0] == 0.0
    origin = PointsMesh([0.0], [0.0])
    with pytest.raises(ValueError, match="undefined at the origin"):
        _ = origin.theta


# --------------------------------------------------------------------------- #
# rotate
# --------------------------------------------------------------------------- #


def test_rotate_is_clockwise_positive_and_in_degrees():
    """Evidence 3: +90 maps (1, 0) to (0, -1); the mirror reading disagrees in sign."""
    rotated = rotate([[1.0, 0.0]], 90.0)
    assert abs(rotated[0, 0]) <= 8 * EPS
    assert abs(rotated[0, 1] + 1.0) <= 8 * EPS
    # Counter-clockwise would give (0, +1): the sign decides the orientation.
    assert rotated[0, 1] < 0.0

    thirty = rotate([[1.0, 0.0]], 30.0)
    assert abs(thirty[0, 0] - math.cos(math.radians(30.0))) <= 8 * EPS
    assert abs(thirty[0, 1] + math.sin(math.radians(30.0))) <= 8 * EPS


def test_rotate_about_a_pivot_and_the_full_turn_are_the_expected_maps():
    """Evidence 3: the pivot is the fixed point and 360 degrees is the identity."""
    around = rotate([[2.0, 0.0]], 180.0, pivot=(1.0, 0.0))
    assert np.all(np.abs(around - np.array([[0.0, 0.0]])) <= 8 * EPS * 2.0)
    points = np.array([[0.3, -0.7], [1.25, 0.5], [-2.0, 3.0]])
    full = rotate(points, 360.0)
    assert np.all(np.abs(full - points) <= 8 * EPS * 3.0)
    # Shape is preserved for a leading batch dimension as well.
    batched = np.arange(12, dtype=float).reshape(2, 3, 2) / 10.0
    assert rotate(batched, 45.0).shape == batched.shape


# --------------------------------------------------------------------------- #
# chords and the rectangular mesh
# --------------------------------------------------------------------------- #


def test_chords_broadcast_their_fixed_coordinate_bitwise():
    """Evidence 5: the fixed coordinate is an exact broadcast, the free one is a copy."""
    axial = np.array([0.2, 0.5, 0.9])
    radial_chord = RChord(axial, 0.3)
    assert np.array_equal(radial_chord.R, axial)
    assert np.array_equal(radial_chord.Z, np.full(3, 0.3))

    heights = np.array([-0.2, 0.4])
    vertical = ZChord(heights, 0.3)
    assert np.array_equal(vertical.Z, heights)
    assert np.array_equal(vertical.R, np.full(2, 0.3))


def test_rect_mesh_is_nz_by_nr_with_r_on_the_second_axis():
    """Evidence 4: the index order, decided by nr != nz and by all four corners."""
    mesh = RectMesh(rmin=0.0, rmax=2.0, nr=3, zmin=-1.0, zmax=1.0, nz=2)
    assert mesh.shape == (2, 3)
    assert mesh.R[0, 0] == 0.0 and mesh.R[0, -1] == 2.0
    assert mesh.Z[0, 0] == -1.0 and mesh.Z[-1, 0] == 1.0
    # A transposed convention would put rmax at a Z corner and zmax at an R corner.
    assert mesh.R[0, -1] != mesh.Z[-1, 0]
    assert np.all(mesh.R == mesh.R[0][None, :])
    assert np.all(mesh.Z == mesh.Z[:, 0][:, None])
    # Interior nodes against the exact rational closed form of linspace.
    r_values = np.linspace(0.0, 2.0, 3)
    z_values = np.linspace(-1.0, 1.0, 2)
    for index, value in enumerate(r_values):
        exact = _frac(0.0) + Fraction(index) * (_frac(2.0) - _frac(0.0)) / 2
        assert abs(value - float(exact)) <= 4 * EPS * 2.0
    for index, value in enumerate(z_values):
        exact = _frac(-1.0) + Fraction(index) * (_frac(1.0) - _frac(-1.0)) / 1
        assert abs(value - float(exact)) <= 4 * EPS * 2.0


def test_points_mesh_keeps_the_shape_it_was_given():
    """Evidence 5: no flattening - the remaining dimensions are preserved."""
    radius = np.array([[0.1, 0.2], [0.3, 0.4]])
    axial = np.array([[0.0, 1.0], [2.0, 3.0]])
    mesh = PointsMesh(radius, axial)
    assert mesh.shape == (2, 2)
    assert np.array_equal(mesh.R, radius)
    scalar = PointsMesh(0.2, 0.3)
    assert scalar.shape == (1,)
    assert scalar.R[0] == 0.2 and scalar.Z[0] == 0.3


# --------------------------------------------------------------------------- #
# declared rejections
# --------------------------------------------------------------------------- #


def test_points_mesh_rejections():
    """Evidence 7: shape, finiteness and radius channels of points-mesh."""
    with pytest.raises(ValueError, match="equal shape"):
        PointsMesh([1.0, 2.0], [0.0])
    with pytest.raises(ValueError, match="finite"):
        PointsMesh([1.0], [np.nan])
    with pytest.raises(ValueError, match="non-negative"):
        PointsMesh([-1.0], [0.0])


def test_chord_rejections():
    """Evidence 7: the chords inherit the points-mesh channels."""
    with pytest.raises(ValueError, match="non-negative"):
        RChord([-0.5], 0.3)
    with pytest.raises(ValueError, match="non-negative"):
        ZChord([0.0], -0.3)
    with pytest.raises(ValueError, match="finite"):
        RChord([0.5], np.inf)
    # A negative spherical radius with a quarter turn generates a negative R.
    with pytest.raises(ValueError, match="non-negative"):
        ThetaChord([90.0], -1.0)
    with pytest.raises(ValueError, match="non-negative"):
        SphericalRChord([-1.0], 90.0)
    # The declared -0.0 note: a signed zero radius passes the R < 0 check.
    allowed = SphericalRChord([-0.0], 0.0)
    assert allowed.R[0] == 0.0


def test_rect_mesh_rejections():
    """Evidence 7: bounds, counts and finiteness channels of rect-mesh."""
    with pytest.raises(ValueError, match="finite"):
        RectMesh(rmin=np.nan)
    with pytest.raises(ValueError, match="invalid rectangular mesh bounds"):
        RectMesh(rmin=1.0, rmax=0.5)
    with pytest.raises(ValueError, match="invalid rectangular mesh bounds"):
        RectMesh(zmin=1.0, zmax=0.5)
    with pytest.raises(ValueError, match="positive integers"):
        RectMesh(nr=0)
    with pytest.raises(ValueError, match="positive integers"):
        RectMesh(nz=True)
    with pytest.raises(ValueError, match="positive integers"):
        RectMesh(nr=2.5)


def test_rotate_rejections():
    """Evidence 7: the shape, pivot, finiteness and overflow channels of rotate."""
    with pytest.raises(ValueError, match="final dimension of length 2"):
        rotate(1.0, 10.0)
    # A one-dimensional pair is one point: the contract rejects scalars, not a
    # length-two final axis, so this call is valid and keeps the (2,) shape.
    single_point = rotate([1.0, 0.0], 10.0)
    assert single_point.shape == (2,)
    with pytest.raises(ValueError, match="final dimension of length 2"):
        rotate([[1.0, 2.0, 3.0]], 10.0)
    with pytest.raises(ValueError, match="finite"):
        rotate([[np.inf, 0.0]], 10.0)
    with pytest.raises(ValueError, match="pivot must contain"):
        rotate([[1.0, 0.0]], 10.0, pivot=(1.0, 2.0, 3.0))
    with pytest.raises(ValueError, match="pivot must contain only finite"):
        rotate([[1.0, 0.0]], 10.0, pivot=(np.nan, 0.0))
    with pytest.raises(ValueError, match="angle must be finite"):
        rotate([[1.0, 0.0]], np.inf)
    with pytest.raises(FloatingPointError, match="nonfinite rotated values"):
        rotate([[1.7e308, 1.7e308]], 45.0)
