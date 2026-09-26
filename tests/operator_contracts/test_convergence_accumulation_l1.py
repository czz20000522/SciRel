"""Bounded historical replay of the r64 convergence/accumulation family
against the saved KN1DPy implementations, when present.

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
    evaluate_kn1d_outer_convergence,
    evaluate_neutral_generation_stopping,
    evaluate_neutral_outer_seed_convergence,
    update_neutral_generation_accumulation,
)

_PINNED = {
    "中性代际收敛判据": "dd110cbdc804c0ee3c4fcadbe7fb5da5254ae0a829de40ffc65c901ad9c89cc3",
    "中性代际累计状态更新": "77eca995baaf8b01a9454ecbe07f6d28f90d5ac5429f8b4fda949558d71e4f80",
    "中性外层种子收敛判据": "25f4918ff0ff2d68429088d9f12ef8902aa8981eab6ceee884255ccbc60e9e03",
    "KN1DPy顶层外层收敛判据": "3a5913b26bdac6361461f37c5494050a9102d6c98a98e9cb2906c9761d3dbbe2",
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
    spec = importlib.util.spec_from_file_location(f"kn1dpy_r64_{len(_LOADED)}", source)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _LOADED[package] = module
    return module


def test_generation_stopping_matches_saved_bit_for_bit():
    saved = _saved("中性代际收敛判据")
    gen = np.array([0.5, 1.0, 2.0])
    acc = np.array([100.0, 200.0, 300.0])
    for truncate in (0.1, 0.01):
        saved_result = saved.evaluate_neutral_generation_stopping(gen, acc, truncate)
        port_result = evaluate_neutral_generation_stopping(gen, acc, truncate)
        assert saved_result == port_result or all(np.array_equal(a, b) if isinstance(a, np.ndarray) else a == b for a, b in zip(saved_result, port_result))


def test_accumulation_matches_saved_bit_for_bit():
    saved = _saved("中性代际累计状态更新")
    rng = np.random.default_rng(91)
    dist = rng.random((2, 3, 4))
    density = rng.random(4) + 0.1
    state1_saved = saved.update_neutral_generation_accumulation(None, dist, density)
    state1_port = update_neutral_generation_accumulation(None, dist, density)
    for key in state1_saved:
        np.testing.assert_array_equal(state1_saved[key], state1_port[key])
    # second call
    dist2 = rng.random((2, 3, 4))
    density2 = rng.random(4) + 0.1
    state2_saved = saved.update_neutral_generation_accumulation(state1_saved, dist2, density2)
    state2_port = update_neutral_generation_accumulation(state1_port, dist2, density2)
    for key in state2_saved:
        np.testing.assert_array_equal(state2_saved[key], state2_port[key])


def test_outer_seed_convergence_matches_saved_bit_for_bit():
    saved = _saved("中性外层种子收敛判据")
    prev = np.array([100.0, 200.0, 300.0])
    curr = np.array([100.5, 200.5, 300.5])
    for truncate in (0.1, 0.001):
        saved_result = saved.evaluate_neutral_outer_seed_convergence(prev, curr, truncate)
        port_result = evaluate_neutral_outer_seed_convergence(prev, curr, truncate)
        assert saved_result == port_result


def test_kn1d_outer_convergence_matches_saved_bit_for_bit():
    saved = _saved("KN1DPy顶层外层收敛判据")
    prev = np.array([100.0, 200.0])
    curr = np.array([100.5, 200.5])
    for truncate in (0.1, 0.001):
        saved_result = saved.evaluate_kn1d_outer_convergence(prev, curr, truncate)
        port_result = evaluate_kn1d_outer_convergence(prev, curr, truncate)
        assert saved_result == port_result


def test_saved_rejection_behavior_agrees_exactly():
    saved_stopping = _saved("中性代际收敛判据")
    with pytest.raises(ValueError):
        saved_stopping.evaluate_neutral_generation_stopping(
            np.array([1.0]), np.array([0.0]), 0.1
        )
    with pytest.raises(ValueError):
        evaluate_neutral_generation_stopping(np.array([1.0]), np.array([0.0]), 0.1)
    saved_accum = _saved("中性代际累计状态更新")
    with pytest.raises(ValueError):
        saved_accum.update_neutral_generation_accumulation(None, np.ones((2, 3, 4)), np.array([-1.0]))
    with pytest.raises(ValueError):
        update_neutral_generation_accumulation(None, np.ones((2, 3, 4)), np.array([-1.0]))
