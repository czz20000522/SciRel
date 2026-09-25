"""Bounded historical replay against the saved KN1DPy implementation, when present.

The saved operator bundle ``KN1DPy-631d0bf1/operators/Maxwellian相对速度速率平均``
now sits in the re-review archive: KN1DPy's strict D1 qualification has been
withdrawn, so this replay is bounded historical development evidence about the
arithmetic, not qualified-L1 provenance and not expert approval.  The tests are
skipped unless ``SCIREL_KN1DPY_REVIEW_ROOT`` points at the bundle root, and the
saved implementation file is pinned by SHA-256 so a different byte stream can
never masquerade as the compared arm.
"""
from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path

import numpy as np
import pytest

from scirel.collisions import average_cross_section_over_maxwellian

SOURCE_OPERATOR_SHA256 = "e006a4ddb49f00d732ba03816fec591bca41d518d6d8df71a2b4985edb1aecb6"


def _source_operator():
    root = os.environ.get("SCIREL_KN1DPY_REVIEW_ROOT")
    if not root:
        pytest.skip(
            "SCIREL_KN1DPY_REVIEW_ROOT is not set; source-free contract tests remain active"
        )
    source = Path(root) / "operators" / "Maxwellian相对速度速率平均" / "scientific_operator.py"
    assert source.is_file(), f"saved operator bundle missing: {source}"
    assert (
        hashlib.sha256(source.read_bytes()).hexdigest() == SOURCE_OPERATOR_SHA256
    ), f"saved operator bytes drifted from the compared arm: {source}"
    spec = importlib.util.spec_from_file_location("kn1dpy_maxwellian_rate", source)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _midpoint_mesh(nvr, nvx, tnorm_ev, target_mass_amu):
    dvr = 3.5 / nvr
    dvx = 7.0 / nvx
    vr = (np.arange(nvr) + 0.5) * dvr
    vx = (np.arange(nvx) + 0.5) * dvx - 3.5
    amu = 1.6726231e-27
    e_ch = 1.602177e-19
    vth = np.sqrt(2.0 * e_ch * tnorm_ev / (target_mass_amu * amu))
    volume = np.outer(vr * dvr, np.full(nvx, dvx)) * vth**3
    return vx, vr, volume


def _arguments(vx, vr, volume, energies):
    return dict(
        particle_energy_ev=energies,
        particle_mass_amu=1.0,
        target_temperature_ev=10.0,
        target_mass_amu=2.0,
        vx=vx,
        vr=vr,
        tnorm_ev=20.0,
        cylindrical_volume=volume,
    )


def test_the_saved_constant_cross_section_extraction_is_reproduced():
    source = _source_operator()
    vx, vr, volume = _midpoint_mesh(48, 72, 20.0, 2.0)
    energies = np.array([0.0, 1.0, 5.0, 50.0, 500.0])
    arguments = _arguments(vx, vr, volume, energies)

    def sigma_const(energy):
        return np.full_like(energy, 2.0e-20)

    saved = source.average_cross_section_over_maxwellian(**arguments, cross_section_m2=sigma_const)
    ours = average_cross_section_over_maxwellian(**arguments, cross_section_m2=sigma_const)
    np.testing.assert_allclose(ours, saved, rtol=1e-14, atol=0.0)


def test_the_saved_linear_cross_section_holdout_is_reproduced():
    source = _source_operator()
    vx, vr, volume = _midpoint_mesh(48, 72, 20.0, 2.0)
    energies = np.array([0.0, 1.0, 5.0, 50.0, 500.0])
    arguments = _arguments(vx, vr, volume, energies)

    def sigma_linear(energy):
        return 2.0e-20 + 1.0e-22 * energy

    saved = source.average_cross_section_over_maxwellian(**arguments, cross_section_m2=sigma_linear)
    ours = average_cross_section_over_maxwellian(**arguments, cross_section_m2=sigma_linear)
    np.testing.assert_allclose(ours, saved, rtol=1e-14, atol=0.0)


def test_the_saved_implementation_accepts_a_nonfinite_mesh_this_asset_rejects():
    """The documented repair: the saved implementation propagated NaN silently."""
    source = _source_operator()
    vx, vr, volume = _midpoint_mesh(8, 12, 20.0, 2.0)
    vx = vx.copy()
    vx[3] = np.nan
    arguments = _arguments(vx, vr, volume, np.array([10.0]))
    sigma_const = lambda energy: np.full_like(energy, 2.0e-20)
    saved = source.average_cross_section_over_maxwellian(**arguments, cross_section_m2=sigma_const)
    assert not np.all(np.isfinite(saved))
    with pytest.raises(ValueError):
        average_cross_section_over_maxwellian(**arguments, cross_section_m2=sigma_const)
