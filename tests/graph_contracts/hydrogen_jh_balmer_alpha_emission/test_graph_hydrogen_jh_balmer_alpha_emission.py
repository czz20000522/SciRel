"""Direct contract tests for the Balmer-alpha emission task graph
``scirel.diagnostics.hydrogen-jh-balmer-alpha-emission``.

The saved KN1DPy package (source anchor ``KN1DPy/jh_related/balmer_alpha.py:40-64``
as recorded by the saved bundle's extraction report) composes the JH r
coefficients (ion 0 and 1, principal level 3), the Saha populations of the
levels 1 and 3, and the packaged ``A_Balmer`` Einstein coefficient into the
photon rate ``A_Balmer[0] * (r03 + r13 * n0 / saha1) * saha3`` and the
emissivity with the frozen factor ``13.6057 * (0.25 - 1/9)`` eV.

The tests re-verify the composition against an independent recomputation
from the bound SciRel assets, the level-3 channel selection, the frozen
constants, and the composed-domain fail-closed rejections.  No repair is
claimed.
"""
from __future__ import annotations

import numpy as np
import pytest
from scipy.interpolate import RectBivariateSpline

from scirel.collisions import evaluate_h_jh_r_coefficient
from scirel.diagnostics import solve_hydrogen_jh_balmer_alpha_emission
from scirel.diagnostics.hydrogen_jh_balmer_alpha_emission import run_graph
from scirel.kinetic import evaluate_h_saha_equilibrium_population
from _review_bindings import load_asset as _load_asset


def make_jh_payload():
    """Synthetic payload with the exact saved field set, the saved knot
    geometry (order field 4, 77 coefficients via an 11-point temperature
    axis and a 7-point density axis), and positive Einstein vectors."""
    temperature_axis = np.linspace(-1.0, 1.0, 11)
    density_axis = np.linspace(30.0, 32.0, 7)
    surface = np.add.outer(temperature_axis, density_axis)
    spline = RectBivariateSpline(temperature_axis, density_axis, surface, kx=4, ky=4)
    temperature_knots, density_knots = spline.get_knots()
    coefficients = spline.get_coeffs()
    return {
        "DKnot": density_knots,
        "TKnot": temperature_knots,
        "order": 4,
        "LogR_BSCoef": np.zeros((coefficients.size, 2, 5)),
        "LogS_BSCoef": coefficients.copy(),
        "LogAlpha_BSCoef": coefficients.copy() + 0.25,
        "A_Lyman": np.linspace(3.0e8, 1.0e5, 15),
        "A_Balmer": np.linspace(4.4e7, 2.0e4, 15),
    }


def _profile(payload):
    density = np.array([1.0e20, 5.0e20, 1.0e21])
    temperature = np.array([5.0, 30.0, 100.0])
    n0 = np.array([1.0e17, 2.0e18, 5.0e18])
    return {"density_m3": density, "temperature_ev": temperature, "n0_m3": n0, "jh_payload": payload}


def test_photon_rate_matches_independent_recomputation_from_bound_assets():
    payload = make_jh_payload()
    inputs = _profile(payload)
    result = solve_hydrogen_jh_balmer_alpha_emission(inputs=inputs)
    density = inputs["density_m3"]
    temperature = inputs["temperature_ev"]
    n0 = inputs["n0_m3"]
    r03 = evaluate_h_jh_r_coefficient(
        density, temperature, 0, 3, payload["DKnot"], payload["TKnot"], int(payload["order"]), payload["LogR_BSCoef"]
    )
    r13 = evaluate_h_jh_r_coefficient(
        density, temperature, 1, 3, payload["DKnot"], payload["TKnot"], int(payload["order"]), payload["LogR_BSCoef"]
    )
    saha1 = evaluate_h_saha_equilibrium_population(density, temperature, 1)
    saha3 = evaluate_h_saha_equilibrium_population(density, temperature, 3)
    expected_photon = np.asarray(payload["A_Balmer"], dtype=float)[0] * (r03 + r13 * n0 / saha1) * saha3
    np.testing.assert_array_equal(result["photon_rate_m3_s"], expected_photon)
    expected_emissivity = (13.6057 * (0.25 - 1.0 / 9.0)) * expected_photon * 1.602177e-19
    np.testing.assert_array_equal(result["emissivity_w_m3"], expected_emissivity)
    assert set(result) == {"emissivity_w_m3", "photon_rate_m3_s"}
    assert np.all(np.isfinite(result["emissivity_w_m3"])) and np.all(result["emissivity_w_m3"] > 0.0)


def test_level_3_channels_are_selected_not_the_level_2_channels():
    """The Balmer relation consumes the level-3 r channels and the level-3
    Saha population; substituting the level-2 channels changes the result."""
    payload = make_jh_payload()
    inputs = _profile(payload)
    density = inputs["density_m3"]
    temperature = inputs["temperature_ev"]
    n0 = inputs["n0_m3"]
    r02 = evaluate_h_jh_r_coefficient(
        density, temperature, 0, 2, payload["DKnot"], payload["TKnot"], int(payload["order"]), payload["LogR_BSCoef"]
    )
    r12 = evaluate_h_jh_r_coefficient(
        density, temperature, 1, 2, payload["DKnot"], payload["TKnot"], int(payload["order"]), payload["LogR_BSCoef"]
    )
    saha1 = evaluate_h_saha_equilibrium_population(density, temperature, 1)
    saha2 = evaluate_h_saha_equilibrium_population(density, temperature, 2)
    level2_photon = np.asarray(payload["A_Balmer"], dtype=float)[0] * (r02 + r12 * n0 / saha1) * saha2
    result = solve_hydrogen_jh_balmer_alpha_emission(inputs=inputs)
    assert not np.array_equal(result["photon_rate_m3_s"], level2_photon)


def test_n0_enters_the_photon_rate_and_the_emissivity_keeps_the_saved_factor():
    payload = make_jh_payload()
    inputs = _profile(payload)
    base = solve_hydrogen_jh_balmer_alpha_emission(inputs=inputs)
    doubled = solve_hydrogen_jh_balmer_alpha_emission(inputs={**inputs, "n0_m3": inputs["n0_m3"] * 2.0})
    assert not np.array_equal(base["photon_rate_m3_s"], doubled["photon_rate_m3_s"])
    saved_factor = 13.6057 * (0.25 - 1.0 / 9.0)
    np.testing.assert_array_equal(
        doubled["emissivity_w_m3"], saved_factor * doubled["photon_rate_m3_s"] * 1.602177e-19
    )


def test_composed_domain_and_branch_failures_fail_closed():
    payload = make_jh_payload()
    inputs = _profile(payload)
    with pytest.raises(ValueError, match="n0_m3 must be finite, positive"):
        solve_hydrogen_jh_balmer_alpha_emission(inputs={**inputs, "n0_m3": np.zeros(3)})
    with pytest.raises(ValueError, match="1e32"):
        solve_hydrogen_jh_balmer_alpha_emission(inputs={**inputs, "density_m3": inputs["density_m3"] * 1e12})
    with pytest.raises(ValueError, match="finite positive same-shaped 1-D"):
        solve_hydrogen_jh_balmer_alpha_emission(inputs={**inputs, "temperature_ev": np.array([-1.0, 5.0, 30.0])})
    with pytest.raises(ValueError, match="no_null=1"):
        solve_hydrogen_jh_balmer_alpha_emission(inputs={**inputs, "no_null": 0})
    with pytest.raises(ValueError, match="missing n0_m3"):
        solve_hydrogen_jh_balmer_alpha_emission(
            inputs={key: value for key, value in inputs.items() if key != "n0_m3"}
        )
    empty = dict(payload)
    empty["A_Balmer"] = np.zeros(15)
    # source parity: the saved branch gates finiteness only -- a zero Einstein
    # coefficient returns zero rates (no emission) instead of being rejected
    zero = solve_hydrogen_jh_balmer_alpha_emission(inputs={**inputs, "jh_payload": empty})
    np.testing.assert_array_equal(zero["photon_rate_m3_s"], np.zeros(3))
    np.testing.assert_array_equal(zero["emissivity_w_m3"], np.zeros(3))
    negative = dict(payload)
    negative["A_Balmer"] = np.linspace(-4.4e7, -2.0e4, 15)
    sign_flip = solve_hydrogen_jh_balmer_alpha_emission(inputs={**inputs, "jh_payload": negative})
    np.testing.assert_array_equal(
        sign_flip["emissivity_w_m3"], (13.6057 * (0.25 - 1.0 / 9.0)) * sign_flip["photon_rate_m3_s"] * 1.602177e-19
    )
    assert np.all(sign_flip["photon_rate_m3_s"] < 0.0)
    # pre-review regression: an unused field may not be dropped either -- the
    # saved composition validates the exact eight-field set on every branch
    missing_unused = {key: value for key, value in payload.items() if key != "A_Lyman"}
    with pytest.raises(ValueError, match="fields are incomplete"):
        solve_hydrogen_jh_balmer_alpha_emission(inputs={**inputs, "jh_payload": missing_unused})
    extra = dict(payload)
    extra["unexpected"] = 1.0
    with pytest.raises(ValueError, match="fields are incomplete"):
        solve_hydrogen_jh_balmer_alpha_emission(inputs={**inputs, "jh_payload": extra})
    nonfinite_unused = dict(payload)
    nonfinite_unused["LogAlpha_BSCoef"] = nonfinite_unused["LogAlpha_BSCoef"].copy()
    nonfinite_unused["LogAlpha_BSCoef"][0] = np.nan
    with pytest.raises(ValueError, match="must be finite"):
        solve_hydrogen_jh_balmer_alpha_emission(inputs={**inputs, "jh_payload": nonfinite_unused})
    bad_geometry = dict(payload)
    bad_geometry["DKnot"] = payload["DKnot"][:-1]
    with pytest.raises(ValueError, match="77 coefficients"):
        solve_hydrogen_jh_balmer_alpha_emission(inputs={**inputs, "jh_payload": bad_geometry})


def test_run_graph_resolves_assets_through_the_declared_asset_loader():
    payload = make_jh_payload()
    inputs = _profile(payload)
    direct = run_graph(inputs, asset_loader=_load_asset)
    wrapped = solve_hydrogen_jh_balmer_alpha_emission(inputs=inputs)
    np.testing.assert_array_equal(direct["photon_rate_m3_s"], wrapped["photon_rate_m3_s"])
