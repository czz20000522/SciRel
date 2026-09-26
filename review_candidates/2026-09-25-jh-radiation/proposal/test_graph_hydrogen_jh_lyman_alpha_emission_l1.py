"""Bounded historical replay of the Lyman-alpha emission graph against the
saved KN1DPy implementation, when present.

The saved operator bundle ``KN1DPy-631d0bf1/operators/原子氢JH-r系数B样条评价``
sits in the re-review archive: KN1DPy's strict D1 qualification has been
withdrawn, so this replay is bounded historical development evidence about
the arithmetic, not qualified-L1 provenance and not expert approval.  The
tests are skipped unless ``SCIREL_KN1DPY_REVIEW_ROOT`` points at the bundle
root, and the saved implementation file is pinned by SHA-256 so a different
byte stream can never masquerade as the compared arm.

The replay covers the shared composed domain only: the SciRel graph declares
density and temperature below ``1e32`` (the bound r56 Saha asset's documented
limit), so inputs at or above the limit are a declared divergence, witnessed
separately.
"""
from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path

import numpy as np
import pytest

from scirel.diagnostics import solve_hydrogen_jh_lyman_alpha_emission

SOURCE_OPERATOR_SHA256 = "253cda226c553cd5cd560914a6474b4b3572262b63aad61c76f91df8bafb6344"


def _source_operator():
    root = os.environ.get("SCIREL_KN1DPY_REVIEW_ROOT")
    if not root:
        pytest.skip(
            "SCIREL_KN1DPY_REVIEW_ROOT is not set; source-free contract tests remain active"
        )
    source = Path(root) / "operators" / "原子氢JH-r系数B样条评价" / "scientific_operator.py"
    assert source.is_file(), f"saved operator bundle missing: {source}"
    assert (
        hashlib.sha256(source.read_bytes()).hexdigest() == SOURCE_OPERATOR_SHA256
    ), f"saved operator bytes drifted from the compared arm: {source}"
    spec = importlib.util.spec_from_file_location("kn1dpy_jh_lyman_s", source)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _profiles():
    return (
        (np.array([1.0e16, 1.0e18, 1.0e20]), np.array([1.0, 5.0, 20.0]), np.array([2.0e15, 3.0e16, 4.0e17])),
        (np.logspace(18, 22, 8), np.logspace(0, 2, 8), np.logspace(14, 19, 8)),
        (np.array([5.0e19]), np.array([3.0]), np.array([5.0e15])),
    )


def test_the_saved_lyman_alpha_composition_is_reproduced_bit_for_bit():
    source = _source_operator()
    payload = source.produce_jh_coefficient_payload()
    for density, temperature, n0 in _profiles():
        saved = source.evaluate_lyman_alpha(density, temperature, n0, payload)
        graph = solve_hydrogen_jh_lyman_alpha_emission(
            inputs={"density_m3": density, "temperature_ev": temperature, "n0_m3": n0, "jh_payload": payload}
        )
        np.testing.assert_array_equal(graph["photon_rate_m3_s"], saved["photon_rate_m3_s"])
        np.testing.assert_array_equal(graph["emissivity_w_m3"], saved["emissivity_w_m3"])


def test_the_saved_rejection_behavior_agrees_exactly():
    source = _source_operator()
    payload = source.produce_jh_coefficient_payload()
    density = np.array([np.exp(31.0)])
    temperature = np.array([np.exp(0.5)])
    n0 = np.array([np.exp(16.0)])
    inputs = {"density_m3": density, "temperature_ev": temperature, "n0_m3": n0, "jh_payload": payload}
    for mutated in (
        {**inputs, "n0_m3": np.array([0.0])},
        {**inputs, "n0_m3": np.array([1.0e32])},
        {**inputs, "temperature_ev": np.array([-1.0])},
        {**inputs, "no_null": 0},
    ):
        with pytest.raises(ValueError):
            source.evaluate_lyman_alpha(
                mutated["density_m3"], mutated["temperature_ev"], mutated["n0_m3"],
                mutated["jh_payload"], no_null=mutated.get("no_null", 1),
            )
        with pytest.raises(ValueError):
            solve_hydrogen_jh_lyman_alpha_emission(inputs=mutated)
    # a payload with an incomplete field set fails closed on both arms
    with pytest.raises(ValueError):
        source.evaluate_lyman_alpha(density, temperature, n0, {"DKnot": payload["DKnot"]})
    with pytest.raises(ValueError):
        solve_hydrogen_jh_lyman_alpha_emission(
            inputs={**inputs, "jh_payload": {"DKnot": payload["DKnot"]}}
        )
    # pre-review regression counterexample: dropping a field the Lyman branch
    # does not numerically consume must still fail closed on both arms
    missing_unused = {key: value for key, value in payload.items() if key != "A_Balmer"}
    with pytest.raises(ValueError):
        source.evaluate_lyman_alpha(density, temperature, n0, missing_unused)
    with pytest.raises(ValueError):
        solve_hydrogen_jh_lyman_alpha_emission(inputs={**inputs, "jh_payload": missing_unused})


def test_the_declared_composed_domain_narrows_the_saved_composition_above_1e32():
    """Declared divergence: the saved composition admits electron densities
    at or above 1e32 (only n0 is bounded by the saved contract); this graph
    fails closed there because the bound r56 Saha asset enforces its
    documented < 1e32 domain.  On the shared domain the outputs are
    bit-identical (the dedicated replay above)."""
    source = _source_operator()
    payload = source.produce_jh_coefficient_payload()
    saved = source.evaluate_lyman_alpha(np.array([2.0e32]), np.array([5.0]), np.array([1.0e18]), payload)
    assert np.all(np.isfinite(saved["photon_rate_m3_s"]))
    with pytest.raises(ValueError, match="1e32"):
        solve_hydrogen_jh_lyman_alpha_emission(
            inputs={
                "density_m3": np.array([2.0e32]),
                "temperature_ev": np.array([5.0]),
                "n0_m3": np.array([1.0e18]),
                "jh_payload": payload,
            }
        )

def test_a_zero_einstein_coefficient_returns_zero_rates_on_both_arms():
    """Pre-review parity regression: the saved payload validation checks the
    finiteness of A_Lyman only, so A_Lyman[0] = 0 returns zero photon rate and
    emissivity on the saved arm; this graph keeps the identical semantics."""
    source = _source_operator()
    payload = source.produce_jh_coefficient_payload()
    zero_payload = dict(payload)
    zero_payload["A_Lyman"] = np.zeros_like(payload["A_Lyman"])
    density = np.array([1.0e19, 1.0e20])
    temperature = np.array([2.0, 10.0])
    n0 = np.array([1.0e17, 1.0e18])
    saved = source.evaluate_lyman_alpha(density, temperature, n0, zero_payload)
    graph = solve_hydrogen_jh_lyman_alpha_emission(
        inputs={"density_m3": density, "temperature_ev": temperature, "n0_m3": n0, "jh_payload": zero_payload}
    )
    np.testing.assert_array_equal(graph["photon_rate_m3_s"], saved["photon_rate_m3_s"])
    np.testing.assert_array_equal(graph["photon_rate_m3_s"], np.zeros(2))
    np.testing.assert_array_equal(graph["emissivity_w_m3"], saved["emissivity_w_m3"])
