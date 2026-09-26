"""Bounded historical replay of the r67 collision-matrix assembly family
against the saved KN1DPy implementations, when present.

The saved operator bundles sit in the re-review archive ``KN1DPy-631d0bf1``:
KN1DPy's strict D1 qualification has been withdrawn, so this replay is
bounded historical development evidence about the arithmetic, not
qualified-L1 provenance and not expert approval.  Skipped unless
``SCIREL_KN1DPY_REVIEW_ROOT`` points at the bundle root; every saved
implementation file is pinned by SHA-256.

Tolerance scope: the integrated ports reuse the standardized
``scirel.collisions`` cross-section leaves, so the elastic families and the
captured predecessor state must agree with the saved arm bit for bit, while
the charge-exchange families are compared with rtol=1e-14.  That budget is
about 4.5x the largest deviation observed on the 200,011-point declared-domain
energy probe (2.22e-15 relative, root-caused to the standardized ``np.exp``
evaluation versus the source's ``np.e **``; a 1,000,001-point log-grid
root-cause probe observes up to 17 double-precision ulp by ``np.spacing``).
The probe covers the clip endpoints, the H-P 10 eV branch boundary and E = 0;
it is sampled evidence, not a bound over the continuous domain.
"""
from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path

import numpy as np
import pytest

from scirel.kinetic import (
    assemble_atomic_hydrogen_collision_matrices,
    assemble_molecular_hydrogen_collision_matrices,
)

_PINNED = {
    "原子氢碰撞矩阵组装": "80fcd63681d255fbe6a2a0fc2e400d63143c9809099d1181bb30ef3266a956fe",
    "分子氢碰撞矩阵组装": "34358f11e3ee91fa6768c8cf89d22eb1a2edbe2707f9e58d0b91472bf1b50d06",
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
    spec = importlib.util.spec_from_file_location(f"kn1dpy_r67_{len(_LOADED)}", source)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _LOADED[package] = module
    return module


CANONICAL = dict(vr=np.array([0.5, 1.0]), vx=np.array([-1.0, 1.0]),
                 Vr2pidVr=np.array([1.7671458676442586, 3.141592653589793]),
                 dVx=np.array([2.0, 2.0]), Tnorm=1.0, mu=1.0)

HOLDOUT = dict(vr=np.array([0.4, 0.8, 1.5]), vx=np.array([-2.0, -1.0, 1.0, 2.0]),
               Vr2pidVr=np.array([1.1309733552923258, 3.0237829290801748, 6.597344572538567]),
               dVx=np.array([1.0, 1.5, 1.5, 1.0]), Tnorm=5.0, mu=1.0)


def test_atomic_assembly_matches_saved():
    saved = _saved("原子氢碰撞矩阵组装")
    for case in (CANONICAL, HOLDOUT):
        saved_result = saved.assemble_atomic_hydrogen_collision_matrices(**case)
        port_result = assemble_atomic_hydrogen_collision_matrices(**case)
        for key in ("SIG_H_H", "SIG_H_H2", "SIG_H_P", "v_v2", "v_v", "vr2_vx2", "vx_vx", "Vr2pidVrdVx"):
            np.testing.assert_array_equal(saved_result[key], port_result[key])
        np.testing.assert_allclose(saved_result["SIG_CX"], port_result["SIG_CX"], rtol=1e-14, atol=0.0)


def test_molecular_assembly_matches_saved():
    saved = _saved("分子氢碰撞矩阵组装")
    for case in (CANONICAL, HOLDOUT):
        saved_result = saved.assemble_molecular_hydrogen_collision_matrices(**case)
        port_result = assemble_molecular_hydrogen_collision_matrices(**case)
        for key in ("SIG_H2_H", "SIG_H2_P", "SIG_H2_H2", "v_v2", "v_v", "vr2_vx2", "vx_vx", "Vr2pidVrdVx"):
            np.testing.assert_array_equal(saved_result[key], port_result[key])
        np.testing.assert_allclose(saved_result["SIG_CX"], port_result["SIG_CX"], rtol=1e-14, atol=0.0)


def test_rejection_behavior_agrees_exactly():
    saved_atomic = _saved("原子氢碰撞矩阵组装")
    saved_molecular = _saved("分子氢碰撞矩阵组装")
    bad = dict(vr=np.array([0.5, 1.0]), vx=np.array([-1.0, 1.0]),
               Vr2pidVr=np.array([1.0]), dVx=np.array([2.0, 2.0]),
               Tnorm=1.0, mu=1.0)
    for saved_call, port_call in (
        (
            lambda: saved_atomic.assemble_atomic_hydrogen_collision_matrices(**bad),
            lambda: assemble_atomic_hydrogen_collision_matrices(**bad),
        ),
        (
            lambda: saved_molecular.assemble_molecular_hydrogen_collision_matrices(**bad),
            lambda: assemble_molecular_hydrogen_collision_matrices(**bad),
        ),
    ):
        with pytest.raises(ValueError):
            saved_call()
        with pytest.raises(ValueError):
            port_call()
