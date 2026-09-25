"""Bounded historical replay against the saved KN1DPy implementation, when present.

The saved operator bundle ``KN1DPy-631d0bf1/operators/原子氢JH-r系数B样条评价``
sits in the re-review archive: KN1DPy's strict D1 qualification has been
withdrawn, so this replay is bounded historical development evidence about
the arithmetic, not qualified-L1 provenance and not expert approval.  The
tests are skipped unless ``SCIREL_KN1DPY_REVIEW_ROOT`` points at the bundle
root, and the saved implementation file is pinned by SHA-256 so a different
byte stream can never masquerade as the compared arm.
"""
from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path

import numpy as np
import pytest

from scirel.collisions import evaluate_h_jh_alpha_coefficient

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
    spec = importlib.util.spec_from_file_location("kn1dpy_jh_bscoef_alpha", source)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_saved_alpha_branch_is_reproduced_exactly_on_the_packaged_payload():
    source = _source_operator()
    payload = source.produce_jh_coefficient_payload()
    density = np.array([1.0e19, 5.0e19, 1.0e20, 2.0e21])
    temperature = np.array([1.0, 5.0, 20.0, 100.0])
    np.testing.assert_array_equal(
        evaluate_h_jh_alpha_coefficient(density, temperature, payload),
        source.evaluate_h_jh_alpha_coefficient(density, temperature, payload),
    )


def test_the_saved_alpha_branch_is_reproduced_exactly_on_a_longer_profile():
    source = _source_operator()
    payload = source.produce_jh_coefficient_payload()
    density = np.logspace(18, 22, 12)
    temperature = np.logspace(0, 2, 12)
    np.testing.assert_array_equal(
        evaluate_h_jh_alpha_coefficient(density, temperature, payload),
        source.evaluate_h_jh_alpha_coefficient(density, temperature, payload),
    )


def test_the_saved_density_overwrite_and_input_immutability_witnesses_are_reproduced():
    source = _source_operator()
    payload = source.produce_jh_coefficient_payload()
    density = np.array([np.exp(30.0), 1.0e10])
    temperature = np.array([np.exp(0.5), np.exp(0.5)])
    density_copy = density.copy()
    source.evaluate_h_jh_alpha_coefficient(density, temperature, payload)
    np.testing.assert_array_equal(density, density_copy)
    np.testing.assert_array_equal(
        evaluate_h_jh_alpha_coefficient(density, temperature, payload),
        evaluate_h_jh_alpha_coefficient(np.array([np.exp(32.0), 1.0e20]), temperature, payload),
    )
    np.testing.assert_array_equal(
        source.evaluate_h_jh_alpha_coefficient(density, temperature, payload),
        source.evaluate_h_jh_alpha_coefficient(np.array([np.exp(32.0), 1.0e20]), temperature, payload),
    )


def test_the_saved_rejection_behavior_agrees_exactly():
    source = _source_operator()
    payload = source.produce_jh_coefficient_payload()
    with pytest.raises(ValueError):
        evaluate_h_jh_alpha_coefficient(np.array([np.exp(31.0)]), np.array([np.exp(0.5)]), payload, no_null=2)
    with pytest.raises(ValueError):
        source.evaluate_h_jh_alpha_coefficient(np.array([np.exp(31.0)]), np.array([np.exp(0.5)]), payload, no_null=2)
    with pytest.raises(ValueError):
        evaluate_h_jh_alpha_coefficient(np.array([-1.0]), np.array([np.exp(0.5)]), payload)
    with pytest.raises(ValueError):
        source.evaluate_h_jh_alpha_coefficient(np.array([-1.0]), np.array([np.exp(0.5)]), payload)
    with pytest.raises(ValueError):
        evaluate_h_jh_alpha_coefficient(np.array([np.exp(31.0)]), np.array([np.exp(0.5)]), {"order": 5})
    with pytest.raises(ValueError):
        source.evaluate_h_jh_alpha_coefficient(np.array([np.exp(31.0)]), np.array([np.exp(0.5)]), {"order": 5})
