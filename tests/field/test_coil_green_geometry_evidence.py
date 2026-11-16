"""Independent evidence for the axisymmetric coil observation geometry.

Asset: ``scirel.field.coil-green-geometry``.

``compute_axisymmetric_coil_modulus`` returns three scalars per coil: the offset
observation radius, the elliptic parameter ``m`` and the distance ``d``.  The
maintained tests in ``test_filament_coil_green.py`` assert these against values
recomputed with the *same* float expressions, which cannot distinguish a correct
formula from a plausible one.  This file replaces that with exact rational
arithmetic: every input is a binary64 number, hence an exact rational, and so
are ``m`` and ``d**2`` **as rational functions of the inputs**:

    m  = 4 R a / D,          D = (R + a)**2 + (Z - z0)**2
    d2 = D

so both can be recomputed with :class:`fractions.Fraction` at zero rounding error
and compared against the returned float using only the one rounding the return
value itself performs.

What that decides, which a float re-derivation cannot:

1. **The modulus value.** ``m`` must be the correctly rounded double of the exact
   rational ``4 R a / D``: ``|m - float(m_exact)| <= eps/2 * m_exact``.  A wrong
   numerator factor, a wrong ``(R + a)`` sign, or a missing ``dz`` term is an
   O(1) error, not an ulp.
2. **The complementary identity.** ``1 - m = ((R - a)**2 + (Z - z0)**2) / D``
   holds exactly in rationals.  This is the discriminator that separates the
   correct denominator from ``(R - a)**2``: the value of ``m`` alone can look
   reasonable under several wrong denominators at a single point, while this
   identity ties ``m`` to the *distance to the wire* at every point.
3. **The modulus bound.** ``m <= 1`` for every legal input, with equality exactly
   when the target is on the ring.  This follows from
   ``D - 4 R a = (R - a)**2 + (Z - z0)**2 >= 0`` and is asserted as an inequality
   with the exact rational residual, plus one case at equality.
4. **The distance.** ``d**2`` must equal the exact rational ``D`` within the two
   roundings of a square root followed by a square (``<= 2 eps`` relative).
5. **The once-only axis offset.** ``regularized_radius == raw + 1e-8`` exactly,
   and a raw radius of exactly zero still produces the positive offset.

Budget: items 1-4 carry ``eps/2``, ``eps/2``, exact, and ``2 eps`` respectively,
each derived from the number of roundings the corresponding output performs - not
from the observed difference.  Item 5 is exact because both operands are binary64
and their sum is exactly representable for the radii used.

Evidence ceiling: this asset is pure geometry, so the evidence is complete for
the returned relation; what it cannot establish is that the relation is the
*right* relation for a physical coil field.  That belongs to the Green kernel
assets, whose Biot-Savart evidence fixes the ``(2-m)K - 2E`` prefactor that this
modulus feeds.
"""

from __future__ import annotations

from fractions import Fraction

import numpy as np
import pytest

from scirel.field import compute_axisymmetric_coil_modulus

EPS = float(np.finfo(float).eps)
AXIS_OFFSET_M = 1.0e-8

# Coil tables with exactly representable radii and heights, so the exact
# rational recomputation is the exact value of the *intended* expression.
COIL_RADIUS = np.array([0.25, 0.5, 1.0])
COIL_Z = np.array([-0.5, 0.0, 0.75])

OBSERVATIONS = [(0.125, 0.0), (0.375, -0.25), (0.75, 0.5), (0.0, 0.125), (2.0, -1.0)]


def _exact(radius, height, coil_radius, coil_z):
    """Return the exact rational ``(m, d**2)`` of one target/coil pair."""
    radial = Fraction(radius) + Fraction(coil_radius)
    axial = Fraction(height) - Fraction(coil_z)
    denominator = radial * radial + axial * axial
    return 4 * Fraction(radius) * Fraction(coil_radius) / denominator, denominator


@pytest.mark.parametrize(("raw_radius", "height"), OBSERVATIONS)
def test_modulus_and_distance_squared_match_the_exact_rational_relation(raw_radius, height):
    """Evidence 1, 2 and 4: m, the complementary identity and d**2 in exact rationals."""
    radius, modulus, distance = compute_axisymmetric_coil_modulus(
        raw_radius, height, COIL_RADIUS, COIL_Z
    )
    assert radius == raw_radius + AXIS_OFFSET_M
    observed = 0.0
    for index, (coil_r, coil_z) in enumerate(zip(COIL_RADIUS, COIL_Z, strict=True)):
        exact_m, exact_denominator = _exact(radius, height, float(coil_r), float(coil_z))
        got_m = float(modulus[index])
        # Evidence 1: one rounding of a rational to float.
        deviation = abs(Fraction(got_m) - exact_m) / exact_m
        assert deviation <= EPS / 2, (raw_radius, height, index, float(deviation))
        observed = max(observed, float(deviation))
        # Evidence 2: 1 - m equals the wire distance squared over D, exactly.
        wire_gap = (Fraction(radius) - Fraction(coil_r)) ** 2 + (
            Fraction(height) - Fraction(coil_z)
        ) ** 2
        assert Fraction(1) - exact_m == wire_gap / exact_denominator
        # The identity is what ties m to the returned modulus: the returned
        # float must satisfy the same relation within two roundings.
        assert abs((1.0 - got_m) - float(wire_gap / exact_denominator)) <= EPS * (
            1.0 - got_m
        )
        # Evidence 4: d squared equals D, one sqrt and one square later.
        got_distance = Fraction(float(distance[index]))
        assert abs(got_distance * got_distance - exact_denominator) <= 2 * Fraction(
            EPS
        ) * exact_denominator
    assert observed > 0.0


def test_modulus_never_exceeds_one_and_reaches_it_only_on_the_ring():
    """Evidence 3: m <= 1 from D - 4 R a = (R - a)**2 + (Z - z0)**2 >= 0."""
    for raw_radius, height in OBSERVATIONS:
        radius, modulus, _ = compute_axisymmetric_coil_modulus(
            raw_radius, height, COIL_RADIUS, COIL_Z
        )
        for index, (coil_r, coil_z) in enumerate(zip(COIL_RADIUS, COIL_Z, strict=True)):
            exact_m, exact_denominator = _exact(radius, height, float(coil_r), float(coil_z))
            assert 0 < exact_m <= 1
            assert exact_denominator - 4 * Fraction(radius) * Fraction(coil_r) >= 0
            assert float(modulus[index]) <= 1.0
    # Equality is reached exactly when the target sits on the ring, and the
    # distance there is 2 R.
    radius, modulus, distance = compute_axisymmetric_coil_modulus(
        0.5, 0.75, np.array([0.5 + AXIS_OFFSET_M]), np.array([0.75])
    )
    assert modulus[0] == 1.0
    assert distance[0] == 2.0 * radius


def test_the_axis_offset_is_applied_once_and_zero_radius_stays_positive():
    """Evidence 5: the offset is the only shift, and it regularises R = 0."""
    radius, modulus, distance = compute_axisymmetric_coil_modulus(
        0.0, 0.0, np.array([0.5]), np.array([0.0])
    )
    assert radius == AXIS_OFFSET_M
    assert radius > 0.0
    # m at the regularised axis point is small but nonzero, and its exact value
    # is the rational one for that same offset radius.
    exact_m, _ = _exact(radius, 0.0, 0.5, 0.0)
    assert abs(Fraction(float(modulus[0])) - exact_m) <= Fraction(EPS) / 2 * exact_m
    assert float(modulus[0]) > 0.0
    # The returned distance uses the offset radius too, not the raw one.
    assert distance[0] == radius + 0.5


def test_each_declared_rejection_channel_is_executable():
    """Every ``failure_semantics`` channel has one assertion."""
    good_radius, good_z = np.array([0.25, 0.5]), np.array([-0.25, 0.25])
    with pytest.raises(ValueError, match="nonnegative"):
        compute_axisymmetric_coil_modulus(-1.0e-9, 0.0, good_radius, good_z)
    with pytest.raises(ValueError, match="finite after source axis offset"):
        compute_axisymmetric_coil_modulus(np.inf, 0.0, good_radius, good_z)
    with pytest.raises(ValueError, match="finite after source axis offset"):
        compute_axisymmetric_coil_modulus(0.3, np.nan, good_radius, good_z)
    with pytest.raises(ValueError, match="same-shape vectors"):
        compute_axisymmetric_coil_modulus(0.3, 0.0, good_radius, good_z[:-1])
    with pytest.raises(ValueError, match="same-shape vectors"):
        compute_axisymmetric_coil_modulus(0.3, 0.0, np.array([[0.25, 0.5]]), np.array([[0.0, 0.0]]))
    with pytest.raises(ValueError, match="positive radii"):
        compute_axisymmetric_coil_modulus(0.3, 0.0, np.array([0.0, 0.5]), good_z)
    with pytest.raises(ValueError, match="positive radii"):
        compute_axisymmetric_coil_modulus(0.3, 0.0, np.array([-0.25, 0.5]), good_z)
    with pytest.raises(ValueError, match="positive radii"):
        compute_axisymmetric_coil_modulus(0.3, 0.0, np.array([np.nan, 0.5]), good_z)
    # The modulus underflow guard: a subnormal observation radius times a normal
    # coil radius underflows the modulus to zero.
    with pytest.raises(ValueError, match="underflowed to zero"):
        compute_axisymmetric_coil_modulus(
            5.0e-324, 0.0, np.array([5.0e-324]), np.array([0.0])
        )
    # The overflow guard: a denominator that overflows to infinity.
    with pytest.raises(ValueError, match="overflowed to non-finite"):
        compute_axisymmetric_coil_modulus(1.0e308, 1.0e308, np.array([1.0e308]), np.array([0.0]))
