"""Bounded historical replay against the saved KN1DPy implementation, when present.

The saved operator bundle ``KN1DPy-631d0bf1/operators/COLLRAD_H0电子碰撞电离率`` sits
in the re-review archive: KN1DPy's strict D1 qualification has been withdrawn,
so this replay is bounded historical development evidence about the arithmetic,
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

from scirel.collisions import evaluate_collrad_h0_ionization_rate

SOURCE_OPERATOR_SHA256 = "2cd665e788e1444d60a4d7ca4b0e95fd76fd651b8a12653f7969aba8b9939bf1"


def _source_operator():
    root = os.environ.get("SCIREL_KN1DPY_REVIEW_ROOT")
    if not root:
        pytest.skip(
            "SCIREL_KN1DPY_REVIEW_ROOT is not set; source-free contract tests remain active"
        )
    source = Path(root) / "operators" / "COLLRAD_H0电子碰撞电离率" / "scientific_operator.py"
    assert source.is_file(), f"saved operator bundle missing: {source}"
    assert (
        hashlib.sha256(source.read_bytes()).hexdigest() == SOURCE_OPERATOR_SHA256
    ), f"saved operator bytes drifted from the compared arm: {source}"
    spec = importlib.util.spec_from_file_location("kn1dpy_collrad_h0", source)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_saved_one_dimensional_sweep_is_reproduced_exactly():
    source = _source_operator()
    density = np.logspace(16, 23, 12)
    temperature = np.logspace(-1, 4, 12)
    np.testing.assert_array_equal(
        evaluate_collrad_h0_ionization_rate(density, temperature),
        source.evaluate_collrad_h0_ionization_rate(density, temperature),
    )


def test_the_saved_clamped_edges_are_reproduced_exactly():
    source = _source_operator()
    density = np.array([1.0e6, 1.0e10, 1.0e23, 1.0e25])
    temperature = np.array([1.0e-3, 10.0**-1.2, 10.0**4.7, 1.0e6])
    np.testing.assert_array_equal(
        evaluate_collrad_h0_ionization_rate(density, temperature),
        source.evaluate_collrad_h0_ionization_rate(density, temperature),
    )


def test_the_saved_implementation_flattens_a_two_dimensional_input_this_asset_does_not():
    """The documented repair: the saved implementation returned a flat 1-D array."""
    source = _source_operator()
    density = np.array([[1.0e16, 1.0e17], [1.0e18, 1.0e19]])
    temperature = np.array([[1.0, 2.0], [4.0, 8.0]])
    saved = source.evaluate_collrad_h0_ionization_rate(density, temperature)
    assert saved.shape == (4,)
    ours = evaluate_collrad_h0_ionization_rate(density, temperature)
    assert ours.shape == (2, 2)
    np.testing.assert_array_equal(ours, saved.reshape(2, 2))


def test_the_saved_implementation_accepts_same_size_mismatched_shapes_this_asset_rejects():
    """The documented repair: the saved implementation compared flattened sizes only."""
    source = _source_operator()
    saved = source.evaluate_collrad_h0_ionization_rate(
        np.array([[1.0e18, 2.0e18], [3.0e18, 4.0e18]]), np.array([1.0, 2.0, 3.0, 4.0])
    )
    assert saved.shape == (4,)
    with pytest.raises(ValueError):
        evaluate_collrad_h0_ionization_rate(
            np.array([[1.0e18, 2.0e18], [3.0e18, 4.0e18]]), np.array([1.0, 2.0, 3.0, 4.0])
        )
