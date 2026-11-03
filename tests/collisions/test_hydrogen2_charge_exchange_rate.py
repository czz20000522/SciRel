"""Contract tests for the H2 charge-exchange rate fit."""

import numpy as np
import pytest

from scirel.collisions import (
    evaluate_atomic_hydrogen_charge_exchange_rate,
    evaluate_hydrogen2_charge_exchange_rate,
)
from scirel.collisions.hydrogen2_charge_exchange_rate import _COEFFICIENTS


def test_fit_matches_reference_points_and_differs_from_atomic_sibling():
    temperature = np.array([0.1, 1.0, 10.0, 100.0, 1000.0, 20100.0])
    energy = np.array([0.2, 1.0, 10.0, 100.0, 1000.0, 20100.0])
    expected = np.array([
        8.323872621217987e-16, 1.8072939336757143e-15,
        4.935149491237489e-15, 8.525859702613574e-15,
        2.492301970872774e-14, 4.3400936549177445e-14,
    ])
    result = evaluate_hydrogen2_charge_exchange_rate(temperature, energy)
    oracle = np.exp(np.polynomial.polynomial.polyval2d(
        np.log(energy), np.log(temperature), _COEFFICIENTS.T,
    )) * 1e-6

    np.testing.assert_allclose(result, expected, rtol=1e-14, atol=0.0)
    np.testing.assert_allclose(result[:-1], oracle[:-1], rtol=1e-12, atol=0.0)
    atomic = evaluate_atomic_hydrogen_charge_exchange_rate(temperature, energy)
    assert not np.allclose(result, atomic, rtol=1e-12, atol=0.0)
    assert result.shape == temperature.shape
    assert np.all(np.isfinite(result)) and np.all(result > 0.0)


def test_fit_preserves_legacy_term_order_bit_for_bit():
    rng = np.random.default_rng(20261019)
    temperature = np.exp(rng.uniform(np.log(0.1), np.log(2.01e4), (5, 7)))
    energy = np.exp(rng.uniform(np.log(0.1), np.log(2.01e4), (5, 7)))
    log_temperature = np.log(np.minimum(np.maximum(temperature, 0.1), 2.01e4))
    log_energy = np.log(np.minimum(np.maximum(energy, 0.1), 2.01e4))

    expected_log_rate = np.zeros_like(log_energy, dtype=float)
    for energy_power in range(9):
        for temperature_power in range(9):
            expected_log_rate = expected_log_rate + (
                _COEFFICIENTS[temperature_power, energy_power]
                * log_energy**energy_power
                * log_temperature**temperature_power
            )
    expected = np.exp(expected_log_rate) * 1.0e-6

    np.testing.assert_array_equal(
        evaluate_hydrogen2_charge_exchange_rate(temperature, energy),
        expected,
    )


def test_clipping_and_scalar_shape():
    clipped = evaluate_hydrogen2_charge_exchange_rate(
        np.array([0.01, 50000.0]), np.array([0.0, 50000.0]),
    )
    edges = evaluate_hydrogen2_charge_exchange_rate(
        np.array([0.1, 20100.0]), np.array([0.1, 20100.0]),
    )
    np.testing.assert_array_equal(clipped, edges)
    assert np.ndim(evaluate_hydrogen2_charge_exchange_rate(1.0, 2.0)) == 0


@pytest.mark.parametrize("temperature,energy", [
    (np.array([1.0, 2.0]), np.array([[1.0], [2.0]])),
    (np.array([0.0]), np.array([1.0])),
    (np.array([-1.0]), np.array([1.0])),
    (np.array([1.0]), np.array([-1.0])),
    (np.array([np.nan]), np.array([1.0])),
    (np.array([1.0]), np.array([np.inf])),
])
def test_invalid_domain_fails_closed(temperature, energy):
    with pytest.raises(ValueError):
        evaluate_hydrogen2_charge_exchange_rate(temperature, energy)


@pytest.mark.parametrize("temperature,energy", [
    ([True, 1.0], [1.0, 2.0]),
    (["1.0", "2.0"], [1.0, 2.0]),
    (np.array([1.0 + 0j]), np.array([1.0])),
    ([1.0, 2.0], [False, True]),
    ([1.0, 2.0], ["1.0", "2.0"]),
    (np.array([1.0]), np.array([1.0 + 0j])),
])
def test_nonreal_input_fails_closed(temperature, energy):
    with pytest.raises(ValueError, match="real"):
        evaluate_hydrogen2_charge_exchange_rate(temperature, energy)


def test_fit_is_nonmonotonic_in_impact_energy_at_1000_ev():
    """AUDIT-D5: the frozen bivariate fit is not monotone; pin that limitation.

    The contract now documents the non-monotonicity; this regression fails if the
    behavior changes without the limitation being revisited.
    """
    energy = np.geomspace(0.1, 2.01e4, 500)
    rate = evaluate_hydrogen2_charge_exchange_rate(
        np.full(energy.shape, 1000.0), energy)
    sign = np.sign(np.diff(np.log(rate)))
    sign_changes = int(np.sum(np.diff(sign) != 0))
    assert sign_changes >= 4
    assert float(rate.min() / rate.max()) < 0.30
