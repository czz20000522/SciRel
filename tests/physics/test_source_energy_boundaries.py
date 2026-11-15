"""Distinct final rounding policies of dilution and stored thermal energy."""

from fractions import Fraction

import numpy as np
import pytest

from scirel.physics import calculate_main_ion_dilution_factor, calculate_stored_thermal_energy


def test_dilution_positive_half_minimum_rounds_to_zero_separately_from_pure_impurity():
    zi = 2.0**1023
    zimp = 2.0**1022
    zeff = zimp + 2.0**970
    exact = (Fraction(zimp) - Fraction(zeff)) / (Fraction(zi) * (Fraction(zimp) - Fraction(zi)))
    assert exact == Fraction(1, 2**1075)
    assert float(exact) == 0.0  # Round to nearest even, with zero as an allowed result.
    actual = calculate_main_ion_dilution_factor(zi, zimp, zeff)
    assert np.isfinite(actual)
    assert actual == float(exact)
    assert calculate_main_ion_dilution_factor(zi, zimp, zimp) == 0.0


@pytest.mark.parametrize("sign", [1, -1])
def test_thermal_exact_above_maximum_is_rejected_even_when_rounding_would_be_finite(sign):
    p1 = 2.0**1023
    p2 = float((2**54 - 7) // 3) * 2.0**969
    maximum = Fraction(float(np.finfo(np.float64).max))
    exact = Fraction(3, 2) * (Fraction(p1) + Fraction(p2))
    assert exact == maximum + 2**968
    assert float(exact) == float(maximum)
    pressure = [sign * p1, sign * p2]
    with pytest.raises(FloatingPointError):
        calculate_stored_thermal_energy(pressure, pressure, pressure, [1, 1], [1, 1])


@pytest.mark.parametrize("sign", [1, -1])
def test_thermal_finite_neighbor_below_conservative_maximum_is_retained(sign):
    p1 = 2.0**1023
    p2 = float((2**54 - 7) // 3 - 1) * 2.0**969
    maximum = Fraction(float(np.finfo(np.float64).max))
    exact = Fraction(3, 2) * (Fraction(p1) + Fraction(p2))
    assert exact == maximum - 2**969
    pressure = [sign * p1, sign * p2]
    actual = calculate_stored_thermal_energy(pressure, pressure, pressure, [1, 1], [1, 1])
    assert actual == (float(sign * exact),) * 3


def test_thermal_true_zero_is_distinct_from_nonzero_energy_rounding_to_zero():
    assert calculate_stored_thermal_energy([1, -1], [1, -1], [1, -1], [1, 1], [1, 1]) == (
        0.0,
        0.0,
        0.0,
    )
    minimum = 2.0**-1074
    exact = Fraction(3, 2) * Fraction(minimum) * Fraction(1, 4)
    assert exact > 0 and float(exact) == 0.0
    with pytest.raises(FloatingPointError):
        calculate_stored_thermal_energy([minimum], [minimum], [minimum], [0.25], [1])
