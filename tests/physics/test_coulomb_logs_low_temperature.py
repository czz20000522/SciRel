"""Issue #10 item 3: the Coulomb logarithms declare the NRL low-temperature boundary."""

import warnings

import numpy as np
import pytest

import scirel
from scirel.physics import (
    calculate_log_lambda_ee,
    calculate_log_lambda_ei,
    calculate_log_lambda_ii,
)

BOUNDARY_KEV = 0.01  # NRL boundary T_e ~ 10 Z^2 eV at Z = 1


def _hand_formula_ee(te_kev, ne_m3):
    return 31.0 - 0.5 * np.log(ne_m3) + np.log(1e3 * te_kev)


def _hand_formula_ei(te_kev, ne_m3):
    return 31.3 - 0.5 * np.log(ne_m3) + np.log(1e3 * te_kev)


@pytest.mark.parametrize(
    "function, hand_formula",
    [(calculate_log_lambda_ee, _hand_formula_ee), (calculate_log_lambda_ei, _hand_formula_ei)],
)
def test_below_ten_ev_warns_once_and_returns_the_same_value(function, hand_formula):
    """The value is unchanged; only the missing low-temperature regime is announced."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        value = function(0.005, 1e19)
    runtime = [item for item in caught if issubclass(item.category, scirel.ApplicabilityWarning)]
    assert len(runtime) == 1
    message = str(runtime[0].message)
    assert "10 Z^2 eV" in message and "10 eV" in message
    # api-spec: the message names the actual offending value, not just the limit.
    assert "lowest input 5 eV" in message
    assert np.isclose(value, hand_formula(0.005, 1e19), rtol=0, atol=1e-14)


@pytest.mark.parametrize("function", [calculate_log_lambda_ee, calculate_log_lambda_ei])
def test_above_the_nrl_boundary_warns_nothing(function):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        function(np.array([0.01, 0.011, 1.0, 50.0]), 1e19)
    assert caught == []


@pytest.mark.parametrize("function", [calculate_log_lambda_ee, calculate_log_lambda_ei])
def test_boundary_is_the_nrl_ten_ev_point_not_the_twenty_seven_ev_crossover(function):
    """Issue #10 item 3: the declared boundary follows the formulary, not the derived crossing."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        function(np.array([0.0099, 0.0101]), 1e19)
    assert (
        len([item for item in caught if issubclass(item.category, scirel.ApplicabilityWarning)])
        == 1
    )


def test_ion_ion_form_never_warns_on_the_electron_boundary():
    """``ii`` already uses the classical cutoff branch, so the electron boundary does not apply."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        calculate_log_lambda_ii(1e-4, 1e19, 1.0)
    assert caught == []
