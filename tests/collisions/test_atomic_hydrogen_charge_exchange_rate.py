"""Contract tests for the atomic-H charge-exchange rate coefficient."""

import math

import numpy as np
import pytest
from scipy.special import roots_legendre

from scirel.collisions import evaluate_atomic_hydrogen_charge_exchange_rate
from scirel.collisions.atomic_hydrogen_charge_exchange_rate import _COEFFICIENTS

M_H = 1.6726231e-27
Q = 1.602177e-19
JOIN_EV = 1.267317514018116e4
CROSS_SECTION_UPPER_EV = 2.5e5


def independent_composite_cross_section(energy_ev):
    energy = np.asarray(energy_ev, dtype=float)
    janev_coefficients = np.array(
        [
            -3.274123792568e1,
            -8.916456579806e-2,
            -3.016990732025e-2,
            9.205482406462e-3,
            2.400266568315e-3,
            -1.927122311323e-3,
            3.654750340106e-4,
            -2.788866460622e-5,
            7.422296363524e-7,
        ]
    )
    janev = np.exp(np.polynomial.polynomial.polyval(np.log(energy), janev_coefficients)) * 1.0e-4
    energy_kev = energy / 1000.0
    lindsay_stebbings = (
        (4.15 - 0.531 * np.log(energy_kev)) ** 2
        * (1.0 - np.exp(-67.3 / energy_kev)) ** 4.5
        * 1.0e-20
    )
    return np.where(energy <= JOIN_EV, janev, lindsay_stebbings)


def independent_maxwellian_rate(temperature_ev, energy_ev, nvr, nvx, vmax):
    """Independent 2D Gauss-Legendre Maxwellian quadrature."""
    xr, wr = roots_legendre(nvr)
    xx, wx = roots_legendre(nvx)
    vr = 0.5 * vmax * (xr + 1.0)
    wvr = 0.5 * vmax * wr
    vx = vmax * (xx + 1.0) - vmax
    wvx = vmax * wx
    radial, axial = np.meshgrid(vr, vx, indexing="ij")
    weights = 2.0 * np.pi * radial * wvr[:, None] * wvx[None, :] * np.exp(-(radial**2 + axial**2))
    weights /= weights.sum()
    beam_speed = math.sqrt(energy_ev / temperature_ev)
    relative_speed = np.sqrt(radial**2 + (axial - beam_speed) ** 2)
    collision_energy = temperature_ev * relative_speed**2
    cross_section = np.zeros_like(collision_energy)
    covered = collision_energy <= CROSS_SECTION_UPPER_EV
    cross_section[covered] = independent_composite_cross_section(
        np.maximum(collision_energy[covered], 0.1)
    )
    thermal_speed = math.sqrt(2.0 * Q * temperature_ev / M_H)
    return thermal_speed * np.sum(weights * cross_section * relative_speed)


def test_low_energy_fit_matches_reference_points_and_independent_polynomial():
    temperature = np.array([0.1, 1.0, 10.0, 100.0, 1000.0, 20100.0])
    energy = np.array([0.2, 1.0, 10.0, 100.0, 1000.0, 20100.0])
    expected = np.array(
        [
            4.876780824328715e-15,
            1.1386973426393434e-14,
            2.582052648196978e-14,
            5.2958886310870015e-14,
            8.964452892686682e-14,
            5.4721543485444824e-14,
        ]
    )
    result = evaluate_atomic_hydrogen_charge_exchange_rate(temperature, energy)
    oracle = (
        np.exp(
            np.polynomial.polynomial.polyval2d(
                np.log(energy),
                np.log(temperature),
                _COEFFICIENTS.T,
            )
        )
        * 1e-6
    )

    np.testing.assert_allclose(result, expected, rtol=1e-14, atol=0.0)
    np.testing.assert_allclose(result[:-1], oracle[:-1], rtol=1e-12, atol=0.0)
    assert result.shape == temperature.shape


def test_low_energy_fit_preserves_legacy_term_order_bit_for_bit():
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
        evaluate_atomic_hydrogen_charge_exchange_rate(temperature, energy),
        expected,
    )


@pytest.mark.parametrize(
    "nvr,nvx,vmax",
    [(260, 400, 7.0), (500, 700, 8.0)],
)
def test_high_energy_rate_matches_independent_maxwellian_quadrature(nvr, nvx, vmax):
    expected = independent_maxwellian_rate(50_000.0, 100_000.0, nvr, nvx, vmax)
    actual = float(evaluate_atomic_hydrogen_charge_exchange_rate(50_000.0, 100_000.0))
    np.testing.assert_allclose(actual, expected, rtol=2.0e-3, atol=0.0)


def test_high_energy_rate_replaces_the_clipped_endpoint():
    result = float(evaluate_atomic_hydrogen_charge_exchange_rate(50_000.0, 100_000.0))
    clipped_endpoint = float(evaluate_atomic_hydrogen_charge_exchange_rate(20_100.0, 20_100.0))
    assert result < clipped_endpoint / 4.0


def test_clipping_and_scalar_shape():
    with pytest.warns(RuntimeWarning, match="upper limit"):
        clipped = evaluate_atomic_hydrogen_charge_exchange_rate(
            np.array([0.01, 3.0e5]),
            np.array([0.0, 3.0e5]),
        )
    edges = evaluate_atomic_hydrogen_charge_exchange_rate(
        np.array([0.1, 2.5e5]),
        np.array([0.1, 2.5e5]),
    )
    np.testing.assert_allclose(clipped, edges, rtol=1e-12, atol=0.0)
    assert np.ndim(evaluate_atomic_hydrogen_charge_exchange_rate(1.0, 2.0)) == 0


@pytest.mark.parametrize(
    "temperature,energy",
    [
        (np.array([1.0, 2.0]), np.array([[1.0], [2.0]])),
        (np.array([0.0]), np.array([1.0])),
        (np.array([-1.0]), np.array([1.0])),
        (np.array([1.0]), np.array([-1.0])),
        (np.array([np.nan]), np.array([1.0])),
        (np.array([1.0]), np.array([np.inf])),
    ],
)
def test_invalid_domain_fails_closed(temperature, energy):
    with pytest.raises(ValueError):
        evaluate_atomic_hydrogen_charge_exchange_rate(temperature, energy)


@pytest.mark.parametrize(
    "temperature,energy",
    [
        ([True, 1.0], [1.0, 2.0]),
        (["1.0", "2.0"], [1.0, 2.0]),
        (np.array([1.0 + 0j]), np.array([1.0])),
        ([1.0, 2.0], [False, True]),
        ([1.0, 2.0], ["1.0", "2.0"]),
        (np.array([1.0]), np.array([1.0 + 0j])),
    ],
)
def test_nonreal_input_fails_closed(temperature, energy):
    with pytest.raises(ValueError, match="real"):
        evaluate_atomic_hydrogen_charge_exchange_rate(temperature, energy)


def test_low_energy_fit_is_nonmonotonic_in_impact_energy_at_1000_ev():
    energy = np.geomspace(0.1, 2.01e4, 500)
    rate = evaluate_atomic_hydrogen_charge_exchange_rate(np.full(energy.shape, 1000.0), energy)
    sign = np.sign(np.diff(np.log(rate)))
    sign_changes = int(np.sum(np.diff(sign) != 0))
    assert sign_changes >= 6
    assert float(rate.min() / rate.max()) < 0.70
