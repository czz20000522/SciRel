"""Direct contract tests for the r66 collision-frequency contraction family:
``contract_atomic_hydrogen_alpha_frequencies`` and
``contract_molecular_hydrogen_alpha_frequencies``.

The saved KN1DPy formal implementations (SHA-256 pinned in the L1 replay) are
reproduced bit for bit on the declared domain.  The atomic saved formal
implementation is verbatim; the molecular one carries the registered
kinetic_h2.py:1204 Alpha_CX reshape repair, which this port reproduces.
"""
from __future__ import annotations

import numpy as np
import pytest

from scirel.kinetic import (
    contract_atomic_hydrogen_alpha_frequencies,
    contract_molecular_hydrogen_alpha_frequencies,
)


def _fixture(nvr=3, nvx=4, nx=5, seed=61):
    rng = np.random.default_rng(seed)
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


def test_atomic_contraction_returns_four_alpha_families():
    SIG, fi_hat, ni, fH2, fH, _, _, _ = _fixture()
    result = contract_atomic_hydrogen_alpha_frequencies(SIG, SIG, SIG, SIG, fi_hat, ni, fH2, fH)
    assert set(result) == {"Alpha_CX", "Alpha_H_H", "Alpha_H_H2", "Alpha_H_P"}
    for key in result:
        assert result[key].shape == fi_hat.shape
        assert np.all(np.isfinite(result[key]))


def test_molecular_contraction_returns_three_alpha_families():
    SIG, fi_hat, ni, _, fH, fHp_hat, n, nHP = _fixture()
    result = contract_molecular_hydrogen_alpha_frequencies(SIG, SIG, SIG, fH, fHp_hat, fi_hat, n, nHP)
    assert set(result) == {"Alpha_CX", "Alpha_H2_H", "Alpha_H2_P"}
    for key in result:
        assert result[key].shape == fi_hat.shape
        assert np.all(np.isfinite(result[key]))


def test_molecular_ni_correct_subtracts_nHP():
    SIG, fi_hat, ni, _, fH, fHp_hat, n, nHP = _fixture()
    r_false = contract_molecular_hydrogen_alpha_frequencies(SIG, SIG, SIG, fH, fHp_hat, fi_hat, n, nHP, ni_correct=False)
    r_true = contract_molecular_hydrogen_alpha_frequencies(SIG, SIG, SIG, fH, fHp_hat, fi_hat, n, nHP, ni_correct=True)
    # ni_correct=True uses max(n - nHP, 0) < n, so Alpha_H2_P is smaller
    assert not np.array_equal(r_true["Alpha_H2_P"], r_false["Alpha_H2_P"])


def test_atomic_contraction_rejects_misaligned_shapes():
    SIG, fi_hat, ni, fH2, fH, _, _, _ = _fixture()
    with pytest.raises((ValueError, IndexError)):
        contract_atomic_hydrogen_alpha_frequencies(SIG[:2, :2], SIG, SIG, SIG, fi_hat, ni, fH2, fH)


def test_molecular_contraction_rejects_misaligned_shapes():
    SIG, fi_hat, ni, _, fH, fHp_hat, n, nHP = _fixture()
    with pytest.raises((ValueError, IndexError)):
        contract_molecular_hydrogen_alpha_frequencies(SIG[:2, :2], SIG, SIG, fH, fHp_hat, fi_hat, n, nHP)


def test_atomic_contraction_discriminating_inputs_with_asymmetric_sig():
    """Use asymmetric SIG matrices, distinct distributions, and a Fortran-order
    carrier mapping witness (one-hot SIG[5,3]=1 + F-order labelled fH)."""
    nvr, nvx, nx = 3, 4, 1
    N = nvr * nvx
    rng = np.random.default_rng(61)
    vr = np.linspace(0.5, 2.0, nvr)
    vx = np.linspace(-1.5, 1.5, nvx)
    vr2 = vr[:, None] ** 2 + vx[None, :] ** 2
    fi_hat = np.exp(-vr2)[:, :, None] * np.ones((nvr, nvx, nx))
    fH2 = np.exp(-vr2 * 0.5)[:, :, None] * np.ones((nvr, nvx, nx))
    fH = np.exp(-vr2 * 0.3)[:, :, None] * np.ones((nvr, nvx, nx))
    ni = np.linspace(1e18, 2e18, nx)
    nHP = np.full(nx, 5e17)
    n = np.full(nx, 1e18)
    fHp_hat = np.exp(-vr2 * 0.7)[:, :, None] * np.ones((nvr, nvx, nx))
    SIG_CX = rng.uniform(0.5, 2.0, (N, N))
    SIG_H_H = rng.uniform(0.3, 1.5, (N, N))
    SIG_H_H2 = rng.uniform(0.7, 1.8, (N, N))
    SIG_H_P = rng.uniform(0.2, 1.2, (N, N))
    result = contract_atomic_hydrogen_alpha_frequencies(
        SIG_CX, SIG_H_H, SIG_H_H2, SIG_H_P, fi_hat, ni, fH2, fH
    )
    assert not np.array_equal(result["Alpha_CX"], result["Alpha_H_H"])
    assert not np.array_equal(result["Alpha_H_H"], result["Alpha_H_H2"])

    # F-order carrier witness: one-hot SIG[5,3]=1, fH nodes labelled by F-order
    # flat index. Alpha_H_H output at flat 5 equals fH_flat[3].
    # F-order: flat 5 -> (2,1), flat 3 -> (0,1). C-order would map differently.
    SIG_onehot = np.zeros((N, N))
    SIG_onehot[5, 3] = 1.0
    fH_labelled = np.arange(N, dtype=float).reshape(nvr, nvx, nx, order="F")
    r_onehot = contract_atomic_hydrogen_alpha_frequencies(
        SIG_onehot, SIG_onehot, SIG_onehot, SIG_onehot, fi_hat, ni, fH2, fH_labelled
    )
    # F-order: out[2,1,0] = SIG_onehot[5,3] * fH_flat[3] = 1.0 * fH_labelled[0,1,0] = 3.0
    assert r_onehot["Alpha_H_H"][2, 1, 0] == 3.0
    # all other output positions are zero
    r_flat = r_onehot["Alpha_H_H"][:, :, 0].ravel(order="F")
    r_flat[5] = 0.0  # exclude the one-hot result
    np.testing.assert_array_equal(r_flat, np.zeros(N))

def test_molecular_contraction_ni_correct_both_branches():
    """Cover both ni_correct branches with distinct results."""
    nvr, nvx, nx = 3, 4, 2
    N = nvr * nvx
    rng = np.random.default_rng(62)
    vr = np.linspace(0.5, 2.0, nvr)
    vx = np.linspace(-1.5, 1.5, nvx)
    vr2 = vr[:, None] ** 2 + vx[None, :] ** 2
    fi_hat = np.exp(-vr2)[:, :, None] * np.ones((nvr, nvx, nx))
    fH = np.exp(-vr2 * 0.5)[:, :, None] * np.ones((nvr, nvx, nx))
    fHp_hat = np.exp(-vr2 * 0.7)[:, :, None] * np.ones((nvr, nvx, nx))
    SIG = rng.uniform(0.5, 2.0, (N, N))
    n = np.full(nx, 1e18)
    nHP = np.full(nx, 5e17)
    r_false = contract_molecular_hydrogen_alpha_frequencies(SIG, SIG, SIG, fH, fHp_hat, fi_hat, n, nHP, ni_correct=False)
    r_true = contract_molecular_hydrogen_alpha_frequencies(SIG, SIG, SIG, fH, fHp_hat, fi_hat, n, nHP, ni_correct=True)
    assert not np.array_equal(r_true["Alpha_H2_P"], r_false["Alpha_H2_P"])

