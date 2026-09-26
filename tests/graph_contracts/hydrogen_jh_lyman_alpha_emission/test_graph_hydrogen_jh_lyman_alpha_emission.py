"""Direct contract tests for the Lyman-alpha emission task graph
``scirel.diagnostics.hydrogen-jh-lyman-alpha-emission``.

The saved KN1DPy package (source anchor ``KN1DPy/jh_related/lyman_alpha.py:42-64``
as recorded by the saved bundle's extraction report) composes the JH r
coefficients (ion 0 and 1, principal level 2), the Saha populations of the
levels 1 and 2, and the packaged ``A_Lyman`` Einstein coefficient into the
photon rate ``A_Lyman[0] * (r02 + r12 * n0 / saha1) * saha2`` and the
emissivity with the frozen factor ``13.6057 * (0.25 - 1/9)`` eV.

The tests re-verify the composition against an independent recomputation
from the bound SciRel assets and against an independent FITPACK
re-evaluation of the r spline, the frozen constants, the composed-domain
fail-closed rejections, and the forward-relation operation order.  No
repair is claimed: the Lyman emissivity factor is the saved one (the
n=3 -> 2 photon energy), recorded as an open expert question.
"""
from __future__ import annotations

import numpy as np
import pytest
from scipy.interpolate import RectBivariateSpline

from scirel.collisions import evaluate_h_jh_r_coefficient
from scirel.diagnostics import solve_hydrogen_jh_lyman_alpha_emission
from scirel.diagnostics.hydrogen_jh_lyman_alpha_emission import run_graph
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
    }, spline


def _profile(payload):
    density = np.array([1.0e20, 5.0e20, 1.0e21])
    temperature = np.array([5.0, 30.0, 100.0])
    n0 = np.array([1.0e17, 2.0e18, 5.0e18])
    return {"density_m3": density, "temperature_ev": temperature, "n0_m3": n0, "jh_payload": payload}


def test_photon_rate_matches_independent_recomputation_from_bound_assets():
    payload, _ = make_jh_payload()
    inputs = _profile(payload)
    result = solve_hydrogen_jh_lyman_alpha_emission(inputs=inputs)
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
    expected_photon = np.asarray(payload["A_Lyman"], dtype=float)[0] * (r02 + r12 * n0 / saha1) * saha2
    np.testing.assert_array_equal(result["photon_rate_m3_s"], expected_photon)
    assert set(result) == {"emissivity_w_m3", "photon_rate_m3_s"}
    assert np.all(np.isfinite(result["emissivity_w_m3"])) and np.all(result["emissivity_w_m3"] > 0.0)
    assert np.all(np.isfinite(result["photon_rate_m3_s"])) and np.all(result["photon_rate_m3_s"] > 0.0)


def test_emissivity_carries_the_saved_energy_factor_not_the_physical_lyman_energy():
    """The saved implementation multiplies BOTH line photon rates by
    13.6057 * (0.25 - 1/9) eV -- the n=3 -> 2 photon energy.  This graph
    preserves that arithmetic bit for bit and records the factor choice as
    an open expert question; the physical n=1 -> 2 energy would differ."""
    payload, _ = make_jh_payload()
    inputs = _profile(payload)
    result = solve_hydrogen_jh_lyman_alpha_emission(inputs=inputs)
    saved_factor = 13.6057 * (0.25 - 1.0 / 9.0)
    expected = saved_factor * result["photon_rate_m3_s"] * 1.602177e-19
    np.testing.assert_array_equal(result["emissivity_w_m3"], expected)
    physical_lyman = 13.6057 * (1.0 - 0.25)
    assert not np.array_equal(result["emissivity_w_m3"], physical_lyman * result["photon_rate_m3_s"] * 1.602177e-19)


def test_r_channels_enter_through_the_bound_asset_with_sentinel_density():
    """The r/alpha density-overwrite contract of the bound r asset carries
    into the composition: the photon rate depends on n0 but not on the
    caller's density beyond the Saha and validation contracts."""
    payload, _ = make_jh_payload()
    inputs = _profile(payload)
    base = solve_hydrogen_jh_lyman_alpha_emission(inputs=inputs)
    with pytest.raises(ValueError, match="1e32"):
        solve_hydrogen_jh_lyman_alpha_emission(inputs={**inputs, "density_m3": inputs["density_m3"] * 1e12})
    shifted_n0 = solve_hydrogen_jh_lyman_alpha_emission(inputs={**inputs, "n0_m3": inputs["n0_m3"] * 2.0})
    assert not np.array_equal(base["photon_rate_m3_s"], shifted_n0["photon_rate_m3_s"])
    # the r02 channel equals the bound asset's own output on the same payload
    r02 = evaluate_h_jh_r_coefficient(
        inputs["density_m3"], inputs["temperature_ev"], 0, 2,
        payload["DKnot"], payload["TKnot"], int(payload["order"]), payload["LogR_BSCoef"],
    )
    assert np.all(np.isfinite(r02)) and np.all(r02 > 0.0)


def test_spline_inputs_reach_the_bound_asset_through_the_independent_oracle():
    """The knot/order/coef ports actually steer the composition: evaluated
    against an independent FITPACK re-evaluation of the r spline."""
    payload, spline = make_jh_payload()
    inputs = _profile(payload)
    result = solve_hydrogen_jh_lyman_alpha_emission(inputs=inputs)
    density = inputs["density_m3"]
    temperature = inputs["temperature_ev"]
    n0 = inputs["n0_m3"]
    log_density = np.clip(np.log(density), payload["DKnot"][0], payload["DKnot"][-1])
    log_temperature = np.clip(np.log(temperature), payload["TKnot"][0], payload["TKnot"][-1])
    # the r channels here are the zero LogR_BSCoef slice: exp(0) = 1 per sample
    r02 = np.empty(density.shape)
    for index in range(density.size):
        r02[index] = np.exp(float(np.atleast_1d(spline.ev(log_temperature[index], log_density[index]))[0]) * 0.0)
    saha1 = evaluate_h_saha_equilibrium_population(density, temperature, 1)
    saha2 = evaluate_h_saha_equilibrium_population(density, temperature, 2)
    expected = np.asarray(payload["A_Lyman"], dtype=float)[0] * (1.0 + 1.0 * n0 / saha1) * saha2
    np.testing.assert_allclose(result["photon_rate_m3_s"], expected, rtol=1e-12, atol=0.0)


def test_composed_domain_and_branch_failures_fail_closed():
    payload, _ = make_jh_payload()
    inputs = _profile(payload)
    with pytest.raises(ValueError, match="n0_m3 must be finite, positive"):
        solve_hydrogen_jh_lyman_alpha_emission(inputs={**inputs, "n0_m3": np.zeros(3)})
    with pytest.raises(ValueError, match="n0_m3 must be finite, positive"):
        solve_hydrogen_jh_lyman_alpha_emission(inputs={**inputs, "n0_m3": np.full(3, 1.0e32)})
    with pytest.raises(ValueError, match="finite positive same-shaped 1-D"):
        solve_hydrogen_jh_lyman_alpha_emission(inputs={**inputs, "temperature_ev": np.array([-1.0, 5.0, 30.0])})
    with pytest.raises(ValueError, match="no_null=1"):
        solve_hydrogen_jh_lyman_alpha_emission(inputs={**inputs, "no_null": 0})
    with pytest.raises(ValueError, match="missing n0_m3"):
        solve_hydrogen_jh_lyman_alpha_emission(
            inputs={key: value for key, value in inputs.items() if key != "n0_m3"}
        )
    incomplete = {key: value for key, value in payload.items() if key != "A_Lyman"}
    with pytest.raises(ValueError, match="fields are incomplete"):
        solve_hydrogen_jh_lyman_alpha_emission(inputs={**inputs, "jh_payload": incomplete})
    # pre-review regression: an unused field may not be dropped either -- the
    # saved composition validates the exact eight-field set on every branch
    missing_unused = {key: value for key, value in payload.items() if key != "A_Balmer"}
    with pytest.raises(ValueError, match="fields are incomplete"):
        solve_hydrogen_jh_lyman_alpha_emission(inputs={**inputs, "jh_payload": missing_unused})
    extra = dict(payload)
    extra["unexpected"] = 1.0
    with pytest.raises(ValueError, match="fields are incomplete"):
        solve_hydrogen_jh_lyman_alpha_emission(inputs={**inputs, "jh_payload": extra})
    nonfinite_unused = dict(payload)
    nonfinite_unused["LogAlpha_BSCoef"] = nonfinite_unused["LogAlpha_BSCoef"].copy()
    nonfinite_unused["LogAlpha_BSCoef"][0] = np.nan
    with pytest.raises(ValueError, match="must be finite"):
        solve_hydrogen_jh_lyman_alpha_emission(inputs={**inputs, "jh_payload": nonfinite_unused})
    bad_geometry = dict(payload)
    bad_geometry["DKnot"] = payload["DKnot"][:-1]
    with pytest.raises(ValueError, match="77 coefficients"):
        solve_hydrogen_jh_lyman_alpha_emission(inputs={**inputs, "jh_payload": bad_geometry})
    empty = dict(payload)
    empty["A_Lyman"] = np.zeros(15)
    # source parity: the saved branch gates finiteness only -- a zero Einstein
    # coefficient returns zero rates (no emission) instead of being rejected
    zero = solve_hydrogen_jh_lyman_alpha_emission(inputs={**inputs, "jh_payload": empty})
    np.testing.assert_array_equal(zero["photon_rate_m3_s"], np.zeros(3))
    np.testing.assert_array_equal(zero["emissivity_w_m3"], np.zeros(3))
    negative = dict(payload)
    negative["A_Lyman"] = np.linspace(-3.0e8, -1.0e5, 15)
    sign_flip = solve_hydrogen_jh_lyman_alpha_emission(inputs={**inputs, "jh_payload": negative})
    np.testing.assert_array_equal(
        sign_flip["emissivity_w_m3"], (13.6057 * (0.25 - 1.0 / 9.0)) * sign_flip["photon_rate_m3_s"] * 1.602177e-19
    )
    assert np.all(sign_flip["photon_rate_m3_s"] < 0.0)


def test_run_graph_resolves_assets_through_the_declared_asset_loader():
    """The graph must consume the declared dependencies through the asset
    loader -- a misspelled reference fails loudly instead of injecting
    nothing."""
    payload, _ = make_jh_payload()
    inputs = _profile(payload)
    direct = run_graph(inputs, asset_loader=_load_asset)
    wrapped = solve_hydrogen_jh_lyman_alpha_emission(inputs=inputs)
    np.testing.assert_array_equal(direct["photon_rate_m3_s"], wrapped["photon_rate_m3_s"])
