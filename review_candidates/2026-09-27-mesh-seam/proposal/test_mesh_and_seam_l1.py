"""Bounded historical replay of the r61 mesh/seam pair against the saved
KN1DPy implementations, when present.

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
    create_adaptive_neutral_velocity_mesh,
    interpolate_scalar_across_mesh,
)

_PINNED = {
    "自适应中性粒子速度网格": "38fcde8ba437ce5ee72f6465968ea3fd8ade9a4ff24b5a6692823a20207f2842",
    "跨网格标量插值": "01a014fe9b733d6afc6b9ce1216baed292a8cc9f79c0a45d6b89d5f9236bffa7",
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
    spec = importlib.util.spec_from_file_location(f"kn1dpy_r61_{len(_LOADED)}", source)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _LOADED[package] = module
    return module


def test_mesh_matches_the_saved_implementation_bit_for_bit():
    saved = _saved("自适应中性粒子速度网格")
    cases = [
        (4, (1.0, 1.05), (), 0.0),
        (4, (1.0, 9.0), (), 0.0),
        (4, (1.0, 4.0), (9.0,), 0.0),
        (6, (0.5, 2.0, 8.0), (3.0, 25.0), 30.0),
        (5, (2.0, 2.1, 2.2), (), 0.0),
    ]
    for nv, temperatures, requested, cap in cases:
        saved_out = saved.create_adaptive_neutral_velocity_mesh(
            nv, temperatures, requested, cap
        )
        new_out = create_adaptive_neutral_velocity_mesh(nv, temperatures, requested, cap)
        for saved_value, new_value in zip(saved_out, new_out):
            if isinstance(saved_value, np.ndarray):
                np.testing.assert_array_equal(saved_value, new_value)
            else:
                assert saved_value == new_value


def test_interpolation_matches_the_saved_implementation_bit_for_bit():
    saved = _saved("跨网格标量插值")
    rng = np.random.default_rng(61)
    for _ in range(4):
        xa = np.sort(rng.uniform(0.0, 10.0, 12))
        fa = rng.uniform(-5.0, 5.0, 12)
        xb = np.sort(rng.uniform(-2.0, 12.0, 20))
        np.testing.assert_array_equal(
            saved.interp_scalar_across_mesh(fa, xa, xb, 0),
            interpolate_scalar_across_mesh(fa, xa, xb, 0),
        )


def test_saved_rejection_behavior_agrees_exactly():
    saved = _saved("自适应中性粒子速度网格")
    with pytest.raises(ValueError):
        saved.create_adaptive_neutral_velocity_mesh(0, (1.0,))
    with pytest.raises(ValueError):
        create_adaptive_neutral_velocity_mesh(0, (1.0,))
    with pytest.raises(ValueError):
        saved.create_adaptive_neutral_velocity_mesh(4, (1.0,), temperature_cap_ev=0.5)
    with pytest.raises(ValueError):
        create_adaptive_neutral_velocity_mesh(4, (1.0,), temperature_cap_ev=0.5)

    saved_interp = _saved("跨网格标量插值")
    xa = np.array([0.0, 1.0, 2.0])
    fa = np.array([1.0, 2.0, 3.0])
    with pytest.raises(ValueError):
        saved_interp.interp_scalar_across_mesh(fa, xa, np.array([5.0, 6.0]), 0)
    with pytest.raises(ValueError):
        interpolate_scalar_across_mesh(fa, xa, np.array([5.0, 6.0]), 0)
    with pytest.raises(ValueError):
        saved_interp.interp_scalar_across_mesh(fa[:-1], xa, np.array([0.5]), 0)
    with pytest.raises(ValueError):
        interpolate_scalar_across_mesh(fa[:-1], xa, np.array([0.5]), 0)
