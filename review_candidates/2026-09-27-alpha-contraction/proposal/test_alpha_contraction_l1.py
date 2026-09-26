"""Bounded historical replay of the r66 collision-frequency contraction family
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
    contract_atomic_hydrogen_alpha_frequencies,
    contract_molecular_hydrogen_alpha_frequencies,
)

_PINNED = {
    "原子氢碰撞频率收缩": "6a30883d44d3fee77add57a09617e9621e728c7e984f3e4394f3b372683d4839",
    "分子氢碰撞频率收缩": "bbf1f1edc4c82ddda57ac7cb32730d4bfb5749670151f73ff2de370313366915",
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
    spec = importlib.util.spec_from_file_location(f"kn1dpy_r66_{len(_LOADED)}", source)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _LOADED[package] = module
    return module


def _fixture(seed=61):
    rng = np.random.default_rng(seed)
    nvr, nvx, nx = 3, 4, 5
    N = nvr * nvx
    SIG = np.eye(N)
    fi_hat = np.exp(-(np.linspace(0.5, 2.0, nvr)[:, None] ** 2 + np.linspace(-1.5, 1.5, nvx)[None, :] ** 2))[:, :, None] * np.ones((nvr, nvx, nx))
    ni = np.full(nx, 1e18)
    fH2 = np.ones((nvr, nvx, nx))
    fH = np.ones((nvr, nvx, nx))
    fHp_hat = np.ones((nvr, nvx, nx))
    n = np.full(nx, 1e18)
    nHP = np.full(nx, 5e17)
    return SIG, fi_hat, ni, fH2, fH, fHp_hat, n, nHP


def test_atomic_contraction_matches_saved_bit_for_bit():
    saved = _saved("原子氢碰撞频率收缩")
    SIG, fi_hat, ni, fH2, fH, _, _, _ = _fixture()
    saved_result = saved.contract_atomic_hydrogen_alpha_frequencies(SIG, SIG, SIG, SIG, fi_hat, ni, fH2, fH)
    port_result = contract_atomic_hydrogen_alpha_frequencies(SIG, SIG, SIG, SIG, fi_hat, ni, fH2, fH)
    for key in saved_result:
        np.testing.assert_array_equal(saved_result[key], port_result[key])


def test_molecular_contraction_matches_saved_bit_for_bit():
    saved = _saved("分子氢碰撞频率收缩")
    SIG, fi_hat, ni, _, fH, fHp_hat, n, nHP = _fixture()
    saved_result = saved.contract_molecular_hydrogen_alpha_frequencies(SIG, SIG, SIG, fH, fHp_hat, fi_hat, n, nHP)
    port_result = contract_molecular_hydrogen_alpha_frequencies(SIG, SIG, SIG, fH, fHp_hat, fi_hat, n, nHP)
    for key in saved_result:
        np.testing.assert_array_equal(saved_result[key], port_result[key])


def test_the_saved_rejection_behavior_agrees_exactly():
    saved_atomic = _saved("原子氢碰撞频率收缩")
    SIG, fi_hat, ni, fH2, fH, _, _, _ = _fixture()
    with pytest.raises((ValueError, IndexError)):
        saved_atomic.contract_atomic_hydrogen_alpha_frequencies(SIG[:2, :2], SIG, SIG, SIG, fi_hat, ni, fH2, fH)
    with pytest.raises((ValueError, IndexError)):
        contract_atomic_hydrogen_alpha_frequencies(SIG[:2, :2], SIG, SIG, SIG, fi_hat, ni, fH2, fH)






def test_atomic_contraction_with_asymmetric_sig_matches_saved():
    """Saved-arm parity with asymmetric SIG and distinct distributions."""
    saved = _saved("原子氢碰撞频率收缩")
    nvr, nvx, nx = 3, 4, 2
    N = nvr * nvx
    rng = np.random.default_rng(66)
    vr = np.linspace(0.5, 2.0, nvr)
    vx = np.linspace(-1.5, 1.5, nvx)
    vr2 = vr[:, None] ** 2 + vx[None, :] ** 2
    fi_hat = np.exp(-vr2)[:, :, None] * np.ones((nvr, nvx, nx))
    fH2 = np.exp(-vr2 * 0.5)[:, :, None] * np.ones((nvr, nvx, nx))
    fH = np.exp(-vr2 * 0.3)[:, :, None] * np.ones((nvr, nvx, nx))
    ni = np.linspace(1e18, 2e18, nx)
    SIG_CX = rng.uniform(0.5, 2.0, (N, N))
    SIG_H_H = rng.uniform(0.3, 1.5, (N, N))
    SIG_H_H2 = rng.uniform(0.7, 1.8, (N, N))
    SIG_H_P = rng.uniform(0.2, 1.2, (N, N))
    saved_result = saved.contract_atomic_hydrogen_alpha_frequencies(
        SIG_CX, SIG_H_H, SIG_H_H2, SIG_H_P, fi_hat, ni, fH2, fH
    )
    port_result = contract_atomic_hydrogen_alpha_frequencies(
        SIG_CX, SIG_H_H, SIG_H_H2, SIG_H_P, fi_hat, ni, fH2, fH
    )
    for key in saved_result:
        np.testing.assert_array_equal(saved_result[key], port_result[key])


def test_molecular_contraction_with_asymmetric_sig_matches_saved():
    """Saved-arm parity with asymmetric SIG, distinct distributions, both ni_correct branches."""
    saved = _saved("分子氢碰撞频率收缩")
    nvr, nvx, nx = 3, 4, 2
    N = nvr * nvx
    rng = np.random.default_rng(67)
    vr = np.linspace(0.5, 2.0, nvr)
    vx = np.linspace(-1.5, 1.5, nvx)
    vr2 = vr[:, None] ** 2 + vx[None, :] ** 2
    fi_hat = np.exp(-vr2)[:, :, None] * np.ones((nvr, nvx, nx))
    fH = np.exp(-vr2 * 0.3)[:, :, None] * np.ones((nvr, nvx, nx))
    fHp_hat = np.exp(-vr2 * 0.7)[:, :, None] * np.ones((nvr, nvx, nx))
    SIG_CX = rng.uniform(0.5, 2.0, (N, N))
    SIG_H2_H = rng.uniform(0.3, 1.5, (N, N))
    SIG_H2_P = rng.uniform(0.2, 1.2, (N, N))
    n = np.full(nx, 1e18)
    nHP = np.full(nx, 5e17)
    for nc in (False, True):
        saved_result = saved.contract_molecular_hydrogen_alpha_frequencies(
            SIG_CX, SIG_H2_H, SIG_H2_P, fH, fHp_hat, fi_hat, n, nHP, ni_correct=nc
        )
        port_result = contract_molecular_hydrogen_alpha_frequencies(
            SIG_CX, SIG_H2_H, SIG_H2_P, fH, fHp_hat, fi_hat, n, nHP, ni_correct=nc
        )
        for key in saved_result:
            np.testing.assert_array_equal(saved_result[key], port_result[key])

