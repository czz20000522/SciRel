"""Contract tests for the H(1s) radiative recombination fit."""

import numpy as np
import pytest

from scirel.collisions import evaluate_atomic_hydrogen_1s_radiative_recombination_rate


def _independent_formula(temperature):
    clipped = np.minimum(np.maximum(np.asarray(temperature, dtype=float), 0.1), 2.01e4)
    ionization_energy_ev = 13.58 / 1.0
    b_n = ionization_energy_ev / clipped
    return 3.92 * 1.0e-14 * np.sqrt(ionization_energy_ev / 13.58) * (
        b_n**1.5 / (b_n + 0.35)
    ) * 1.0e-6


def test_saved_values_and_independent_formula():
    temperature = np.array([0.1, 1.0, 10.0, 100.0, 1000.0, 20100.0])
    expected = np.array([
        4.556360479469746e-19, 1.4082657125240181e-19,
        3.6320168576101056e-20, 4.038110616603453e-21,
        1.7062227825507621e-22, 1.9630712377328093e-24,
    ])
    actual = evaluate_atomic_hydrogen_1s_radiative_recombination_rate(temperature)
    np.testing.assert_allclose(actual, expected, rtol=1e-15, atol=0.0)
    np.testing.assert_allclose(actual, _independent_formula(temperature), rtol=1e-15, atol=0.0)
    assert actual.shape == temperature.shape
    assert np.all(np.isfinite(actual)) and np.all(actual > 0.0)
    assert np.all(np.diff(actual) < 0.0)


def test_holdout_grid_matches_independent_formula():
    temperature = np.array([0.2, 2.0, 20.0, 200.0, 2000.0, 5000.0])
    np.testing.assert_allclose(
        evaluate_atomic_hydrogen_1s_radiative_recombination_rate(temperature),
        _independent_formula(temperature), rtol=1e-15, atol=0.0,
    )


def test_endpoint_clipping_and_scalar_shape():
    clipped = evaluate_atomic_hydrogen_1s_radiative_recombination_rate(
        np.array([0.01, 50000.0]),
    )
    edges = evaluate_atomic_hydrogen_1s_radiative_recombination_rate(
        np.array([0.1, 20100.0]),
    )
    np.testing.assert_array_equal(clipped, edges)
    scalar = evaluate_atomic_hydrogen_1s_radiative_recombination_rate(12.5)
    assert np.ndim(scalar) == 0 and np.isfinite(scalar) and scalar > 0.0


@pytest.mark.parametrize("temperature", [
    0.0, -5.0, np.nan, np.inf, [1.0, np.nan],
])
def test_invalid_temperature_fails_closed(temperature):
    with pytest.raises(ValueError, match="electron_temperature_ev"):
        evaluate_atomic_hydrogen_1s_radiative_recombination_rate(temperature)


@pytest.mark.parametrize("temperature", [
    True, [True, 1.0], "10.0", ["1.0", "2.0"], 1.0 + 0j,
])
def test_nonreal_temperature_fails_closed(temperature):
    with pytest.raises(ValueError, match="real"):
        evaluate_atomic_hydrogen_1s_radiative_recombination_rate(temperature)


def test_analytic_asymptotic_slopes_are_bound_to_this_test_file():
    """AUDIT-D5: the -1/2 / -3/2 slope evidence is bound by the contract.

    The contract previously pointed at an unbound audit file for these slopes;
    this test puts the evidence in the contract-bound direct test file.
    """
    temperature = np.geomspace(0.1, 2.01e4, 400)
    rate = evaluate_atomic_hydrogen_1s_radiative_recombination_rate(temperature)

    def slope(low, high):
        idx = np.searchsorted(temperature, [low, high])
        return float(
            (np.log(rate[idx[1]]) - np.log(rate[idx[0]]))
            / (np.log(temperature[idx[1]]) - np.log(temperature[idx[0]]))
        )

    assert -0.52 <= slope(0.15, 0.45) <= -0.49
    assert -1.52 <= slope(1.0e3, 1.8e4) <= -1.46
