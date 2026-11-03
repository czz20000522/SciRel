"""Contract tests for terminal H2+ density and temperature reduction."""

import numpy as np
import pytest

from scirel.kinetic import reduce_terminal_molecular_ion_state


def _case():
    rates = np.array(
        [[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 1.0, 2.0, 3.0, 4.0],
         [0.4, 0.3, 0.2, 0.1, 0.6, 0.5, 0.7, 4.0, 3.0, 2.0, 1.0]]
    ) * 1e-18
    return (
        np.array([4.0e17, 5.0e17]), np.array([1.0e18, 2.0e18]),
        np.array([2.0, 3.0]), 2.0, np.array([4.0, 5.0]),
        rates, np.array([1.0, 3.0]),
    )


def test_four_profiles_match_independent_cell_reduction():
    molecular, neutral, temperature, mass, ionization, rates, loss = _case()
    result = reduce_terminal_molecular_ion_state(*_case())
    expected_dissociation = []
    expected_exchange = []
    expected_density = []
    expected_temperature = []
    for k in range(molecular.size):
        dissociation = neutral[k] * sum(rates[k, channel] for channel in range(7, 11))
        exchange = 7.7e-7 * neutral[k] * 1e-6 / (np.sqrt(mass) * temperature[k] ** 1.5)
        denominator = dissociation + loss[k]
        expected_dissociation.append(dissociation)
        expected_exchange.append(exchange)
        expected_density.append(molecular[k] * neutral[k] * ionization[k] / denominator)
        expected_temperature.append(temperature[k] * exchange / (exchange + denominator))
    assert set(result) == {
        "molecular_ion_density_m3", "molecular_ion_temperature_ev",
        "dissociation_frequency_s_inv", "energy_exchange_frequency_s_inv",
    }
    for key, expected in (
        ("molecular_ion_density_m3", expected_density),
        ("molecular_ion_temperature_ev", expected_temperature),
        ("dissociation_frequency_s_inv", expected_dissociation),
        ("energy_exchange_frequency_s_inv", expected_exchange),
    ):
        np.testing.assert_allclose(result[key], expected, rtol=1e-15, atol=0)


def test_only_reaction_table_channels_seven_through_ten_are_used():
    arguments = list(_case())
    baseline = reduce_terminal_molecular_ion_state(*arguments)
    changed = arguments[5].copy()
    changed[:, :7] = 1e10
    arguments[5] = changed
    result = reduce_terminal_molecular_ion_state(*arguments)
    for key in baseline:
        np.testing.assert_array_equal(result[key], baseline[key])


def test_zero_molecular_density_is_allowed_with_positive_denominator():
    arguments = list(_case())
    arguments[0] = np.array([0.0, 5.0e17])
    result = reduce_terminal_molecular_ion_state(*arguments)
    assert result["molecular_ion_density_m3"][0] == 0.0


@pytest.mark.parametrize("index,value", [
    (0, np.array([True, False])),
    (1, np.array(["1e18", "2e18"])),
    (2, np.array([2.0, 3.0], dtype=complex)),
    (3, True),
    (4, np.array([True, True])),
    (5, np.ones((2, 11), dtype=bool)),
    (6, np.array(["1", "3"])),
])
def test_nonreal_or_nonnumeric_inputs_fail_closed(index, value):
    arguments = list(_case())
    arguments[index] = value
    with pytest.raises(ValueError, match="real numeric"):
        reduce_terminal_molecular_ion_state(*arguments)


def test_zero_density_denominator_and_nonfinite_output_fail_closed():
    arguments = list(_case())
    arguments[5] = np.zeros((2, 11))
    arguments[6] = np.array([0.0, 3.0])
    with pytest.raises(ValueError, match="strictly positive molecular-ion density denominator"):
        reduce_terminal_molecular_ion_state(*arguments)
    arguments = list(_case())
    arguments[0] = np.full(2, np.finfo(float).max)
    with np.errstate(over="ignore", invalid="ignore"):
        with pytest.raises(ValueError, match="invalid profile"):
            reduce_terminal_molecular_ion_state(*arguments)
