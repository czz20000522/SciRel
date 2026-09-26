"""Bounded historical replay of the r68 Omega aggregation family against the
saved KN1DPy implementations, when present.

The saved operator bundles sit in the re-review archive ``KN1DPy-631d0bf1``:
KN1DPy's strict D1 qualification has been withdrawn, so this replay is
bounded historical development evidence about the arithmetic, not
qualified-L1 provenance and not expert approval.  Skipped unless
``SCIREL_KN1DPY_REVIEW_ROOT`` points at the bundle root; every saved
implementation file is pinned by SHA-256.

Parity scope: all six declared outputs must agree bit for bit on the saved
fixtures, which cover both Wperp branch paths per arm (weight totals 0.5 and
-0.5; the atomic ``<= 0`` and molecular ``< 0`` selectors therefore take
their documented opposite paths at zero).  The registered fail-closed
hardenings (scalar Vth/tol gates, non-positive density, non-finite output
gate) are NOT replayed as rejection agreements where the saved arm silently
accepts the input; the direct tests discriminate those boundaries instead.
"""
from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path

import numpy as np
import pytest

from scirel.kinetic import (
    assemble_atomic_hydrogen_omega_frequencies,
    assemble_molecular_hydrogen_omega_frequencies,
)

_PINNED = {
    "原子氢弹性散射频率聚合": "5b80ea51cf51490208c5e39d71ca5a56c9a4610943a703e066cbbfa4ea6d9038",
    "分子氢弹性碰撞频率聚合": "13b001078958fa6fd8a819e65340a3a4e22fbfb6a3dbb58e4451db92e81f78d9",
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
    spec = importlib.util.spec_from_file_location(f"kn1dpy_r68_{len(_LOADED)}", source)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _LOADED[package] = module
    return module


VR = np.linspace(0.5, 4.5, 9)
VX = np.linspace(-6.0, 6.0, 13)
NX = 3
NVR, NVX = VR.size, VX.size
_R = np.linspace(0.0, 1.0, NVR + 1)
VR2PIDVR = np.pi * (_R[1:] ** 2 - _R[:-1] ** 2)
_X = np.linspace(-6.5, 6.5, NVX + 1)
DVX = np.diff(_X)
KERNEL = VR[:, None] ** 2 - 2.0 * VX[None, :] ** 2
VTH = 1000.0
VXI = np.array([900.0, 800.0, 1200.0])
VXH2 = np.array([700.0, 750.0, 1100.0])
NH = np.array([0.7, 1.9, 1.1])
NH2 = np.array([1.4, 0.9, 2.1])
_RNG_SEED = 55
_SHAPE = np.exp(-(VR[:, None] ** 2 + (VX[None, :] - 1.5) ** 2) / 9.0)


def _fixture(weight_sum):
    """Freshly seeded per call: single-test runs see the same carriers as the
    whole-file run."""
    rng = np.random.default_rng(_RNG_SEED)
    fh = np.repeat(_SHAPE[:, :, None], NX, axis=2) * rng.uniform(0.7, 1.3, NX)[None, None, :]
    a_p = rng.uniform(0.1, 0.9, size=(NVR, NVX, NX))
    a_h = rng.uniform(0.1, 0.9, size=(NVR, NVX, NX))
    sig = -rng.uniform(0.1, 0.9, size=(NVR * NVX, NVR * NVX))
    return fh, a_p, a_h, sig, fh * weight_sum


ATOMIC_KEYS = ("VxH", "Omega_H_P", "Omega_H_H2", "Omega_H_H", "Omega_EL", "Wperp_paraH")
MOLECULAR_KEYS = ("VxH2", "Omega_H2_P", "Omega_H2_H", "Omega_H2_H2", "Omega_EL", "Wperp_paraH2")


@pytest.mark.parametrize("weight_sum", [0.5, -0.5])
def test_atomic_omega_matches_saved_bit_for_bit(weight_sum):
    saved = _saved("原子氢弹性散射频率聚合")
    fh, a_p, a_h2, sig, w = _fixture(weight_sum)
    saved_result = saved.assemble_atomic_hydrogen_omega_frequencies(
        fh, NH, a_p, a_h2, sig, VR2PIDVR, DVX, VR, VX, VTH, VXI, VXH2,
        w, KERNEL, DeltaVx_tol=0.01, Wpp_tol=0.001,
        H_P_EL=True, H_H2_EL=True, H_H_EL=True)
    port_result = assemble_atomic_hydrogen_omega_frequencies(
        fh, NH, a_p, a_h2, sig, VR2PIDVR, DVX, VR, VX, VTH, VXI, VXH2,
        w, KERNEL, DeltaVx_tol=0.01, Wpp_tol=0.001,
        H_P_EL=True, H_H2_EL=True, H_H_EL=True)
    for key in ATOMIC_KEYS:
        np.testing.assert_array_equal(saved_result[key], port_result[key])


@pytest.mark.parametrize("weight_sum", [0.5, -0.5])
def test_molecular_omega_matches_saved_bit_for_bit(weight_sum):
    saved = _saved("分子氢弹性碰撞频率聚合")
    fh, a_p, a_h, sig, w = _fixture(weight_sum)
    saved_result = saved.assemble_molecular_hydrogen_omega_frequencies(
        fh, NH2, a_p, a_h, sig, VR2PIDVR, DVX, VR, VX, VTH, VXI, VXH2,
        w, KERNEL, DeltaVx_tol=0.01, Wpp_tol=0.001,
        H2_P_EL=True, H2_H_EL=True, H2_H2_EL=True)
    port_result = assemble_molecular_hydrogen_omega_frequencies(
        fh, NH2, a_p, a_h, sig, VR2PIDVR, DVX, VR, VX, VTH, VXI, VXH2,
        w, KERNEL, DeltaVx_tol=0.01, Wpp_tol=0.001,
        H2_P_EL=True, H2_H_EL=True, H2_H2_EL=True)
    for key in MOLECULAR_KEYS:
        np.testing.assert_array_equal(saved_result[key], port_result[key])


def test_saved_rejection_behavior_agrees_on_shared_boundaries():
    """Only boundaries where the saved arm itself raises are replayed here;
    the registered hardenings (scalar Vth/tol gates, non-finite output gate,
    density fail-closed) diverge from the silent saved behavior by design."""
    saved_atomic = _saved("原子氢弹性散射频率聚合")
    saved_molecular = _saved("分子氢弹性碰撞频率聚合")
    fh, a_p, a_h, sig, w = _fixture(0.5)
    bad_sig = np.zeros((NVR * NVX, NVX))
    for saved_call, port_call in (
        (
            lambda: saved_atomic.assemble_atomic_hydrogen_omega_frequencies(
                fh, NH, a_p, a_h, bad_sig, VR2PIDVR, DVX, VR, VX, VTH, VXI, VXH2,
                w, KERNEL, DeltaVx_tol=0.01, Wpp_tol=0.001),
            lambda: assemble_atomic_hydrogen_omega_frequencies(
                fh, NH, a_p, a_h, bad_sig, VR2PIDVR, DVX, VR, VX, VTH, VXI, VXH2,
                w, KERNEL, DeltaVx_tol=0.01, Wpp_tol=0.001),
        ),
        (
            lambda: saved_molecular.assemble_molecular_hydrogen_omega_frequencies(
                fh, np.ones(NX + 1), a_p, a_h, sig, VR2PIDVR, DVX, VR, VX, VTH,
                VXI, VXH2, w, KERNEL, DeltaVx_tol=0.01, Wpp_tol=0.001),
            lambda: assemble_molecular_hydrogen_omega_frequencies(
                fh, np.ones(NX + 1), a_p, a_h, sig, VR2PIDVR, DVX, VR, VX, VTH,
                VXI, VXH2, w, KERNEL, DeltaVx_tol=0.01, Wpp_tol=0.001),
        ),
    ):
        with pytest.raises(ValueError):
            saved_call()
        with pytest.raises(ValueError):
            port_call()
