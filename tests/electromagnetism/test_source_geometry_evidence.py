"""Independent evidence for the parameterized filament source geometries.

Assets: ``scirel.electromagnetism.arbitrary-points``,
``scirel.electromagnetism.rectangular-coil`` and
``scirel.electromagnetism.magnet-ring``.

The maintained tests pin the geometry and lifecycle behaviour of these classes;
none of them compares a geometry against a source outside the implementation,
and the field methods are the shared Green kernel wrapped.  The evidence here
therefore has two kinds of second source, chosen per statement:

* **Exact geometry laws.**  A rectangular coil is the product of two arithmetic
  sequences placed in a declared order, symmetric about its centroid, with an
  area that is the exact product of its parameters; a magnet ring is two
  columns at ``r0 -+ width/2`` with an arithmetic axial sequence; an arbitrary
  point source is the caller's own table.  These are decided with
  ``fractions.Fraction`` over the returned binary64 values and with bitwise
  equality where the arithmetic is exact, so an implementation that echoes its
  input, returns zero, or uses a wrong spacing cannot pass them.
* **The elementary on-axis loop field.**  For a ring, ``B_Z`` on the axis is
  ``1e-7 w 2 pi a^2 / (a^2 + dz^2)^{3/2}`` per filament - a closed form with no
  elliptic integral at all - so the summed on-axis field of a whole ring is an
  independent value for the geometry the ring actually built.
* **The 40-digit reference.**  For the small sources (three arbitrary points,
  a 2 x 2 coil) the full ``(psi, B_R, B_Z)`` is compared against
  ``_ideal_ring_reference.superpose``.

Deliberate limits, recorded in the contracts: the large fixed configurations
(88- and 904-filament) are not recomputed filament by filament at 40 digits;
their values rest on the per-filament kernel evidence plus the exact
composition identity, and their geometry is checked by exact symmetry and
spacing laws instead.
"""

from __future__ import annotations

from fractions import Fraction

import numpy as np
import pytest

import _ideal_ring_reference as reference
from scirel.electromagnetism import ArbitraryPoints, MagnetRing, RectangularCoil

PSI_BUDGET = reference.PSI_BUDGET
FIELD_BUDGET = reference.FIELD_BUDGET
FIELDS = ("psi", "BR", "BZ")
TARGETS = np.array([[0.3, 0.15], [0.75, -0.4], [1.6, 0.55]])


def _fraction_close(value, expected, count=2, eps=Fraction(2, 2**52)):
    """Assert ``value`` equals ``expected`` within ``count`` roundings."""
    got, want = Fraction(float(value)), Fraction(float(expected))
    scale = abs(want) if want != 0 else Fraction(1)
    return abs(got - want) <= count * eps * scale


# --------------------------------------------------------------------- points
def test_arbitrary_points_are_the_callers_table_and_match_the_reference():
    """Points assets: identity of the table, and values from the second source."""
    table = np.array([[0.42, 0.0], [0.95, 0.3], [1.6, -0.25]])
    source = ArbitraryPoints(table, current=2.5, mesh=TARGETS)
    np.testing.assert_array_equal(source.rz_pts, table)
    assert source.npts == 3
    observed = []
    for index, (radius, height) in enumerate(TARGETS):
        expected = reference.superpose([(row[0], row[1], 2.5) for row in table], radius, height)
        for slot, got in enumerate((source.psi(), source.BR(), source.BZ())):
            want = float(expected[slot])
            if want == 0.0:
                assert float(got[index]) == 0.0
                continue
            deviation = abs(float(got[index]) - want) / abs(want)
            assert deviation <= (PSI_BUDGET if slot == 0 else FIELD_BUDGET), (
                FIELDS[slot],
                index,
                deviation,
            )
            observed.append(deviation)
    assert observed


def test_total_current_laws_are_exact():
    """The current/weight bookkeeping is decided with exact arithmetic."""
    weights = np.array([1.0, 2.0, -0.5, 4.0])
    source = ArbitraryPoints(
        [[0.4, 0.0], [0.7, 0.1], [1.1, -0.2], [1.9, 0.35]], current=3.0, weights=weights
    )
    exact = Fraction(3.0) * sum((Fraction(float(w)) for w in weights), Fraction(0))
    assert _fraction_close(source.total_current, exact, count=2)
    source.total_current = 10.0
    # Setting the total rescales the common current by the exact weight sum.
    assert _fraction_close(source.current, Fraction(10.0) / Fraction(float(weights.sum())), count=2)
    assert _fraction_close(source.total_current, 10.0, count=2)
    # A power-of-two current makes every product exact.
    source.current = 8.0
    assert _fraction_close(source.total_current, exact * 8 / 3, count=2)
    with pytest.raises(ValueError, match="weight sum is zero"):
        ArbitraryPoints([[0.4, 0.0], [0.7, 0.1]], weights=[1.0, -1.0]).total_current = 5.0


def test_translation_and_rotation_laws():
    """Rigid transforms are exact on the table and consistent in the field."""
    table = np.array([[0.5, 0.1], [1.2, -0.3]])
    source = ArbitraryPoints(table, mesh=TARGETS)
    original = np.array([source.psi(), source.BR(), source.BZ()])
    # Only an axial translation is a symmetry of this configuration: the kernel
    # depends on the signed height difference z - z0, while the radial
    # coordinate is measured from a fixed axis and a radial shift therefore
    # describes a different set of rings.  All three components must be
    # invariant under the axial shift.
    for delta in (np.array([0.0, -0.6]), np.array([0.0, 1.35])):
        moved_source = ArbitraryPoints(table + delta, mesh=TARGETS + delta)
        moved = np.array([moved_source.psi(), moved_source.BR(), moved_source.BZ()])
        for slot, name in enumerate(FIELDS):
            deviation = np.max(np.abs(moved[slot] - original[slot])) / np.max(
                np.abs(original[slot])
            )
            assert deviation <= 2 * FIELD_BUDGET, (name, deviation)
    # A radial shift is not claimed as a symmetry; the reported table is the
    # only exact statement, and the response must change.
    shifted_radially = ArbitraryPoints(table + [0.35, 0.0], mesh=TARGETS + [0.35, 0.0])
    assert not np.allclose(
        np.array([shifted_radially.BZ()]), np.array([original[2]]), rtol=1e-10, atol=0.0
    )
    delta = np.array([0.35, -0.6])
    source.translate(delta)
    np.testing.assert_array_equal(source.rz_pts, table + delta)
    # A rotation about the centroid is a rigid motion: the centroid stays put
    # and every distance to it is preserved.  The pivot is passed explicitly,
    # because the default pivot is the origin and a rotation about the origin
    # moves the centroid as well.
    coil = RectangularCoil(0.8, 0.2, nr=2, nz=3, dr=0.1, dz=0.06)
    pivot = coil.centroid.copy()
    before = np.linalg.norm(coil.rz_pts - pivot, axis=1)
    coil.rotate(np.deg2rad(37.0), pivot=pivot)
    after = np.linalg.norm(coil.rz_pts - coil.centroid, axis=1)
    np.testing.assert_allclose(after, before, rtol=4 * 2**-52, atol=0.0)
    np.testing.assert_allclose(coil.centroid, pivot, rtol=0.0, atol=1e-15)
    # A rotation about the origin does move the centroid, and the table follows
    # the same rotation.
    moved = RectangularCoil(0.8, 0.2, nr=2, nz=3, dr=0.1, dz=0.06)
    original_points = moved.rz_pts.copy()
    moved.rotate(np.deg2rad(30.0))
    assert not np.allclose(moved.centroid, pivot)
    np.testing.assert_allclose(
        np.linalg.norm(moved.rz_pts, axis=1),
        np.linalg.norm(original_points, axis=1),
        rtol=4 * 2**-52,
        atol=0.0,
    )


def test_arbitrary_points_failure_channels():
    """Failure matrix: the declared rejections of the point source."""
    with pytest.raises(ValueError, match=r"rz_pts must have shape \(N, 2\)"):
        ArbitraryPoints([[0.4, 0.1, 0.2]])
    with pytest.raises(ValueError, match="non-negative radius"):
        ArbitraryPoints([[-0.4, 0.1]])
    with pytest.raises(ValueError, match="must be finite"):
        ArbitraryPoints([[np.nan, 0.1]])
    with pytest.raises(ValueError, match="weights must be a finite vector matching npts"):
        ArbitraryPoints([[0.4, 0.1], [0.5, 0.2]], weights=[1.0])
    with pytest.raises(ValueError, match="current must be a finite scalar"):
        ArbitraryPoints([[0.4, 0.1]], current=np.inf)
    with pytest.raises(ValueError, match="a mesh is required for field evaluation"):
        ArbitraryPoints([[0.4, 0.1]]).psi()
    with pytest.raises(NotImplementedError, match="simplify is not supported"):
        ArbitraryPoints([[0.4, 0.1]]).simplify()
    with pytest.raises(TypeError):
        ArbitraryPoints([[0.4, 0.1]], misspelt=1.0)


# --------------------------------------------------------------- rectangular
def test_rectangular_coil_layout_is_the_declared_product_sequence():
    """The ordered product of two arithmetic sequences, decided exactly."""
    r0, z0, nr, nz, dr, dz = 0.55, -0.2, 3, 4, 0.05, 0.02
    coil = RectangularCoil(r0, z0, nr=nr, nz=nz, dr=dr, dz=dz)
    assert coil.npts == nr * nz
    points = coil.rz_pts
    # Radial index outermost, axial index innermost.
    radii = points[:, 0]
    assert np.allclose(radii.reshape(nr, nz).T, radii.reshape(nr, nz).T[0], rtol=0, atol=0)
    # Both sequences have a single spacing, and both are symmetric about the
    # centroid to the last bit.
    # ``linspace`` reproduces the spacing to a few roundings rather than
    # bitwise, so the spacing law carries that bound and not more.
    np.testing.assert_allclose(
        np.diff(np.unique(radii)), np.full(nr - 1, dr), rtol=4 * 2**-52, atol=0.0
    )
    np.testing.assert_allclose(
        np.diff(np.unique(points[:, 1])), np.full(nz - 1, dz), rtol=4 * 2**-52, atol=0.0
    )
    np.testing.assert_array_equal(points[:, 0] + points[::-1, 0], np.full(nr * nz, 2 * r0))
    np.testing.assert_array_equal(points[:, 1] + points[::-1, 1], np.full(nr * nz, 2 * z0))
    np.testing.assert_array_equal(coil.centroid, [r0, z0])
    # Area and current density are exact products of the parameters.
    assert _fraction_close(coil.area, Fraction(nr * nz) * Fraction(dr) * Fraction(dz), count=2)
    coil.current = 12.0
    assert _fraction_close(
        coil.current_density,
        Fraction(12.0) * Fraction(nr * nz) / Fraction(float(coil.area)),
        count=4,
    )


def test_coil_values_match_the_reference_and_zero_rotation_is_exact():
    """The coil's field against the second source, and the angle-zero identity."""
    coil = RectangularCoil(0.6, 0.1, nr=2, nz=2, dr=0.08, dz=0.05, current=1.5, mesh=TARGETS)
    filaments = [(row[0], row[1], 1.5) for row in coil.rz_pts]
    for index, (radius, height) in enumerate(TARGETS):
        expected = reference.superpose(filaments, radius, height)
        for slot, got in enumerate((coil.psi(), coil.BR(), coil.BZ())):
            want = float(expected[slot])
            if want == 0.0:
                assert float(got[index]) == 0.0
                continue
            deviation = abs(float(got[index]) - want) / abs(want)
            assert deviation <= (PSI_BUDGET if slot == 0 else FIELD_BUDGET), (
                FIELDS[slot],
                index,
                deviation,
            )
    # angle = 0 takes the unrotated branch and must return the bare product.
    plain = RectangularCoil(0.6, 0.1, nr=2, nz=2, dr=0.08, dz=0.05, angle=0.0)
    np.testing.assert_array_equal(plain.rz_pts, coil.rz_pts)


def test_coil_setters_are_atomic_and_counts_are_guarded():
    """A rejected rebuild preserves the previous valid state bitwise."""
    coil = RectangularCoil(0.5, 0.0, nr=2, nz=3, dr=0.1, dz=0.06)
    before = coil.rz_pts.copy()
    with pytest.raises(ValueError, match="geometry dimensions must be positive"):
        coil.dr = -0.1
    np.testing.assert_array_equal(coil.rz_pts, before)
    assert coil.dr == 0.1
    with pytest.raises(ValueError, match="radius must be non-negative"):
        coil.r0 = -1.0
    np.testing.assert_array_equal(coil.rz_pts, before)
    with pytest.raises(ValueError, match="preserve the existing weight cardinality"):
        coil.nr = 3
    np.testing.assert_array_equal(coil.rz_pts, before)
    with pytest.raises(ValueError, match="nr and nz must be positive integers"):
        RectangularCoil(nr=0)
    with pytest.raises(ValueError, match="nr and nz must be positive integers"):
        RectangularCoil(nz=True)


# ----------------------------------------------------------------- ring
def test_magnet_ring_layout_and_on_axis_field():
    """Two columns, an arithmetic axial sequence, and the elementary on-axis form."""
    r0, z0, width, height, half = 0.4, 0.15, 0.02, 0.032, 8
    weights = list(np.r_[np.ones(half), -np.ones(half)])
    ring = MagnetRing(r0, z0, width=width, height=height, weights=weights, current=7.0)
    assert ring.npts == 2 * half
    points = ring.rz_pts
    np.testing.assert_array_equal(points[:half, 0], np.full(half, r0 - width / 2))
    np.testing.assert_array_equal(points[half:, 0], np.full(half, r0 + width / 2))
    # ``linspace`` places each interior node with its own rounding, so two
    # adjacent nodes can differ from the nominal increment by up to two
    # roundings; ``32 eps`` is that allowance for a 16-node span rounded up to a
    # power of two, and it is not a fitted value.
    np.testing.assert_allclose(
        np.diff(points[:half, 1]),
        np.full(half - 1, height / (half - 1)),
        rtol=32 * 2**-52,
        atol=0.0,
    )
    np.testing.assert_array_equal(points[:half, 1], points[half:, 1])
    # The default weight pattern is an exactly balanced pair set.
    assert ring.total_current == 0.0
    # On the axis the response is a sum of elementary loop fields, so the value
    # is decided without any elliptic integral.
    ring_axis = MagnetRing(r0, z0, width=width, height=height, weights=list(np.ones(2 * half)))
    ring_axis.mesh = np.array([[0.0, z0 + 0.25], [0.0, z0 - 0.6]])
    axial = ring_axis.BZ()
    observed = 0.0
    for index, height_query in enumerate([z0 + 0.25, z0 - 0.6]):
        expected = 0.0
        for radius, height_point in ring_axis.rz_pts:
            expected += (
                1e-7
                * 2.0
                * np.pi
                * radius**2
                / (radius**2 + (height_query - height_point) ** 2) ** 1.5
            )
        deviation = abs(float(axial[index]) - expected) / abs(expected)
        assert deviation <= FIELD_BUDGET, (index, float(axial[index]), expected, deviation)
        observed = max(observed, deviation)
    assert observed >= 0.0
    # Rotation of the magnetisation is a rigid motion of the point cloud.
    before = np.linalg.norm(ring.rz_pts - ring.centroid, axis=1)
    ring.mu_hat = np.deg2rad(25.0)
    np.testing.assert_allclose(
        np.linalg.norm(ring.rz_pts - ring.centroid, axis=1), before, rtol=8 * 2**-52, atol=0.0
    )


def test_magnet_ring_failure_channels():
    """Failure matrix: the declared rejections of the ring source."""
    with pytest.raises(ValueError, match="weights must have an even positive length"):
        MagnetRing(0.4, 0.0, weights=[1.0, -1.0, 1.0])
    # A nonfinite or odd-length weight vector is rejected through the ring's
    # single weight-domain message.
    with pytest.raises(ValueError, match="weights must have an even positive length"):
        MagnetRing(0.4, 0.0, weights=[1.0, np.nan])
    with pytest.raises(ValueError, match="weights must have an even positive length"):
        MagnetRing(0.4, 0.0, weights=[])
    with pytest.raises(ValueError, match="invalid magnet geometry"):
        MagnetRing(0.4, 0.0, width=-0.01)
    with pytest.raises(ValueError, match="invalid magnet geometry"):
        MagnetRing(-0.4, 0.0)
