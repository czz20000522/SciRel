"""Bounded historical replay of the r63 transport-step family against the
saved KN1DPy implementations, when present.

The saved operator bundles sit in the re-review archive ``KN1DPy-631d0bf1``:
KN1DPy's strict D1 qualification has been withdrawn, so this replay is
bounded historical development evidence about the arithmetic, not
qualified-L1 provenance and not expert approval.  Skipped unless
``SCIREL_KN1DPY_REVIEW_ROOT`` points at the bundle root; every saved
implementation file is pinned by SHA-256.
"""
from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path

import numpy as np
import pytest

from scirel.kinetic import (
    assemble_neutral_boltzmann_rhs,
    assemble_neutral_upwind_transport_coefficients,
    propagate_neutral_generation,
)

_PINNED = {
    "中性代际空间传播": "9d24a06959b37deaa142857bf75bb545c1bedcdbd9ec54f721c62387698c1a13",
    "中性上风空间推进系数": "b7b2979415f82d64fb9f963d1c6e531a9ff6353b8d93e209d3370b34db721bf2",
    "中性BoltzmannRHS组装": "fc47ee0a4c5ad0668844cc0ca30bf6ba4b3fc3530e8ca393e60642d8cf9e95fa",
}

_LOADED = {}


def _saved(package):
    root = os.environ.get("SCIREL_KN1DPY_REVIEW_ROOT")
    if not root:
        pytest.skip("SCIREL_KN1DPY_REVIEW_ROOT is not set; source-free contract tests remain active")
    if package in _LOADED:
        return _LOADED[package]
    source = Path(root) / "operators" / package / "scientific_operator.py"
    assert source.is_file(), f"saved operator bundle missing: {source}"
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    assert digest == _PINNED[package], f"saved operator bytes drifted from the compared arm: {source}"
    spec = importlib.util.spec_from_file_location(f"kn1dpy_r63_{len(_LOADED)}", source)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _LOADED[package] = module
    return module


def _fixture(seed=81):
    rng = np.random.default_rng(seed)
    vr = np.linspace(0.5, 1.5, 2)
    vx = np.array([-1.5, -0.5, 0.5, 1.5])
    x = np.linspace(0.0, 1.0, 5)
    alpha = rng.uniform(0.1, 1.0, (2, 4, 5))
    source = rng.uniform(0.0, 1.0, (2, 4, 5))
    return rng, vr, vx, x, alpha, source


def test_upwind_coefficients_match_the_saved_implementation_bit_for_bit():
    saved = _saved("中性上风空间推进系数")
    _, vr, vx, x, alpha, source = _fixture()
    saved_result = saved.assemble_neutral_upwind_transport_coefficients(x, vx, alpha, source)
    port_result = assemble_neutral_upwind_transport_coefficients(x, vx, alpha, source)
    assert set(saved_result) == set(port_result)
    for key in saved_result:
        np.testing.assert_array_equal(saved_result[key], port_result[key])


def test_propagation_matches_the_saved_implementation_bit_for_bit():
    saved = _saved("中性代际空间传播")
    _, vr, vx, x, alpha, source = _fixture()
    coeffs = assemble_neutral_upwind_transport_coefficients(x, vx, alpha, source)
    boundary = np.ones((alpha.shape[0], alpha.shape[1]))
    for kind, kw in (
        ("first_flight", {"incoming_boundary": boundary}),
        ("scattered", {"scattered_source_distribution": source}),
    ):
        saved_gen = saved.propagate_neutral_generation(
            vx, coeffs["Ak"], coeffs["Bk"], coeffs["Fk"],
            coeffs["Ck"], coeffs["Dk"], coeffs["Gk"], generation_kind=kind, **kw
        )
        port_gen = propagate_neutral_generation(
            vx, coeffs["Ak"], coeffs["Bk"], coeffs["Fk"],
            coeffs["Ck"], coeffs["Dk"], coeffs["Gk"], generation_kind=kind, **kw
        )
        np.testing.assert_array_equal(saved_gen, port_gen)


def test_boltzmann_rhs_matches_the_saved_implementation_bit_for_bit():
    saved = _saved("中性BoltzmannRHS组装")
    rng = np.random.default_rng(82)
    shape = (2, 3, 4)
    vth = 5000.0
    args = tuple(rng.uniform(-1.0, 1.0, shape) for _ in range(6))
    saved_result = saved.assemble_neutral_boltzmann_rhs(vth, *args)
    port_result = assemble_neutral_boltzmann_rhs(vth, *args)
    np.testing.assert_array_equal(saved_result["rhs"], port_result["rhs"])


def test_the_saved_rejection_behavior_agrees_exactly():
    saved_prop = _saved("中性代际空间传播")
    saved_upwind = _saved("中性上风空间推进系数")
    saved_rhs = _saved("中性BoltzmannRHS组装")
    _, vr, vx, x, alpha, source = _fixture()
    coeffs = assemble_neutral_upwind_transport_coefficients(x, vx, alpha, source)
    with pytest.raises(ValueError):
        saved_upwind.assemble_neutral_upwind_transport_coefficients(
            np.array([0.0]), vx, alpha, source
        )
    with pytest.raises(ValueError):
        assemble_neutral_upwind_transport_coefficients(np.array([0.0]), vx, alpha, source)
    with pytest.raises(ValueError):
        saved_prop.propagate_neutral_generation(
            vx, coeffs["Ak"], coeffs["Bk"], coeffs["Fk"],
            coeffs["Ck"], coeffs["Dk"], coeffs["Gk"], generation_kind="invalid"
        )
    with pytest.raises(ValueError):
        propagate_neutral_generation(
            vx, coeffs["Ak"], coeffs["Bk"], coeffs["Fk"],
            coeffs["Ck"], coeffs["Dk"], coeffs["Gk"], generation_kind="invalid"
        )
    ones = np.ones((2, 4, 5))
    with pytest.raises(ValueError):
        saved_rhs.assemble_neutral_boltzmann_rhs(float("nan"), ones, ones, ones, ones, ones, ones)
    with pytest.raises(ValueError):
        assemble_neutral_boltzmann_rhs(float("nan"), ones, ones, ones, ones, ones, ones)
