"""Bounded historical replay against the saved KN1DPy implementation, when present.

The saved operator bundle ``KN1DPy-631d0bf1/operators/原子氢Saha平衡人口密度`` sits in
the re-review archive: KN1DPy's strict D1 qualification has been withdrawn, so
this replay is bounded historical development evidence about the arithmetic,
not qualified-L1 provenance and not expert approval.  The tests are skipped
unless ``SCIREL_KN1DPY_REVIEW_ROOT`` points at the bundle root, and the saved
implementation file is pinned by SHA-256 so a different byte stream can never
masquerade as the compared arm.  Unlike most leaves in this family, the saved
implementation already enforced its declared contract, so no repair witness is
expected; the replay establishes exact agreement instead.
"""
from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path

import numpy as np
import pytest

from scirel.kinetic import evaluate_h_saha_equilibrium_population

SOURCE_OPERATOR_SHA256 = "38fa28ac6728cf4aaa3e98ec638b1c39435200901ba8415a444a4df8d1dee89c"


def _source_operator():
    root = os.environ.get("SCIREL_KN1DPY_REVIEW_ROOT")
    if not root:
        pytest.skip(
            "SCIREL_KN1DPY_REVIEW_ROOT is not set; source-free contract tests remain active"
        )
    source = Path(root) / "operators" / "原子氢Saha平衡人口密度" / "scientific_operator.py"
    assert source.is_file(), f"saved operator bundle missing: {source}"
    assert (
        hashlib.sha256(source.read_bytes()).hexdigest() == SOURCE_OPERATOR_SHA256
    ), f"saved operator bytes drifted from the compared arm: {source}"
    spec = importlib.util.spec_from_file_location("kn1dpy_saha", source)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("level", [1, 2, 3])
def test_the_saved_population_is_reproduced_exactly(level):
    source = _source_operator()
    density = np.logspace(18, 23, 12)
    temperature = np.logspace(0, 3, 12)
    np.testing.assert_array_equal(
        evaluate_h_saha_equilibrium_population(density, temperature, level),
        source.evaluate_h_saha_equilibrium_population(density, temperature, level),
    )


def test_the_saved_rejections_are_reproduced_exactly():
    source = _source_operator()
    with pytest.raises(ValueError):
        source.evaluate_h_saha_equilibrium_population(np.array([[1.0e18]]), np.array([[1.0]]), 1)
    with pytest.raises(ValueError):
        source.evaluate_h_saha_equilibrium_population(np.array([1.0e18]), np.array([1.0]), 0)
    with pytest.raises(ValueError):
        evaluate_h_saha_equilibrium_population(np.array([[1.0e18]]), np.array([[1.0]]), 1)
    with pytest.raises(ValueError):
        evaluate_h_saha_equilibrium_population(np.array([1.0e18]), np.array([1.0]), 0)
