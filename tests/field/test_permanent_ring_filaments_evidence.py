"""Independent evidence for the signed permanent-ring discretization.

Asset: ``scirel.field.permanent-ring-filaments``.

``discretize_permanent_ring`` returns 16 filament positions and 16 relative
weights: the first eight on the inner radial surface with weight ``-1`` and the
last eight on the outer surface with ``+1``.  The maintained tests check the
shape, the two radius groups and the weight sign pattern against literals taken
from the same construction.

The evidence here is exact rational and structural, and it is split from what it
cannot cover, because this asset has two different kinds of claim:

**Established here (geometry and the discrete weight law):**

1. **The point table, exactly.**  With a dyadic centroid, width and height, the
   two surface radii are exactly ``r0 -+ width/2`` and are shared by the whole
   group; both groups carry the *same* axial list, bitwise.  The axial nodes are
   checked against the exact rational ``z0 + (k - 7/2) * height / 7``.
2. **The first and last axial node are the exact section edges**, because a
   ``linspace`` endpoint is assigned rather than accumulated.
3. **The axial nodes are symmetric about ``z0``**, which is what makes the two
   groups a *sheet pair* rather than two unrelated rings.
4. **The weight law.**  Weights are exactly ``[-1] * 8 + [1] * 8``; their sum is
   exactly zero; the weighted axial first moment ``sum(w Z)`` is exactly zero
   because both groups share the same axial list; and the weighted radial first
   moment is exactly ``8 * width``.  Those three are the discrete statement of a
   signed magnetisation sheet - a pair of equal and opposite surface currents -
   and they are equalities, not tolerances.  A sign error, a swapped group or an
   off-by-one node count breaks at least one of them.
5. **Rotation about the section centroid** keeps the unweighted centroid, keeps
   every radius nonnegative, and leaves the table untouched at ``0`` degrees.

**Not established here, and reported as such:**

6. The physical claim that these 16 filaments *are* a uniformly magnetised ring,
   i.e. that the discrete sheet converges to the surface-current density
   ``M x n`` and that an eight-node per surface rule is accurate enough for a
   given section.  Settling that needs a magnetisation distribution and a
   convergence study against a reference field or a magnet vendor's section
   drawing, neither of which this repository has.  The contract records this as
   a limitation; no test here asserts it, and none of the exact statements above
   depends on it.

Budget: items 1-5 are exact equalities except the axial-node comparison against
the exact rational, which carries ``8 eps * scale`` (one ``linspace`` step
division, one multiply and one add, doubled for the interval accumulation), and
the centroid-preservation check, which carries ``16 eps * scale`` for the same
reason plus the rotation.

Evidence ceiling: geometry and the weight law only; no magnetic field, no
inductance and no magnetisation model is exercised.
"""

from __future__ import annotations

from fractions import Fraction

import numpy as np
import pytest

from scirel.field import discretize_permanent_ring

EPS = float(np.finfo(float).eps)

# Dyadic section so both surface radii are exactly representable.
R0, Z0, WIDTH, HEIGHT = 2.0, 3.0, 1.0, 2.0
INNER_R, OUTER_R = R0 - WIDTH / 2, R0 + WIDTH / 2
NODES = 8


def _result(**overrides):
    arguments = {"r0": R0, "z0": Z0, "width": WIDTH, "height": HEIGHT}
    arguments.update(overrides)
    return discretize_permanent_ring(**arguments)


def test_point_table_matches_the_exact_section_geometry():
    """Evidence 1 and 2: radii, shared axial list and exact section edges."""
    result = _result()
    points = result["rz_pts"]
    assert points.shape == (2 * NODES, 2)
    np.testing.assert_array_equal(points[:NODES, 0], INNER_R)
    np.testing.assert_array_equal(points[NODES:, 0], OUTER_R)
    # One axial list, used by both groups, so the two surfaces are paired.
    np.testing.assert_array_equal(points[:NODES, 1], points[NODES:, 1])
    axial = points[:NODES, 1]
    assert axial[0] == Z0 - HEIGHT / 2
    assert axial[-1] == Z0 + HEIGHT / 2
    assert np.all(np.diff(axial) > 0.0)
    # Every node equals the exact rational node position within the roundings a
    # linspace performs.
    observed = 0.0
    for index in range(NODES):
        exact = Fraction(Z0) + (Fraction(index) - Fraction(NODES - 1, 2)) * Fraction(
            HEIGHT
        ) / Fraction(NODES - 1)
        deviation = abs(Fraction(float(axial[index])) - exact)
        assert deviation <= 8 * Fraction(EPS) * abs(exact), (index, float(deviation))
        observed = max(observed, float(deviation))
    assert observed > 0.0


def test_axial_nodes_are_symmetric_about_the_section_centroid():
    """Evidence 3: the pair is a sheet pair, symmetric about ``z0``."""
    axial = _result()["rz_pts"][:NODES, 1]
    for index in range(NODES):
        mirrored = axial[NODES - 1 - index]
        assert abs(axial[index] + mirrored - 2.0 * Z0) <= 8 * EPS * abs(Z0), index
    # Not symmetric by accident: a one-sided shift would break at least one pair.
    assert axial[0] != Z0 and axial[-1] != Z0


def test_the_signed_weight_law_and_its_exact_moments():
    """Evidence 4: +/-1 weights, zero total weight and the exact sheet moments."""
    result = _result()
    points, weights = result["rz_pts"], result["default_weights"]
    assert weights.shape == (2 * NODES,)
    np.testing.assert_array_equal(weights, np.r_[-np.ones(NODES), np.ones(NODES)])
    # Zero net weight, exactly.
    total = Fraction(0)
    for value in weights:
        total += Fraction(float(value))
    assert total == 0
    # Zero weighted axial first moment, exactly, because both groups share the
    # same axial list - this is the statement that the two surfaces are a pair.
    axial_moment = sum(
        (Fraction(float(weight)) * Fraction(float(point[1])) for point, weight in zip(points, weights, strict=True)),
        start=Fraction(0),
    )
    assert axial_moment == 0
    # The weighted radial first moment is exactly the group count times the width.
    radial_moment = sum(
        (Fraction(float(weight)) * Fraction(float(point[0])) for point, weight in zip(points, weights, strict=True)),
        start=Fraction(0),
    )
    assert radial_moment == NODES * Fraction(WIDTH)
    # Anchors that a zero-weight result would fail.
    assert np.any(weights < 0.0) and np.any(weights > 0.0)
    assert radial_moment != 0


def test_rotation_keeps_the_section_centroid_and_the_axis_clear():
    """Evidence 5: rotation about the centroid, zero angle is the identity."""
    base = _result()
    unchanged = _result(mu_hat_deg=0.0)
    np.testing.assert_array_equal(unchanged["rz_pts"], base["rz_pts"])
    rotated = _result(mu_hat_deg=30.0)
    centre = np.array([R0, Z0])
    # The unweighted centroid of the 16 nodes is the section centroid, before and
    # after the rotation.
    np.testing.assert_allclose(base["rz_pts"].mean(axis=0), centre, rtol=0.0, atol=8 * EPS * 4.0)
    np.testing.assert_allclose(
        rotated["rz_pts"].mean(axis=0), centre, rtol=0.0, atol=16 * EPS * 4.0
    )
    # Distances to the centroid are preserved, and the rotation really moved the
    # table, so the two assertions above are not satisfied by the identity.
    np.testing.assert_allclose(
        np.hypot(*(rotated["rz_pts"] - centre).T),
        np.hypot(*(base["rz_pts"] - centre).T),
        rtol=0.0,
        atol=16 * EPS * 4.0,
    )
    assert not np.array_equal(rotated["rz_pts"], base["rz_pts"])
    assert np.all(rotated["rz_pts"][:, 0] >= 0.0)
    # The weights are a property of the discretization, not of the rotation.
    np.testing.assert_array_equal(rotated["default_weights"], base["default_weights"])


def test_each_declared_rejection_channel_is_executable():
    """Every ``failure_semantics`` channel has one assertion."""
    with pytest.raises(ValueError, match="ring geometry must be finite"):
        _result(r0=np.nan)
    with pytest.raises(ValueError, match="ring geometry must be finite"):
        _result(width=np.inf)
    with pytest.raises(ValueError, match="ring geometry must be finite"):
        _result(mu_hat_deg=np.nan)
    with pytest.raises(ValueError, match="nonnegative radius and positive dimensions"):
        _result(r0=-R0)
    with pytest.raises(ValueError, match="nonnegative radius and positive dimensions"):
        _result(width=0.0)
    with pytest.raises(ValueError, match="nonnegative radius and positive dimensions"):
        _result(height=-HEIGHT)
    # The axis guard: a tall section rotated 90 degrees crosses R = 0.
    with pytest.raises(ValueError, match="crosses the cylindrical axis"):
        discretize_permanent_ring(0.25, 0.0, 0.5, 4.0, mu_hat_deg=90.0)
    # Unrepresentable coordinates.
    with pytest.raises(ValueError, match="crosses the cylindrical axis or contains nonfinite"):
        discretize_permanent_ring(
            np.finfo(float).max, 0.0, np.finfo(float).max, 1.0
        )
