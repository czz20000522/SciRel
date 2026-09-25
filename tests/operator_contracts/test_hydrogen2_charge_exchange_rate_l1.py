"""Bounded historical replay against the saved KN1DPy implementation, when present.

The saved operator bundle ``KN1DPy-631d0bf1/operators/分子氢电荷交换Maxwellian速率系数``
sits in the re-review archive: KN1DPy's strict D1 qualification has been
withdrawn, so this replay is bounded historical development evidence about the
arithmetic, not qualified-L1 provenance and not expert approval.  The tests
are skipped unless ``SCIREL_KN1DPY_REVIEW_ROOT`` points at the bundle root,
and the saved implementation file is pinned by SHA-256 so a different byte
stream can never masquerade as the compared arm.
"""
from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path

import numpy as np
import pytest

from scirel.collisions import evaluate_hydrogen2_charge_exchange_rate

SOURCE_OPERATOR_SHA256 = "8ca54201138f6d1d19803e2bfb042b80980b2a9367bad36d53eafccdfc6bfd22"


def _source_operator():
    root = os.environ.get("SCIREL_KN1DPY_REVIEW_ROOT")
    if not root:
        pytest.skip(
            "SCIREL_KN1DPY_REVIEW_ROOT is not set; source-free contract tests remain active"
        )
    source = Path(root) / "operators" / "分子氢电荷交换Maxwellian速率系数" / "scientific_operator.py"
    assert source.is_file(), f"saved operator bundle missing: {source}"
    assert (
        hashlib.sha256(source.read_bytes()).hexdigest() == SOURCE_OPERATOR_SHA256
    ), f"saved operator bytes drifted from the compared arm: {source}"
    spec = importlib.util.spec_from_file_location("kn1dpy_h2_cx_rate", source)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_saved_bivariate_fit_is_reproduced_exactly():
    source = _source_operator()
    temperature = np.array([0.1, 0.3, 1.0, 5.0, 50.0, 500.0, 5.0e3, 2.01e4, 4.0e4])
    energy = np.array([0.15, 0.7, 3.0, 30.0, 300.0, 3.0e3, 2.01e4, 1.0, 6.0e4])
    np.testing.assert_array_equal(
        evaluate_hydrogen2_charge_exchange_rate(temperature, energy),
        source.evaluate_hydrogen2_charge_exchange_rate(temperature, energy),
    )


def test_the_saved_two_dimensional_profile_is_reproduced_exactly():
    source = _source_operator()
    temperature = np.logspace(0, 3, 12).reshape(4, 3)
    energy = np.logspace(-1, 3, 12).reshape(4, 3)
    np.testing.assert_array_equal(
        evaluate_hydrogen2_charge_exchange_rate(temperature, energy),
        source.evaluate_hydrogen2_charge_exchange_rate(temperature, energy),
    )


def test_the_saved_implementation_accepts_a_nonpositive_temperature_this_asset_rejects():
    """The documented repair: the saved implementation clipped it into the fit."""
    source = _source_operator()
    saved = source.evaluate_hydrogen2_charge_exchange_rate(np.array([-5.0]), np.array([1.0]))
    np.testing.assert_allclose(
        saved,
        source.evaluate_hydrogen2_charge_exchange_rate(np.array([0.1]), np.array([1.0])),
        rtol=0.0,
        atol=0.0,
    )
    with pytest.raises(ValueError):
        evaluate_hydrogen2_charge_exchange_rate(np.array([-5.0]), np.array([1.0]))


def test_the_saved_implementation_accepts_a_negative_energy_this_asset_rejects():
    """The documented repair: the saved implementation clipped it into the fit."""
    source = _source_operator()
    saved = source.evaluate_hydrogen2_charge_exchange_rate(np.array([2.0]), np.array([-1.0]))
    np.testing.assert_allclose(
        saved,
        source.evaluate_hydrogen2_charge_exchange_rate(np.array([2.0]), np.array([0.1])),
        rtol=0.0,
        atol=0.0,
    )
    with pytest.raises(ValueError):
        evaluate_hydrogen2_charge_exchange_rate(np.array([2.0]), np.array([-1.0]))
