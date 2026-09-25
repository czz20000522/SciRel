"""Bounded historical replay against the saved KN1DPy seed leaf, when present.

The saved ``平移Maxwellian离散初值`` package sits in the re-review archive
(KN1DPy's strict D1 qualification withdrawn), so this replay is bounded
historical development evidence about the arithmetic, not qualified-L1
provenance.  Skipped unless ``SCIREL_KN1DPY_REVIEW_ROOT`` points at the bundle
root; the saved implementation file is pinned by SHA-256.
"""
from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path

import numpy as np
import pytest

from scirel.kinetic import build_shifted_maxwellian_seed

SOURCE_OPERATOR_SHA256 = "c495a86822c02dbb4bd84fe11f5cffb6093a85906be3dae66773d2e334641051"


def _source_operator():
    root = os.environ.get("SCIREL_KN1DPY_REVIEW_ROOT")
    if not root:
        pytest.skip(
            "SCIREL_KN1DPY_REVIEW_ROOT is not set; source-free contract tests remain active"
        )
    source = Path(root) / "operators" / "平移Maxwellian离散初值" / "scientific_operator.py"
    assert source.is_file(), f"saved operator bundle missing: {source}"
    assert (
        hashlib.sha256(source.read_bytes()).hexdigest() == SOURCE_OPERATOR_SHA256
    ), f"saved operator bytes drifted from the compared arm: {source}"
    spec = importlib.util.spec_from_file_location("kn1dpy_shifted_maxwellian_seed", source)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "shifts, temperatures",
    [
        (np.array([0.0, 2.0e4]), np.array([2.0, 2.0])),
        (np.array([5.0e3]), np.array([10.0])),
    ],
)
def test_the_seed_distribution_is_reproduced(shifts, temperatures):
    source = _source_operator()
    vr = np.array([0.5, 1.0])
    vx = np.array([-1.0, 0.0, 1.0])
    volume = np.outer([0.5, 1.5], [1.0, 2.0, 1.0])
    saved = source.build_shifted_maxwellian_seed(
        vr, vx, 20.0, shifts, temperatures, 2.0, 1, volume
    )
    ours = build_shifted_maxwellian_seed(
        vr=vr,
        vx=vx,
        tnorm_ev=20.0,
        shifted_vx_m_s=shifts,
        temperature_ev=temperatures,
        mass_amu=2.0,
        molecule_count=1,
        cylindrical_volume=volume,
    )
    assert set(saved) == set(ours)
    np.testing.assert_allclose(ours["distribution"], saved["distribution"], rtol=1e-15, atol=0.0)
    np.testing.assert_allclose(ours["exponent"], saved["exponent"], rtol=1e-15, atol=0.0)
    assert ours["thermal_speed_m_s"] == saved["thermal_speed_m_s"]


def test_the_molecule_count_two_holdout_is_reproduced():
    source = _source_operator()
    vr = np.array([0.5, 1.0])
    vx = np.array([-1.0, 0.0, 1.0])
    volume = np.ones((2, 3))
    saved = source.build_shifted_maxwellian_seed(vr, vx, 20.0, [0.0], [10.0], 2.0, 2, volume)
    ours = build_shifted_maxwellian_seed(
        vr=vr,
        vx=vx,
        tnorm_ev=20.0,
        shifted_vx_m_s=np.array([0.0]),
        temperature_ev=np.array([10.0]),
        mass_amu=2.0,
        molecule_count=2,
        cylindrical_volume=volume,
    )
    np.testing.assert_allclose(ours["distribution"], saved["distribution"], rtol=1e-15, atol=0.0)
