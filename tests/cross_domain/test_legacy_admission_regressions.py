"""Independent counterexamples found while admitting the old scientific leaves."""
from decimal import Decimal, localcontext

import numpy as np
import pytest

from scirel.field.complete_elliptic_integrals_approx import evaluate_complete_elliptic_integrals
from scirel.diagnostics.species_absorption_fraction import compute_species_absorption_fraction
from scirel.kinetic.thermal_speed_scale import compute_thermal_speed_m_s


@pytest.mark.parametrize("m", [1.0, [1.0], [0.5, 1.0], [[1.0, 0.0], [0.2, 1.0]]])
def test_complete_elliptic_endpoint_is_elementwise_mathematical_limit(m):
    # K(1) diverges; E(1)=integral_0^(pi/2) cos(theta) dtheta=1.
    k, e = evaluate_complete_elliptic_integrals(m)
    boundary = np.asarray(m) == 1
    assert np.all(np.isposinf(np.asarray(k)[boundary]))
    np.testing.assert_array_equal(np.asarray(e)[boundary], 1.0)


def test_unrepresentable_signed_percentages_are_rejected():
    # Exact binary64 ledger total is the last tiny term. Each first share
    # exceeds float64 even though the total is finite and nonzero.
    with pytest.raises(ValueError, match="percent"):
        compute_species_absorption_fraction([1e308, -1e308, 0.0, 1e-308])


@pytest.mark.parametrize("temperature,mass", [(1e-308, 1e-308), (5e-324, 1e308), (1e308, 1e308), (1e-300, 1e-310)])
def test_thermal_speed_does_not_lose_representable_result_to_intermediate_range(temperature, mass):
    # Decimal consumes the exact supplied binary64 values and computes the
    # defining square root independently of the implementation operation order.
    with localcontext() as ctx:
        ctx.prec = 100
        expected = float((Decimal(2) * Decimal.from_float(1.602177e-19)
                          * Decimal.from_float(temperature)
                          / (Decimal.from_float(mass) * Decimal.from_float(1.6726231e-27))).sqrt())
    actual = compute_thermal_speed_m_s(temperature, mass)["thermal_speed_m_s"]
    assert abs(actual - expected) <= 2 * abs(np.spacing(expected))


def test_true_final_thermal_speed_overflow_remains_rejected():
    with pytest.raises(ValueError, match="thermal speed"):
        compute_thermal_speed_m_s(1e308, 5e-324)


def test_signed_ledger_sum_keeps_small_terms_between_large_cancellation():
    result = compute_species_absorption_fraction([1e16, 1.0, -1e16, 1.0])
    assert result['total_power'] == 2.0
    np.testing.assert_array_equal(result['species_fraction_percent'], [5e17, 50.0, -5e17, 50.0])


def test_exact_zero_is_detected_before_intermediate_sum_overflow():
    with pytest.raises(ValueError, match='zero total_power'):
        compute_species_absorption_fraction([1e308, 1e308, -1e308, -1e308])


def test_exact_signed_sum_survives_intermediate_overflow():
    result = compute_species_absorption_fraction([1e308, 1e308, -1e308, 1.0])
    assert result['total_power'] == 1e308
    np.testing.assert_array_equal(result['species_fraction_percent'], [100.0, 100.0, -100.0, 1e-306])


def test_subnormal_share_survives_divide_then_scale_underflow():
    result = compute_species_absorption_fraction([5e-324, 100.0, 0.0, 0.0])
    assert result['species_fraction_percent'][0] == 5e-324


def test_numeric_object_ledger_is_a_valid_real_input():
    result = compute_species_absorption_fraction(np.array([1.0, 2, 3.0, 4], dtype=object))
    np.testing.assert_array_equal(result['species_fraction_percent'], [10.0, 20.0, 30.0, 40.0])
