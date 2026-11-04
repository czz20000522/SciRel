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
