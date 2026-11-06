"""Contract tests for terminal H2+ density and temperature reduction."""

import inspect

import numpy as np
import pytest

from scirel.kinetic import reduce_terminal_molecular_ion_state


def _case():
    rates = (
        np.array(
            [
                [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 1.0, 2.0, 3.0, 4.0],
                [0.4, 0.3, 0.2, 0.1, 0.6, 0.5, 0.7, 4.0, 3.0, 2.0, 1.0],
            ]
        )
        * 1e-18
    )
    return (
        np.array([4.0e17, 5.0e17]),
        np.array([1.0e18, 2.0e18]),
        np.array([2.0, 3.0]),
        2.0,
        np.array([4.0, 5.0]),
        rates,
        np.array([1.0, 3.0]),
    )


def test_four_profiles_match_independent_cell_reduction():
    molecular, electron, temperature, mass, ionization, rates, loss = _case()
    result = reduce_terminal_molecular_ion_state(*_case())
    expected_electron_loss = []
    expected_exchange = []
    expected_density = []
    expected_temperature = []
    for k in range(molecular.size):
        electron_loss = electron[k] * sum(rates[k, channel] for channel in range(7, 11))
        exchange = 7.7e-7 * electron[k] * 1e-6 / (np.sqrt(mass) * temperature[k] ** 1.5)
        denominator = electron_loss + loss[k]
        expected_electron_loss.append(electron_loss)
        expected_exchange.append(exchange)
        expected_density.append(molecular[k] * electron[k] * ionization[k] / denominator)
        expected_temperature.append(temperature[k] * exchange / (exchange + denominator))
    assert set(result) == {
        "molecular_ion_density_m3",
        "molecular_ion_temperature_ev",
        "electron_loss_frequency_s_inv",
        "energy_exchange_frequency_s_inv",
    }
    for key, expected in (
        ("molecular_ion_density_m3", expected_density),
        ("molecular_ion_temperature_ev", expected_temperature),
        ("electron_loss_frequency_s_inv", expected_electron_loss),
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


def test_public_parameter_and_output_names_are_the_canonical_contract():
    molecular, electron, temperature, mass, ionization, rates, loss = _case()
    assert list(inspect.signature(reduce_terminal_molecular_ion_state).parameters) == [
        "molecular_density_m3",
        "electron_density_m3",
        "ion_temperature_ev",
        "mass_ratio",
        "ionization_rate_coefficient_m3_s",
        "reaction_rate_table_m3_s",
        "loss_frequency_s_inv",
    ]
    result = reduce_terminal_molecular_ion_state(
        molecular_density_m3=molecular,
        electron_density_m3=electron,
        ion_temperature_ev=temperature,
        mass_ratio=mass,
        ionization_rate_coefficient_m3_s=ionization,
        reaction_rate_table_m3_s=rates,
        loss_frequency_s_inv=loss,
    )
    np.testing.assert_array_equal(
        result["electron_loss_frequency_s_inv"],
        electron * np.sum(rates[:, 7:11], axis=1),
    )


@pytest.mark.parametrize("mass", [1.0, 2.0, 3.0])
def test_mass_ratio_follows_the_same_algebraic_form(mass):
    arguments = list(_case())
    arguments[3] = mass
    result = reduce_terminal_molecular_ion_state(*arguments)
    expected = 7.7e-7 * arguments[1] * 1e-6 / (np.sqrt(mass) * arguments[2] ** 1.5)
    np.testing.assert_allclose(result["energy_exchange_frequency_s_inv"], expected, rtol=1e-15)


@pytest.mark.parametrize("mass", [0.0, -1.0])
def test_nonpositive_mass_ratio_fails_closed(mass):
    arguments = list(_case())
    arguments[3] = mass
    with pytest.raises(ValueError, match="physically nonnegative"):
        reduce_terminal_molecular_ion_state(*arguments)


@pytest.mark.parametrize(
    "index,value",
    [
        (0, np.array([True, False])),
        (1, np.array(["1e18", "2e18"])),
        (2, np.array([2.0, 3.0], dtype=complex)),
        (3, True),
        (4, np.array([True, True])),
        (5, np.ones((2, 11), dtype=bool)),
        (6, np.array(["1", "3"])),
    ],
)
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
