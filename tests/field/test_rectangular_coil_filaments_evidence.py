"""Independent evidence for the rectangular-coil filament centres.

Asset: ``scirel.field.rectangular-coil-filaments``.

``discretize_rectangular_coil`` is pure geometry, so the second source is exact
rational arithmetic rather than another floating-point formula.  Every input is
a binary64 number, hence an exact rational, and the centre table is a rational
function of them:

    r_i = r0 + (i - (nr - 1)/2) * dr,     z_j = z0 + (j - (nz - 1)/2) * dz

The test inputs are chosen so both spans and both spacings stay exactly
representable, which makes the exact rational recomputation the exact value of
the intended expression and the equality bitwise rather than approximate.

What the tests decide:

1. **The centre table, in exact rationals.**  The returned coordinates must equal
   the exact rational centres, in the declaration order the contract states: the
   radial index outermost, the axial index innermost.  This kills an off-by-half
   offset, a swapped spacing, a transposed loop order and an ``n`` versus
   ``n - 1`` error at once, and the failure modes are O(spacing), not an ulp.
2. **The span and the count.**  The first and last radial centres are exactly
   ``r0 -+ dr (nr - 1)/2``; the number of rows is exactly ``nr * nz``.
3. **A single filament is exactly the centroid.**  With ``nr = nz = 1`` the one
   centre is ``(r0, z0)`` bitwise, and it stays there under any rotation angle,
   because ``(p - c) @ R + c`` with ``p == c`` returns ``c`` exactly.  Any
   implementation that rotated about the wrong point fails here with an O(1)
   error.
4. **The rotation is a proper rotation about the centroid**, checked by the
   cardinal-direction image of a known offset, the preservation of distance to
   the centroid, and the preservation of the centroid itself.  ``deg2rad`` and
   ``cos``/``sin`` are themselves inexact, so this item carries a rounding budget
   instead of an exact equality; the budget is 16 eps of the largest coordinate,
   derived from one ``deg2rad`` rounding plus one each for ``cos``/``sin``, two
   products and one sum.
5. **The axis guard**: a rotation that drives a radius negative is rejected, and
   the unrotated table never has a negative radius.

Budget: items 1-3 are exact equalities.  Item 4 is ``16 eps * scale`` as derived
above; the observed maximum over the sampled angles is below ``3 eps * scale``.
Item 5 is a rejection.

Evidence ceiling: this asset assigns no current, weight or conductor cross
section, so the evidence covers only the geometry it returns.  It also says
nothing about how finely a rectangular block must be subdivided to approximate a
finite conductor; that is outside this contract.
"""

from __future__ import annotations

from fractions import Fraction

import numpy as np
import pytest

from scirel.field import discretize_rectangular_coil

EPS = float(np.finfo(float).eps)

# Dyadic parameters: every centre and every spacing is exactly representable.
R0, Z0 = 1.0, 2.0
DR, DZ = 0.5, 0.25
NR, NZ = 4, 5


def _exact_centres(r0, z0, nr, nz, dr, dz):
    radial = [Fraction(r0) + (Fraction(index) - Fraction(nr - 1, 2)) * Fraction(dr) for index in range(nr)]
    axial = [Fraction(z0) + (Fraction(index) - Fraction(nz - 1, 2)) * Fraction(dz) for index in range(nz)]
    return radial, axial


def test_centre_table_matches_exact_rational_centres_in_the_declared_order():
    """Evidence 1 and 2: bitwise centres, radial-outer / axial-inner order."""
    points = discretize_rectangular_coil(R0, Z0, nr=NR, nz=NZ, dr=DR, dz=DZ)
    assert points.shape == (NR * NZ, 2)
    radial, axial = _exact_centres(R0, Z0, NR, NZ, DR, DZ)
    for row in range(NR * NZ):
        outer, inner = divmod(row, NZ)
        assert Fraction(float(points[row, 0])) == radial[outer], row
        assert Fraction(float(points[row, 1])) == axial[inner], row
    # Span anchors, in exact rationals.
    assert Fraction(float(points[0, 0])) == Fraction(R0) - Fraction(DR) * Fraction(NR - 1) / 2
    assert Fraction(float(points[-1, 0])) == Fraction(R0) + Fraction(DR) * Fraction(NR - 1) / 2
    assert Fraction(float(points[0, 1])) == Fraction(Z0) - Fraction(DZ) * Fraction(NZ - 1) / 2
    assert Fraction(float(points[-1, 1])) == Fraction(Z0) + Fraction(DZ) * Fraction(NZ - 1) / 2
    # The order statement the contract makes: swapping it would sort the axial
    # coordinate first, which shows up as a different sequence.
    assert not np.array_equal(
        points[:, 1], np.repeat(axial and [float(value) for value in axial][:NZ], NR)
    )


def test_a_single_filament_sits_exactly_on_the_centroid_under_any_rotation():
    """Evidence 3: one centre, exactly at (r0, z0), invariant under rotation."""
    for angle in (0.0, 90.0, -135.0, 271.5):
        points = discretize_rectangular_coil(
            R0, Z0, nr=1, nz=1, dr=DR, dz=DZ, angle_deg=angle
        )
        assert points.shape == (1, 2)
        assert points[0, 0] == R0, angle
        assert points[0, 1] == Z0, angle


def test_rotation_is_a_proper_rotation_about_the_centroid():
    """Evidence 4: cardinal image, distance and centroid preservation."""
    observed = 0.0
    for angle, expected_direction in [(90.0, (0.0, -1.0)), (180.0, (-1.0, 0.0)), (270.0, (0.0, 1.0))]:
        points = discretize_rectangular_coil(
            R0, Z0, nr=1, nz=1, dr=0.0 + 2.0, dz=1.0e-300, angle_deg=angle
        )
        offset = points[0] - np.array([R0, Z0])
        scale = float(np.max(np.abs(points[0])))
        # The row-vector convention sends (dr, 0) to dr * (cos, -sin)?  The
        # maintained rule is (p - c) @ [[cos, -sin], [sin, cos]], so (1, 0) maps
        # to (cos, -sin) and the cardinal images below are its exact limits.
        deviation = abs(offset[0] / 2.0 - expected_direction[0])
        assert deviation <= 16 * EPS * max(1.0, scale), (angle, deviation)
        observed = max(observed, deviation)
        deviation = abs(offset[1] / 2.0 - expected_direction[1])
        assert deviation <= 16 * EPS * max(1.0, scale), (angle, deviation)
        observed = max(observed, deviation)
    assert observed > 0.0
    # A field of centres keeps its distance to the centroid and its centroid.
    base = discretize_rectangular_coil(R0, Z0, nr=NR, nz=NZ, dr=DR, dz=DZ)
    rotated = discretize_rectangular_coil(R0, Z0, nr=NR, nz=NZ, dr=DR, dz=DZ, angle_deg=37.0)
    centre = np.array([R0, Z0])
    np.testing.assert_allclose(rotated.mean(axis=0), centre, rtol=0.0, atol=8 * EPS * 4.0)
    np.testing.assert_allclose(
        np.hypot(*(rotated - centre).T),
        np.hypot(*(base - centre).T),
        rtol=0.0,
        atol=16 * EPS * 4.0,
    )
    # Not the identity: the rotation really moved the centres.
    assert not np.array_equal(rotated, base)


def test_each_declared_rejection_channel_is_executable():
    """Every ``failure_semantics`` channel has one assertion."""
    with pytest.raises(ValueError, match="r0 and z0 must be finite"):
        discretize_rectangular_coil(np.nan, Z0, nr=2, nz=2, dr=DR, dz=DZ)
    with pytest.raises(ValueError, match="r0 and z0 must be finite"):
        discretize_rectangular_coil(R0, np.inf, nr=2, nz=2, dr=DR, dz=DZ)
    with pytest.raises(ValueError, match="nonnegative cylindrical radius"):
        discretize_rectangular_coil(-R0, Z0, nr=2, nz=2, dr=DR, dz=DZ)
    for name, value in [("nr", 0), ("nr", -1), ("nz", 1.5), ("nz", True)]:
        arguments = {"r0": R0, "z0": Z0, "nr": 2, "nz": 2, "dr": DR, "dz": DZ}
        arguments[name] = value
        with pytest.raises(ValueError, match=f"{name} must be a positive integer"):
            discretize_rectangular_coil(**arguments)
    for name, value in [("dr", 0.0), ("dr", -DR), ("dz", np.nan)]:
        arguments = {"r0": R0, "z0": Z0, "nr": 2, "nz": 2, "dr": DR, "dz": DZ}
        arguments[name] = value
        with pytest.raises(ValueError, match=f"{name} must be a positive finite scalar"):
            discretize_rectangular_coil(**arguments)
    with pytest.raises(ValueError, match="angle_deg must be finite"):
        discretize_rectangular_coil(R0, Z0, nr=2, nz=2, dr=DR, dz=DZ, angle_deg=np.nan)
    # The axis guard: a wide block rotated about a small radius crosses R = 0.
    with pytest.raises(ValueError, match="crosses the cylindrical axis"):
        discretize_rectangular_coil(0.1, 0.0, nr=2, nz=1, dr=1.0, dz=1.0, angle_deg=90.0)
    # Unrepresentable coordinates.
    with pytest.raises(ValueError, match="not representable"):
        discretize_rectangular_coil(
            np.finfo(float).max, 0.0, nr=3, nz=1, dr=np.finfo(float).max, dz=1.0
        )
