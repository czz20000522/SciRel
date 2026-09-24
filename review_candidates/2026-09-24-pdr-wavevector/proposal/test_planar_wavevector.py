"""Distinguishing evidence for the two frozen L1 wavevector operators."""

from __future__ import annotations

import importlib.util
import hashlib
import os
from pathlib import Path

import numpy as np
import pytest

from planar_wavevector import project_planar_wavevector


SOURCE_HASHES = {
    ("PDRF", "plasma_k_projection"): "3e1ec867cddc4ee89958aef046ad886cb3c9f01e02cfe96b51dc70953b515ccf",
    ("PDRK", "wavevector_projection"): "ce6aa7abf1598457d889845b72d2ab2329639afcf62b682834e0cb74aa899196",
}


def _source_operator(project: str, name: str):
    root = Path(os.environ["SCIREL_L1_ROOT"])
    source = root / project / "operators" / name / "scientific_operator.py"
    assert hashlib.sha256(source.read_bytes()).hexdigest() == SOURCE_HASHES[(project, name)]
    spec = importlib.util.spec_from_file_location(f"{project}_{name}", source)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_pdrf_polar_and_cartesian_contracts_map_to_proposal():
    source = _source_operator("PDRF", "plasma_k_projection")
    polar = source.compute_plasma_k_projection(k_grid=[0.0, 0.5, 1.0], theta=np.pi / 4)
    proposed = project_planar_wavevector(k_grid=[0.0, 0.5, 1.0], theta_rad=np.pi / 4)
    for key in ("kx", "kz", "k"):
        np.testing.assert_allclose(proposed[key], polar[key], rtol=2e-14, atol=0)
    assert proposed["theta_rad"] == polar["theta"]

    direct = source.compute_plasma_k_projection(kx_grid=[3.0, -3.0], kz_grid=[4.0, 4.0])
    proposed = project_planar_wavevector(kx_grid=[3.0, -3.0], kz_grid=[4.0, 4.0])
    for key in ("kx", "kz", "k"):
        np.testing.assert_allclose(proposed[key], direct[key], rtol=0, atol=0)
    assert proposed["theta_rad"] is direct["theta"] is None


def test_pdrk_polar_relation_agrees_only_after_explicit_unit_and_angle_mapping():
    source = _source_operator("PDRK", "wavevector_projection")
    cwp_m = 2.0
    k_m_inv = [0.0, 0.5, 1.0]
    proposed = project_planar_wavevector(k_grid=k_m_inv, theta_rad=np.pi / 4)
    for index, k in enumerate(k_m_inv):
        current = source.scientific_operator(
            par=[k * cwp_m, 45.0, 0.0, 0.0],
            cwp=cwp_m,
            ipa=1,
            ipb=2,
        )
        for key in ("kx", "kz", "k"):
            np.testing.assert_allclose(
                proposed[key][index], current[key], rtol=2e-14, atol=0
            )
        if k == 0.0:
            assert current["theta"] == 0.0
            assert proposed["theta_rad"] == np.pi / 4
        else:
            np.testing.assert_allclose(proposed["theta_rad"], np.deg2rad(current["theta"]))


def test_negative_magnitude_and_scan_state_prevent_whole_operator_reuse():
    pdrf = _source_operator("PDRF", "plasma_k_projection")
    pdrk = _source_operator("PDRK", "wavevector_projection")
    with pytest.raises(ValueError):
        pdrf.compute_plasma_k_projection(k_grid=[-0.5], theta=0.0)
    with pytest.raises(ValueError):
        project_planar_wavevector(k_grid=[-0.5], theta_rad=0.0)
    positive = pdrk.scientific_operator(par=[0.0, 0.0, 0.0, 0.0], cwp=2.0, ipa=1, ipb=2, pa_value=0.5)
    negative = pdrk.scientific_operator(par=[0.0, 0.0, 0.0, 0.0], cwp=2.0, ipa=1, ipb=2, pa_value=-0.5)
    np.testing.assert_allclose(positive["kx"], negative["kx"], rtol=0, atol=0)
    np.testing.assert_allclose(positive["kz"], negative["kz"], rtol=0, atol=0)
    assert negative["par"][0] == -0.5
    logged = pdrk.scientific_operator(par=[0.0, 0.0, 0.0, 0.0], cwp=2.0, ipa=1, ipb=2, pa_value=0.5, iloga=1)
    assert logged["par"][0] == 10.0**0.5
    assert "par" not in project_planar_wavevector(k_grid=[0.5], theta_rad=0.0)


def test_cartesian_relation_overlaps_but_angle_output_differs():
    pdrk = _source_operator("PDRK", "wavevector_projection")
    proposed = project_planar_wavevector(kx_grid=[3.0], kz_grid=[4.0])
    current = pdrk.scientific_operator(par=[0.0, 0.0, 8.0, 6.0], cwp=2.0, ipa=3, ipb=4)
    for key in ("kx", "kz", "k"):
        np.testing.assert_allclose(proposed[key][0], current[key], rtol=0, atol=0)
    assert proposed["theta_rad"] is None
    np.testing.assert_allclose(current["theta"], np.rad2deg(np.arctan2(3.0, 4.0)))


def test_cartesian_norm_overflow_is_an_explicit_successor_difference():
    pdrf = _source_operator("PDRF", "plasma_k_projection")
    with np.errstate(over="ignore"):
        source = pdrf.compute_plasma_k_projection(kx_grid=[1e200], kz_grid=[0.0])
    proposed = project_planar_wavevector(kx_grid=[1e200], kz_grid=[0.0])
    assert np.isinf(source["k"][0])
    assert proposed["k"][0] == 1e200


def test_negative_pdrk_normalization_length_flips_geometry():
    pdrk = _source_operator("PDRK", "wavevector_projection")
    current = pdrk.scientific_operator(par=[1.0, 45.0, 0.0, 0.0], cwp=-2.0, ipa=1, ipb=2)
    assert current["kx"] < 0 and current["kz"] < 0
    assert current["k"] == 0.5


def test_proposal_rejects_nonfinite_and_mismatched_inputs():
    for kwargs in (
        {},
        {"k_grid": [-1.0]},
        {"k_grid": [float("nan")]},
        {"k_grid": [1.0], "kx_grid": [1.0]},
        {"kx_grid": [1.0], "kz_grid": [1.0, 2.0]},
    ):
        with pytest.raises(ValueError):
            project_planar_wavevector(**kwargs)
