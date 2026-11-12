"""Contract tests for the H(1s) radiative recombination fit."""

import warnings

import numpy as np
import pytest
from scipy import constants as _constants
from scipy import integrate

import scirel
from scirel.collisions import evaluate_atomic_hydrogen_1s_radiative_recombination_rate

# (2^9 pi^2 / 3) alpha a0^2: the prefactor of the exact 1s photoionization cross section.
_SIGMA_SCALE = (
    512 * np.pi**2 / 3 * _constants.alpha * _constants.physical_constants["Bohr radius"][0] ** 2
)
# Declared accuracy of the fit over [0.1, 30] eV: the observed maximum is 5.72% at ~19.5 eV.
_DECLARED_BOUND = 0.0575


def _independent_formula(temperature):
    clipped = np.minimum(np.maximum(np.asarray(temperature, dtype=float), 0.1), 2.01e4)
    ionization_energy_ev = 13.58 / 1.0
    b_n = ionization_energy_ev / clipped
    return (
        3.92 * 1.0e-14 * np.sqrt(ionization_energy_ev / 13.58) * (b_n**1.5 / (b_n + 0.35)) * 1.0e-6
    )


def test_saved_values_and_independent_formula():
    temperature = np.array([0.1, 1.0, 10.0, 100.0, 1000.0, 20100.0])
    expected = np.array(
        [
            4.556360479469746e-19,
            1.4082657125240181e-19,
            3.6320168576101056e-20,
            4.038110616603453e-21,
            1.7062227825507621e-22,
            1.9630712377328093e-24,
        ]
    )
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
        _independent_formula(temperature),
        rtol=1e-15,
        atol=0.0,
    )


def _exact_rate(temperature_ev):
    """Independent 1s radiative recombination rate, built from physics only.

    `sigma_bf` is the exact hydrogenic 1s photoionization cross section (Stobbe 1930 closed
    form), `exact_rate` applies the Milne relation with the level-one statistical weight
    ratio ``g_n/g_+ = 2`` and averages over a Maxwellian. Nothing here reads the fit, its
    coefficients or its output, so a constant error in the fit cannot hide in the oracle.
    """
    temperature_ev = np.asarray(temperature_ev, dtype=float)
    return np.array([_exact_rate_scalar(float(value)) for value in temperature_ev.ravel()]).reshape(
        temperature_ev.shape
    )


def _exact_rate_scalar(temperature_ev):
    chi = _constants.Rydberg * _constants.h * _constants.c
    kT = temperature_ev * _constants.e
    prefactor = np.sqrt(8.0 / (np.pi * _constants.m_e)) / np.sqrt(kT)

    def integrand(u):
        energy = u * kT
        eps = np.sqrt(energy / chi)
        if eps == 0.0:
            sigma_bf = _SIGMA_SCALE * np.exp(-4.0)
        else:
            sigma_bf = (
                _SIGMA_SCALE
                * (chi / (chi + energy)) ** 4
                * np.exp(-4.0 * np.arctan(eps) / eps)
                / (-np.expm1(-2.0 * np.pi / eps))
            )
        return (chi + energy) ** 2 / (_constants.m_e * _constants.c**2) * sigma_bf * np.exp(-u)

    value, _ = integrate.quad(integrand, 0.0, np.inf, epsabs=0.0, epsrel=1e-10)
    return prefactor * value


def test_the_oracle_reproduces_the_textbook_level_one_rate():
    """Anchor the independent oracle before using it: alpha_1(1e4 K) = 1.58e-13 cm^3/s."""
    rate = _exact_rate_scalar(_constants.k * 1e4 / _constants.e) * 1e6
    assert abs(rate / 1.582e-13 - 1.0) < 2e-3


def test_fit_matches_the_independent_oracle_within_the_measured_bound():
    """Issue #10 item 1: the declared accuracy is the observed maximum, not a guessed band.

    Measured on a 601-point log grid over [0.1, 30] eV: the worst departure is +5.72% at
    about 19.5 eV. The bound is therefore stated as 5.75%; the old "5.3%" claim is refuted by
    the 20 eV point (+5.71517%), which the grid covers here.
    """
    temperature = np.geomspace(0.1, 30.0, 601)
    oracle = _exact_rate(temperature)
    fit = evaluate_atomic_hydrogen_1s_radiative_recombination_rate(temperature)
    deviation = np.abs(fit / oracle - 1.0)
    assert deviation.max() <= _DECLARED_BOUND
    worst = temperature[deviation.argmax()]
    assert 19.1 < worst < 19.7  # independent scans put the peak at 19.37-19.47 eV
    # The counterexample that killed the 5.3% claim must stay visible, not be smoothed away.
    at_20 = float(
        evaluate_atomic_hydrogen_1s_radiative_recombination_rate(20.0) / _exact_rate_scalar(20.0)
        - 1.0
    )
    assert 0.05 < at_20 < 0.06


def test_anchor_ratios_against_the_independent_oracle():
    """The five anchors that issue #10 records, recomputed against the physics-only oracle."""
    temperature = np.array([0.1, 1.0, 10.0, 20.0, 30.0])
    expected = np.array([0.9473085930, 0.9647996863, 1.0432707998, 1.0571517077, 1.0490534031])
    fit = evaluate_atomic_hydrogen_1s_radiative_recombination_rate(temperature)
    np.testing.assert_allclose(fit / _exact_rate(temperature), expected, rtol=5e-9, atol=0.0)


def test_above_30_ev_warns_and_clips_instead_of_extrapolating():
    """Issue #10 item 1: values above the validated interval warn, then clip, unchanged."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        above = evaluate_atomic_hydrogen_1s_radiative_recombination_rate(
            np.array([30.0, 31.0, 1000.0, 20100.0])
        )
    warnings_above = [
        item for item in caught if issubclass(item.category, scirel.ApplicabilityWarning)
    ]
    # One warning per call: the message names the violated limit, not the per-sample count.
    assert len(warnings_above) == 1
    message = str(warnings_above[0].message)
    assert "30 eV" in message
    # api-spec: the message names the actual offending value, not just the limit.
    assert "highest input 20100 eV" in message
    # The fit interval stays [0.1, 2.01e4] eV: samples above 30 eV are evaluated by the fit at
    # their own temperature (clipped only at 2.01e4) and marked low-biased by the warning.
    np.testing.assert_array_equal(
        above, _independent_formula(np.array([30.0, 31.0, 1000.0, 20100.0]))
    )


def test_below_0_1_ev_warns_once_and_names_the_actual_value():
    """Issue #10 item 1: the low end was silently truncated; the bias is now announced."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        low = evaluate_atomic_hydrogen_1s_radiative_recombination_rate(np.array([0.001, 0.01, 0.1]))
    applicable = [item for item in caught if issubclass(item.category, scirel.ApplicabilityWarning)]
    assert len(applicable) == 1
    message = str(applicable[0].message)
    assert "lower limit of 0.1 eV" in message and "lowest input 0.001 eV" in message
    # Values below the limit repeat the 0.1 eV endpoint; the true rate there is larger.
    np.testing.assert_array_equal(low, np.full(3, low[2]))
    assert _exact_rate_scalar(0.01) > low[0]


def test_within_30_ev_warns_nothing():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        evaluate_atomic_hydrogen_1s_radiative_recombination_rate(np.array([0.1, 1.0, 29.9]))
    assert caught == []


def test_an_out_of_range_call_fails_when_applicability_warnings_are_errors():
    """Issue #156 acceptance shape: callers can require validated input."""
    with warnings.catch_warnings():
        warnings.simplefilter("error", scirel.ApplicabilityWarning)
        with pytest.raises(scirel.ApplicabilityWarning, match="30 eV"):
            evaluate_atomic_hydrogen_1s_radiative_recombination_rate(100.0)


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


@pytest.mark.parametrize(
    "temperature",
    [
        0.0,
        -5.0,
        np.nan,
        np.inf,
        [1.0, np.nan],
    ],
)
def test_invalid_temperature_fails_closed(temperature):
    with pytest.raises(ValueError, match="electron_temperature_ev"):
        evaluate_atomic_hydrogen_1s_radiative_recombination_rate(temperature)


@pytest.mark.parametrize(
    "temperature",
    [
        True,
        [True, 1.0],
        "10.0",
        ["1.0", "2.0"],
        1.0 + 0j,
    ],
)
def test_nonreal_temperature_fails_closed(temperature):
    with pytest.raises(ValueError, match="real"):
        evaluate_atomic_hydrogen_1s_radiative_recombination_rate(temperature)


def test_analytic_asymptotic_slopes_are_bound_to_this_test_file():
    """AUDIT-D5: the -1/2 / -3/2 slope evidence is bound by the contract.

    The contract previously pointed at an unbound audit file for these slopes;
    this test puts the evidence in the contract-bound direct test file.
    """
    temperature = np.geomspace(0.1, 2.01e4, 400)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", scirel.ApplicabilityWarning)
        rate = evaluate_atomic_hydrogen_1s_radiative_recombination_rate(temperature)

    def slope(low, high):
        idx = np.searchsorted(temperature, [low, high])
        return float(
            (np.log(rate[idx[1]]) - np.log(rate[idx[0]]))
            / (np.log(temperature[idx[1]]) - np.log(temperature[idx[0]]))
        )

    assert -0.52 <= slope(0.15, 0.45) <= -0.49
    assert -1.52 <= slope(1.0e3, 1.8e4) <= -1.46
