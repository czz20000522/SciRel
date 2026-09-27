"""Bounded historical replay against the saved KN1DPy implementation, when present.

The saved operator bundle ``KN1DPy-631d0bf1/operators/原子氢分子氢弹性动量转移截面`` sits in
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

from scirel.collisions import evaluate_hydrogen_h2_elastic_cross_section

SOURCE_OPERATOR_SHA256 = "4377ae235fbcc0fb798253c995f44cf1e91aedecc99ce1b6bcbd1418b6c8d1bb"


def _source_operator():
    root = os.environ.get("SCIREL_KN1DPY_REVIEW_ROOT")
    if not root:
        pytest.skip(
            "SCIREL_KN1DPY_REVIEW_ROOT is not set; source-free contract tests remain active"
        )
    source = Path(root) / "operators" / "原子氢分子氢弹性动量转移截面" / "scientific_operator.py"
    assert source.is_file(), f"saved operator bundle missing: {source}"
    assert (
        hashlib.sha256(source.read_bytes()).hexdigest() == SOURCE_OPERATOR_SHA256
    ), f"saved operator bytes drifted from the compared arm: {source}"
    spec = importlib.util.spec_from_file_location("kn1dpy_h_hh_elastic", source)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_saved_fit_is_reproduced_exactly():
    source = _source_operator()
    energy = np.array([0.03, 0.3, 1.0, 7.5, 100.0, 1.0e3, 9.0e3, 1.01e4, 4.0e4])
    np.testing.assert_array_equal(
        evaluate_hydrogen_h2_elastic_cross_section(energy),
        source.evaluate_hydrogen_h2_elastic_cross_section(energy),
    )


def test_the_saved_leading_axis_wrapper_is_reproduced_exactly():
    source = _source_operator()
    energy = np.logspace(-1.5, 4, 12).reshape(4, 3)
    saved = source.evaluate_hydrogen_h2_elastic_cross_section(energy)
    ours = evaluate_hydrogen_h2_elastic_cross_section(energy)
    assert saved.shape == (1, 4, 3) and ours.shape == (1, 4, 3)
    np.testing.assert_array_equal(ours, saved)


def test_the_saved_implementation_accepts_a_negative_energy_this_asset_rejects():
    """The documented repair: the saved implementation clipped negatives into the fit."""
    source = _source_operator()
    saved = source.evaluate_hydrogen_h2_elastic_cross_section(np.array([-1.0]))
    np.testing.assert_allclose(
        saved,
        source.evaluate_hydrogen_h2_elastic_cross_section(np.array([0.03])),
        rtol=0.0,
        atol=0.0,
    )
    with pytest.raises(ValueError):
        evaluate_hydrogen_h2_elastic_cross_section(np.array([-1.0]))
