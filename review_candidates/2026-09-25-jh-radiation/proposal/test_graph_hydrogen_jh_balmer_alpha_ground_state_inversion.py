"""Direct contract tests for the Balmer-alpha ground-state inversion task
graph ``scirel.diagnostics.hydrogen-jh-balmer-alpha-ground-state-inversion``.

The saved KN1DPy package (source anchor
``KN1DPy/jh_related/N0_from_balmer_alpha.py:12-70`` as recorded by the saved
bundle's extraction report) inverts an observed Balmer-alpha volumetric
emissivity into the ground-state neutral density and the ionization /
recombination / net-source terms, consuming the JH r (levels 3), s, alpha
coefficients and the Saha populations of the levels 1 and 3.

The tests re-verify the composition against an independent recomputation
from the bound SciRel assets, the round-trip recovery of a known neutral
density through the forward Balmer-alpha emission graph, the s/alpha
density-semantics split carrying into the returned source terms, and the
composed-domain fail-closed rejections.  No repair is claimed.
"""
from __future__ import annotations

import numpy as np
import pytest
from scipy.interpolate import RectBivariateSpline

from scirel.collisions import evaluate_h_jh_alpha_coefficient, evaluate_h_jh_s_coefficient
from scirel.diagnostics import (
    solve_hydrogen_jh_balmer_alpha_emission,
    solve_hydrogen_jh_balmer_alpha_ground_state_inversion,
)
from scirel.diagnostics.hydrogen_jh_balmer_alpha_ground_state_inversion import run_graph
from scirel.kinetic import evaluate_h_saha_equilibrium_population
from scirel.collisions import evaluate_h_jh_r_coefficient
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


def test_inversion_reproduces_independent_recomputation_and_round_trips_n0():
    payload = make_jh_payload()
    inputs = _profile(payload)
    forward = solve_hydrogen_jh_balmer_alpha_emission(inputs=inputs)
    result = solve_hydrogen_jh_balmer_alpha_ground_state_inversion(
        inputs={
            "balmer_alpha_w_m3": forward["emissivity_w_m3"],
            "density_m3": inputs["density_m3"],
            "temperature_ev": inputs["temperature_ev"],
            "jh_payload": payload,
        }
    )
    expected_keys = {
        "ground_state_density_m3",
        "photon_rate_m3_s",
        "n3_population_m3",
        "ionization_rate_m3_s",
        "recombination_rate_m3_s",
        "net_source_m3_s",
    }
    assert set(result) == expected_keys
    np.testing.assert_allclose(
        result["ground_state_density_m3"], inputs["n0_m3"], rtol=1.0e-12, atol=1.0e3
    )
    density = inputs["density_m3"]
    temperature = inputs["temperature_ev"]
    r03 = evaluate_h_jh_r_coefficient(
        density, temperature, 0, 3, payload["DKnot"], payload["TKnot"], int(payload["order"]), payload["LogR_BSCoef"]
    )
    r13 = evaluate_h_jh_r_coefficient(
        density, temperature, 1, 3, payload["DKnot"], payload["TKnot"], int(payload["order"]), payload["LogR_BSCoef"]
    )
    saha1 = evaluate_h_saha_equilibrium_population(density, temperature, 1)
    saha3 = evaluate_h_saha_equilibrium_population(density, temperature, 3)
    s_rate = evaluate_h_jh_s_coefficient(density, temperature, payload)
    alpha_rate = evaluate_h_jh_alpha_coefficient(density, temperature, payload)
    expected_photon = forward["emissivity_w_m3"] / ((13.6057 * (0.25 - 1.0 / 9.0)) * 1.602177e-19)
    np.testing.assert_array_equal(result["photon_rate_m3_s"], expected_photon)
    expected_n3 = expected_photon / np.asarray(payload["A_Balmer"], dtype=float)[0]
    np.testing.assert_array_equal(result["n3_population_m3"], expected_n3)
    expected_n0 = (expected_n3 / saha3 - r03) * saha1 / r13
    np.testing.assert_array_equal(result["ground_state_density_m3"], expected_n0)
    expected_ionization = expected_n0 * (density * s_rate)
    expected_recombination = density * (density * alpha_rate)
    np.testing.assert_array_equal(result["ionization_rate_m3_s"], expected_ionization)
    np.testing.assert_array_equal(result["recombination_rate_m3_s"], expected_recombination)
    np.testing.assert_array_equal(result["net_source_m3_s"], expected_ionization - expected_recombination)


def test_source_terms_carry_the_s_alpha_density_semantics_split():
    """The bound alpha coefficient is density-independent (the saved r57
    sentinel behavior), so a density change moves the returned recombination
    only through the explicit ``density * (density * alpha)`` factor -- it
    scales with density squared -- while the ionization term additionally
    carries the density-consuming s branch and the recovered n0."""
    payload = make_jh_payload()
    inputs = _profile(payload)
    forward = solve_hydrogen_jh_balmer_alpha_emission(inputs=inputs)
    kwargs = {
        "balmer_alpha_w_m3": forward["emissivity_w_m3"],
        "density_m3": inputs["density_m3"],
        "temperature_ev": inputs["temperature_ev"],
        "jh_payload": payload,
    }
    base = solve_hydrogen_jh_balmer_alpha_ground_state_inversion(inputs=kwargs)
    shifted = solve_hydrogen_jh_balmer_alpha_ground_state_inversion(
        inputs={**kwargs, "density_m3": inputs["density_m3"] * 10.0}
    )
    assert not np.array_equal(base["ionization_rate_m3_s"], shifted["ionization_rate_m3_s"])
    assert not np.array_equal(base["net_source_m3_s"], shifted["net_source_m3_s"])
    np.testing.assert_allclose(
        shifted["recombination_rate_m3_s"], base["recombination_rate_m3_s"] * 100.0, rtol=1.0e-9, atol=0.0
    )
    # the alpha coefficient entering the product is itself density-independent
    alpha_base = evaluate_h_jh_alpha_coefficient(inputs["density_m3"], inputs["temperature_ev"], payload)
    alpha_shifted = evaluate_h_jh_alpha_coefficient(inputs["density_m3"] * 10.0, inputs["temperature_ev"], payload)
    np.testing.assert_array_equal(alpha_base, alpha_shifted)
    # ... while the s coefficient consumes density
    s_base = evaluate_h_jh_s_coefficient(np.array([np.exp(30.5)]), inputs["temperature_ev"][:1], payload)
    s_shifted = evaluate_h_jh_s_coefficient(np.array([np.exp(31.5)]), inputs["temperature_ev"][:1], payload)
    assert not np.array_equal(s_base, s_shifted)


def test_inversion_of_a_biased_emissivity_shifts_the_recovered_n0():
    payload = make_jh_payload()
    inputs = _profile(payload)
    forward = solve_hydrogen_jh_balmer_alpha_emission(inputs=inputs)
    kwargs = {
        "density_m3": inputs["density_m3"],
        "temperature_ev": inputs["temperature_ev"],
        "jh_payload": payload,
    }
    base = solve_hydrogen_jh_balmer_alpha_ground_state_inversion(
        inputs={**kwargs, "balmer_alpha_w_m3": forward["emissivity_w_m3"]}
    )
    biased = solve_hydrogen_jh_balmer_alpha_ground_state_inversion(
        inputs={**kwargs, "balmer_alpha_w_m3": forward["emissivity_w_m3"] * 2.0}
    )
    assert not np.array_equal(base["ground_state_density_m3"], biased["ground_state_density_m3"])


def test_composed_domain_and_branch_failures_fail_closed():
    payload = make_jh_payload()
    inputs = _profile(payload)
    kwargs = {
        "density_m3": inputs["density_m3"],
        "temperature_ev": inputs["temperature_ev"],
        "jh_payload": payload,
    }
    with pytest.raises(ValueError, match="balmer_alpha_w_m3 must be finite, positive"):
        solve_hydrogen_jh_balmer_alpha_ground_state_inversion(
            inputs={**kwargs, "balmer_alpha_w_m3": np.zeros(3)}
        )
    with pytest.raises(ValueError, match="balmer_alpha_w_m3 must be finite, positive"):
        solve_hydrogen_jh_balmer_alpha_ground_state_inversion(
            inputs={**kwargs, "balmer_alpha_w_m3": np.array([-1.0, 1.0, 1.0])}
        )
    with pytest.raises(ValueError, match="1e32"):
        solve_hydrogen_jh_balmer_alpha_ground_state_inversion(
            inputs={**kwargs, "balmer_alpha_w_m3": np.ones(3), "temperature_ev": np.array([5.0, 30.0, 2.0e32])}
        )
    with pytest.raises(ValueError, match="no_null=1"):
        solve_hydrogen_jh_balmer_alpha_ground_state_inversion(
            inputs={**kwargs, "balmer_alpha_w_m3": np.ones(3), "no_null": 0}
        )
    with pytest.raises(ValueError, match="missing balmer_alpha_w_m3"):
        solve_hydrogen_jh_balmer_alpha_ground_state_inversion(inputs=kwargs)
    # pre-review regression: an unused field may not be dropped either -- the
    # saved composition validates the exact eight-field set on every branch
    missing_a_lyman = {key: value for key, value in payload.items() if key != "A_Lyman"}
    with pytest.raises(ValueError, match="fields are incomplete"):
        solve_hydrogen_jh_balmer_alpha_ground_state_inversion(
            inputs={**kwargs, "balmer_alpha_w_m3": np.ones(3), "jh_payload": missing_a_lyman}
        )
    extra = dict(payload)
    extra["unexpected"] = 1.0
    with pytest.raises(ValueError, match="fields are incomplete"):
        solve_hydrogen_jh_balmer_alpha_ground_state_inversion(
            inputs={**kwargs, "balmer_alpha_w_m3": np.ones(3), "jh_payload": extra}
        )
    with pytest.raises(ValueError, match="finite positive same-shaped 1-D"):
        solve_hydrogen_jh_balmer_alpha_ground_state_inversion(
            inputs={**kwargs, "balmer_alpha_w_m3": np.array([[1.0]]), "density_m3": np.array([[1.0e20]])}
        )


def test_run_graph_resolves_assets_through_the_declared_asset_loader():
    payload = make_jh_payload()
    inputs = _profile(payload)
    forward = solve_hydrogen_jh_balmer_alpha_emission(inputs=inputs)
    inversion_inputs = {
        "balmer_alpha_w_m3": forward["emissivity_w_m3"],
        "density_m3": inputs["density_m3"],
        "temperature_ev": inputs["temperature_ev"],
        "jh_payload": payload,
    }
    direct = run_graph(inversion_inputs, asset_loader=_load_asset)
    wrapped = solve_hydrogen_jh_balmer_alpha_ground_state_inversion(inputs=inversion_inputs)
    np.testing.assert_array_equal(direct["ground_state_density_m3"], wrapped["ground_state_density_m3"])
