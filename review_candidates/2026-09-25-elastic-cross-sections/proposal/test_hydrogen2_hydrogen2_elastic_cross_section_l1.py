"""Bounded historical replay against the saved KN1DPy implementation, when present.

The saved operator bundle ``KN1DPy-631d0bf1/operators/分子氢分子氢弹性动量转移截面`` sits in
the re-review archive: KN1DPy's strict D1 qualification has been withdrawn, so
this replay is bounded historical development evidence about the arithmetic,
not qualified-L1 provenance and not expert approval.  The tests are skipped
unless ``SCIREL_KN1DPY_REVIEW_ROOT`` points at the bundle root, and the saved
implementation file is pinned by SHA-256 so a different byte stream can never
masquerade as the compared arm.
"""
from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path

import numpy as np
import pytest

from scirel.collisions import evaluate_hydrogen2_hydrogen2_elastic_cross_section

SOURCE_OPERATOR_SHA256 = "0c10fbb9364212681e6d8c023b5db707a09b02f73e984948be1d4448e7daccac"


def _source_operator():
    root = os.environ.get("SCIREL_KN1DPY_REVIEW_ROOT")
    if not root:
        pytest.skip(
            "SCIREL_KN1DPY_REVIEW_ROOT is not set; source-free contract tests remain active"
        )
    source = Path(root) / "operators" / "分子氢分子氢弹性动量转移截面" / "scientific_operator.py"
    assert source.is_file(), f"saved operator bundle missing: {source}"
    assert (
        hashlib.sha256(source.read_bytes()).hexdigest() == SOURCE_OPERATOR_SHA256
    ), f"saved operator bytes drifted from the compared arm: {source}"
    spec = importlib.util.spec_from_file_location("kn1dpy_hh_hh_elastic", source)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_saved_fit_is_reproduced_exactly():
    source = _source_operator()
    energy = np.array([0.03, 0.3, 1.0, 7.5, 100.0, 1.0e3, 9.0e3, 1.01e4, 4.0e4])
    np.testing.assert_array_equal(
        evaluate_hydrogen2_hydrogen2_elastic_cross_section(energy),
        source.evaluate_hydrogen2_hydrogen2_elastic_cross_section(energy),
    )


def test_the_saved_viscosity_fallback_is_reproduced_exactly():
    source = _source_operator()
    energy = np.array([0.5, 10.0, 1.0e3])
    np.testing.assert_array_equal(
        evaluate_hydrogen2_hydrogen2_elastic_cross_section(energy, viscosity=True),
        source.evaluate_hydrogen2_hydrogen2_elastic_cross_section(energy, viscosity=True),
    )


def test_the_saved_implementation_accepts_a_negative_energy_this_asset_rejects():
    """The documented repair: the saved implementation clipped negatives into the fit."""
    source = _source_operator()
    saved = source.evaluate_hydrogen2_hydrogen2_elastic_cross_section(np.array([-1.0]))
    np.testing.assert_allclose(
        saved,
        source.evaluate_hydrogen2_hydrogen2_elastic_cross_section(np.array([0.03])),
        rtol=0.0,
        atol=0.0,
    )
    with pytest.raises(ValueError):
        evaluate_hydrogen2_hydrogen2_elastic_cross_section(np.array([-1.0]))
