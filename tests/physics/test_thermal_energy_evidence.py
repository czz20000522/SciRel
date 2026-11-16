"""Independent exact-rational evidence for the stored-thermal-energy relation.

The relation is

.. math:: W = \\tfrac{3}{2} \\sum_i p_i \\, vpr_i \\, drho_i ,

computed in exact rational arithmetic on binary64 inputs and rounded once at the
end. This file recomputes that same discrete sum from ``Fraction`` values
constructed directly from the float64 inputs, so it shares no operation with the
implementation: no product, no accumulation order and no rounding step. Every
comparison is exact, not approximate, because both sides are the same rational
number and the implementation states that it round-once.

What this can and cannot show is stated in the contract as well: it establishes
the documented discrete relation, its scaling law and its component independence.
It does not establish a closure between ``p_tot`` and ``p_el``/``p_ion`` — the
function deliberately imposes none — and it says nothing about whether a given
profile is a physically valid pressure.
"""

from __future__ import annotations

from fractions import Fraction

import pytest

from scirel.physics import calculate_stored_thermal_energy

#: A nonuniform three-cell grid: unequal widths and a non-unit volume metric, so a
#: swapped index pair or a dropped weight changes the answer at O(1).
VPR = [2.0, 3.0, 0.5]
DRHO = [0.25, 0.5, 1.5]
P_EL = [1.25, 2.0, -0.75]
P_ION = [0.5, 0.125, 3.0]
P_TOT = [1.75, 2.125, 2.25]


def _exact(pressure, vpr=VPR, drho=DRHO):
    """Recompute ``1.5 * sum(p*v*d)`` as a rational number from the raw inputs."""
    total = Fraction(0)
    for p, v, d in zip(pressure, vpr, drho):
        total += Fraction(p) * Fraction(v) * Fraction(d)
    return Fraction(3, 2) * total


def test_the_documented_sum_is_reproduced_exactly():
    """Every component equals its exact rational value after a single rounding."""
    result = calculate_stored_thermal_energy(P_EL, P_ION, P_TOT, VPR, DRHO)
    expected = tuple(float(_exact(profile)) for profile in (P_EL, P_ION, P_TOT))
    assert result == expected


def test_the_three_halves_factor_is_pinned_by_a_nonunit_case():
    """Dropping the ``3/2`` changes the result by more than one part in ten.

    A relation stated only as "sum of products" would pass the reproduction test
    above if the expected value were derived the same way, so the factor is
    checked against a value this file computes without it.
    """
    (energy_electron, _ions, _total) = calculate_stored_thermal_energy(
        P_EL, P_ION, P_TOT, VPR, DRHO
    )
    without_factor = float(_exact(P_EL) / Fraction(3, 2))
    assert energy_electron != pytest.approx(without_factor, rel=1e-3)
    assert energy_electron == pytest.approx(1.5 * without_factor, rel=0.0)


@pytest.mark.parametrize("pressure_scale,volume_scale", [(2.0, 4.0), (0.5, 0.25), (-1.0, 2.0)])
def test_the_relation_is_exactly_equidimensional(pressure_scale, volume_scale):
    """``W`` scales as pressure times volume, and the scales are exact powers of two.

    Both scales are dyadic, so the scaled product is exactly representable: a
    wrong exponent, a missing weight or a weight applied twice breaks the ratio
    exactly rather than within a tolerance.
    """
    base = calculate_stored_thermal_energy(P_EL, P_ION, P_TOT, VPR, DRHO)
    scaled = calculate_stored_thermal_energy(
        [pressure_scale * p for p in P_EL],
        [pressure_scale * p for p in P_ION],
        [pressure_scale * p for p in P_TOT],
        [volume_scale * v for v in VPR],
        DRHO,
    )
    for before, after in zip(base, scaled):
        assert after == before * pressure_scale * volume_scale


def test_the_components_are_independent_and_cancel_exactly():
    """``p_tot`` is not tied to the other two profiles, and signed cancellation is exact.

    Two profiles whose weighted sum is zero must give exactly zero, not a small
    residual: the sum is rational, so the result is the exact value rather than a
    floating-point accumulation with a drift. The grid weights here are
    ``[0.5, 1.5, 0.75]``, so ``[3, -1, 0]`` cancels exactly while a swapped weight
    pair would not.
    """
    cancel = [3.0, -1.0, 0.0]
    _, _, zero = calculate_stored_thermal_energy(cancel, cancel, cancel, VPR, DRHO)
    assert zero == 0.0

    # An unrelated total profile does not disturb the component results.
    first = calculate_stored_thermal_energy(P_EL, P_ION, P_TOT, VPR, DRHO)
    second = calculate_stored_thermal_energy(P_EL, P_ION, [0.0, 0.0, 0.0], VPR, DRHO)
    assert first[:2] == second[:2]


def test_a_unit_volume_and_unit_width_reduce_to_the_bare_pressure_sum():
    """With ``vpr = drho = 1`` the relation collapses to ``1.5 * sum(p)`` exactly.

    This is the degenerate case: the weights stop discriminating between the
    index conventions, so it isolates the factor and the summation from the
    weighting.
    """
    pressure = [1.0, 2.0, 4.0]
    ones = [1.0, 1.0, 1.0]
    (energy, _, _) = calculate_stored_thermal_energy(pressure, pressure, pressure, ones, ones)
    assert energy == float(Fraction(3, 2) * Fraction(sum(Fraction(p) for p in pressure)))
    assert energy == 10.5
