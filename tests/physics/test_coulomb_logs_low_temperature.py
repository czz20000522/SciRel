"""Issue #197: each Coulomb-log pair carries its own low-temperature reference.

The e-e reference is the NRL Plasma Formulary (2016, printed p. 34) e-e relation itself, not its
high-temperature limit. The e-i reference is the formulary's low-temperature e-i branch, whose
``T_e > 10 Z^2 eV`` condition belongs to e-i only. Expected deviations are recomputed here from
the published formulas, never from the implementation under test.
"""

import math
import warnings

import numpy as np
import pytest

import scirel
from scirel.physics import (
    calculate_log_lambda_ee,
    calculate_log_lambda_ei,
    calculate_log_lambda_ii,
)

# Advisory line below which both relations warn (eV).
BOUNDARY_EV = 10.0


def _quantum_ee(t_ev, n_m3):
    """The high-temperature branch SciRel evaluates for e-e, from its documented algebra."""
    return 31.0 + math.log(t_ev) - 0.5 * math.log(n_m3)


def _quantum_ei(t_ev, n_m3):
    return 31.3 + math.log(t_ev) - 0.5 * math.log(n_m3)


def _nrl_ee(t_ev, n_m3):
    """NRL Plasma Formulary 2016 printed p.34 e-e relation (T_e in eV, n_e in cm^-3)."""
    n_cm3 = n_m3 * 1e-6
    return (
        23.5
        - math.log(math.sqrt(n_cm3) * t_ev**-1.25)
        - math.sqrt(1e-5 + (math.log(t_ev) - 2.0) ** 2 / 16.0)
    )


def _nrl_ei_low(t_ev, n_m3, z=1.0):
    """NRL low-temperature e-i branch (T_e in eV, n_e in cm^-3)."""
    n_cm3 = n_m3 * 1e-6
    return 23.0 - math.log(math.sqrt(n_cm3) * z * t_ev**-1.5)


def _hand_formula_ee(te_kev, ne_m3):
    return 31.0 - 0.5 * np.log(ne_m3) + np.log(1e3 * te_kev)


def _hand_formula_ei(te_kev, ne_m3):
    return 31.3 - 0.5 * np.log(ne_m3) + np.log(1e3 * te_kev)


def _applicability(warnings_list):
    return [
        item for item in warnings_list if issubclass(item.category, scirel.ApplicabilityWarning)
    ]


@pytest.mark.parametrize(
    "function, hand_formula",
    [(calculate_log_lambda_ee, _hand_formula_ee), (calculate_log_lambda_ei, _hand_formula_ei)],
)
def test_below_the_advisory_boundary_warns_once_and_returns_the_same_value(function, hand_formula):
    """The value is unchanged; only the missing low-temperature regime is announced."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        value = function(0.005, 1e19)
    found = _applicability(caught)
    assert len(found) == 1
    message = str(found[0].message)
    assert "10 eV" in message
    # api-spec: the message names the actual offending value, not just the limit.
    assert "lowest input 5 eV" in message
    assert np.isclose(value, hand_formula(0.005, 1e19), rtol=0, atol=1e-14)


@pytest.mark.parametrize("function", [calculate_log_lambda_ee, calculate_log_lambda_ei])
def test_at_or_above_the_advisory_boundary_warns_nothing(function):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        function(np.array([0.01, 0.011, 1.0, 50.0]), 1e19)
    assert caught == []


def test_ee_message_uses_the_nrl_ee_relation_and_reports_the_measured_gap():
    """Issue #197: the e-e gap is ~+49% at 0.1 eV against the NRL e-e relation.

    The NRL e-e form and its high-temperature limit differ by this much, so quoting the limit
    (the old behaviour, which produced +1.37%) understates the gap by more than an order of
    magnitude.
    """
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        calculate_log_lambda_ee(0.002, 1e19)  # 2 eV -> below the advisory line
    message = str(_applicability(caught)[0].message)
    expected = _quantum_ee(2.0, 1e19) / _nrl_ee(2.0, 1e19) - 1.0
    assert "T_e^(-5/4)" in message and "sqrt(1e-5" in message
    assert "algebraic difference" in message
    assert f"{expected:+.2%}" in message
    assert "not to this relation" in message  # the 10 Z^2 condition belongs to e-i


def test_ee_deviation_against_the_nrl_relation_at_the_issue_anchors():
    """Anchor values from issue #197 (n_e = 1e19 m^-3), recomputed from the published formula."""
    anchors = {0.1: 0.489929631, 1.0: 0.135967796, 10.0: 0.008143358}
    for t_ev, expected in anchors.items():
        deviation = _quantum_ee(t_ev, 1e19) / _nrl_ee(t_ev, 1e19) - 1.0
        assert deviation == pytest.approx(expected, abs=5e-9)
    # And the implementation's returned value reproduces the same ratio.
    for t_ev, expected in anchors.items():
        value = float(calculate_log_lambda_ee(t_ev / 1000.0, 1e19))
        assert value / _nrl_ee(t_ev, 1e19) - 1.0 == pytest.approx(expected, abs=1e-9)


def test_ee_deviation_grows_with_density_so_it_is_computed_per_sample():
    """A fixed percentage would be wrong: the same offset spans ~+33% to ~+99% at 0.1 eV."""
    expected = {1e17: 0.3260, 1e19: 0.4899, 1e21: 0.9854}
    for density, ratio in expected.items():
        deviation = _quantum_ee(0.1, density) / _nrl_ee(0.1, density) - 1.0
        assert deviation == pytest.approx(ratio, abs=5e-4)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        calculate_log_lambda_ee(1e-4, 1e21)  # 0.1 eV at high density
    message = str(_applicability(caught)[0].message)
    assert "n_e = 1e+21 m^-3" in message


def test_ei_message_states_its_own_branches_and_units():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        calculate_log_lambda_ei(0.005, 1e19)
    message = str(_applicability(caught)[0].message)
    assert "23 - ln(sqrt(n_e) Z T_e^(-1.5))" in message
    assert "T_e in eV" in message and "n_e in cm^-3" in message
    assert "algebraic extrapolation" in message


def test_ei_deviation_against_its_own_low_temperature_branch_at_the_issue_anchors():
    anchors = {0.1: 0.5554, 1.0: 0.1733}
    for t_ev, expected in anchors.items():
        deviation = _quantum_ei(t_ev, 1e19) / _nrl_ei_low(t_ev, 1e19) - 1.0
        assert deviation == pytest.approx(expected, abs=5e-4)


def test_ei_intersection_with_the_extended_low_temperature_form_is_about_16_ev():
    """The ~16.2 eV crossing is algebra on an extrapolated branch, not a physical switch."""
    low, high = 1.0, 100.0
    for _ in range(200):
        mid = math.sqrt(low * high)
        if _quantum_ei(mid, 1e19) - _nrl_ei_low(mid, 1e19) > 0:
            low = mid
        else:
            high = mid
    assert math.sqrt(low * high) == pytest.approx(16.2, abs=0.1)


def test_ion_ion_form_never_warns_on_the_electron_boundary():
    """``ii`` already uses the classical cutoff branch, so the electron boundary does not apply."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        calculate_log_lambda_ii(1e-4, 1e19, 1.0)
    assert caught == []
