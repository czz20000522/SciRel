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


# --- Issue #10 item 3 split round: ee and ei are different collision pairs ---------
# Their classical references differ, so the deviation of the quantum branch must be
# measured per pair.  The references below are the NRL classical forms recomputed
# here, not taken from the implementation's warning text.


def _nrl_classical_ee(te_ev, ne_m3):
    """NRL classical e-e form: 24 - ln(n_e^0.5 T_e^-1), T_e in eV, n_e in cm^-3."""
    return 24.0 - np.log(np.sqrt(ne_m3 / 1e6) / te_ev)


def _nrl_classical_ei(te_ev, ne_m3, z=1.0):
    """NRL classical e-i form: 23 - ln(n_e^0.5 Z T_e^-1.5)."""
    return 23.0 - np.log(np.sqrt(ne_m3 / 1e6) * z * te_ev**-1.5)


def _warned_message(function, te_kev, ne_m3=1e19):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        function(te_kev, ne_m3)
    messages = [
        str(item.message)
        for item in caught
        if issubclass(item.category, scirel.ApplicabilityWarning)
    ]
    assert len(messages) == 1
    return messages[0]


def test_the_two_pairs_do_not_share_one_warning_message():
    """A shared message was the defect: it quoted the e-i reference for both pairs."""
    ee_message = _warned_message(calculate_log_lambda_ee, 0.005)
    ei_message = _warned_message(calculate_log_lambda_ei, 0.005)
    assert ee_message != ei_message
    # each message cites its own pair's classical reference
    assert "24 - ln(n_e^0.5 T_e^-1)" in ee_message
    assert "23 - ln(n_e^0.5 Z T_e^-1.5)" in ei_message
    assert "23 - ln(n_e^0.5 Z T_e^-1.5)" not in ee_message
    assert "24 - ln(n_e^0.5 T_e^-1)" not in ei_message


@pytest.mark.parametrize(
    "function, reference",
    [
        (calculate_log_lambda_ee, _nrl_classical_ee),
        (calculate_log_lambda_ei, _nrl_classical_ei),
    ],
)
@pytest.mark.parametrize("te_ev", [0.1, 1.0])
@pytest.mark.parametrize("ne", [1e17, 1e19, 1e21])
def test_the_warned_deviation_is_computed_at_the_offending_sample(function, reference, te_ev, ne):
    """The message must quote the deviation at the caller's own density.

    A fixed percentage would mislead: the relative gap grows with density, so the
    same pair reads very differently at 1e17 and 1e21.  The check recomputes the
    ratio from the pair's own classical form and requires the quoted value to
    match at the printed precision.
    """
    measured = (function(te_ev / 1000.0, ne) / reference(te_ev, ne) - 1.0) * 100.0
    message = _warned_message(function, te_ev / 1000.0, ne)
    assert f"n_e = {ne:.6g} m^-3" in message
    quoted = [
        float(token.rstrip("%"))
        for token in message.replace("+", " ").split()
        if token.endswith("%") and _is_number(token.rstrip("%"))
    ]
    assert quoted, message
    assert any(abs(value - measured) < 0.5 for value in quoted), (measured, quoted, message)


def _is_number(text):
    try:
        float(text)
        return True
    except ValueError:
        return False


def test_the_relative_gap_grows_with_density_for_both_pairs():
    """Both pairs keep a fixed absolute offset, so the relative gap rises with density."""
    for function, reference in (
        (calculate_log_lambda_ee, _nrl_classical_ee),
        (calculate_log_lambda_ei, _nrl_classical_ei),
    ):
        low = function(1e-4, 1e17) / reference(0.1, 1e17) - 1.0
        high = function(1e-4, 1e21) / reference(0.1, 1e21) - 1.0
        assert high > low


def test_ei_quantum_branch_crosses_its_classical_form_near_sixteen_ev():
    """Above the crossing the quantum e-i form reads lower, so the boundary is not a
    'below is wrong, above is right' rule; the e-e pair has no crossing in this range."""
    ne = 1e19
    below = calculate_log_lambda_ei(0.010, ne) - _nrl_classical_ei(10.0, ne)
    above = calculate_log_lambda_ei(0.030, ne) - _nrl_classical_ei(30.0, ne)
    assert below > 0.0 and above < 0.0
    grid = np.logspace(-2, 4, 4000)
    crossings = [
        te
        for a, b, te in zip(grid[:-1], grid[1:], grid[1:])
        if (calculate_log_lambda_ei(a / 1000.0, ne) - _nrl_classical_ei(a, ne))
        * (calculate_log_lambda_ei(b / 1000.0, ne) - _nrl_classical_ei(b, ne))
        < 0
    ]
    assert len(crossings) == 1 and 16.0 < crossings[0] < 16.5
    ee_gap = [calculate_log_lambda_ee(te / 1000.0, ne) - _nrl_classical_ee(te, ne) for te in grid]
    assert all(value > 0.0 for value in ee_gap)
