import numpy as np
import pytest
from scirel.plasma.fast_ion_heating import fast_ion_fractional_heating


def test_zero_birth_energy_is_finite_continuous_limit():
    assert fast_ion_fractional_heating(0.0, 10.0, 2.0) == 1.0
    np.testing.assert_array_equal(
        fast_ion_fractional_heating(np.array([0.0, 1e-3]), 10.0, 2.0)[0], 1.0
    )


def test_relation_matches_independent_direct_expression_away_from_boundary():
    E, Te, mass = 20.0, 4.0, 2.0
    x2 = E / (10.0 * mass * Te)
    x = np.sqrt(x2)
    expected = 2.0 * ((1 / 6) * np.log((1 - x + x2) / (1 + 2 * x + x2)) + (np.arctan((2 * x - 1) / np.sqrt(3)) + np.pi / 6) / np.sqrt(3)) / x2
    assert np.isclose(fast_ion_fractional_heating(E, Te, mass), expected, rtol=1e-14, atol=1e-14)


def test_mixed_small_and_closed_form_entries_preserve_exact_values():
    E = np.array([0.0, 20.0])
    Te = 4.0
    mass = 2.0
    large_expected = fast_ion_fractional_heating(E[1], Te, mass)
    np.testing.assert_array_equal(
        fast_ion_fractional_heating(E, Te, mass),
        np.array([1.0, large_expected]),
    )


@pytest.mark.parametrize("args", [(-1.0, 10.0, 2.0), (1.0, 0.0, 2.0), (1.0, 10.0, 0.0)])
def test_invalid_domain_fails_closed(args):
    with pytest.raises(ValueError):
        fast_ion_fractional_heating(*args)
