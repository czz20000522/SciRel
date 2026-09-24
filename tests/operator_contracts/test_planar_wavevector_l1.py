"""Bounded comparison with saved PDRF/PDRK implementations, when present."""

from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path

import numpy as np
import pytest

from scirel.geometry import project_planar_wavevector


SOURCE_HASHES = {
    ("PDRF", "plasma_k_projection"): "3e1ec867cddc4ee89958aef046ad886cb3c9f01e02cfe96b51dc70953b515ccf",
    ("PDRK", "wavevector_projection"): "ce6aa7abf1598457d889845b72d2ab2329639afcf62b682834e0cb74aa899196",
}


def _source_operator(project: str, name: str):
    root = os.environ.get("SCIREL_L1_ROOT")
    if not root:
        pytest.skip("SCIREL_L1_ROOT is not set; source-free contract tests remain active")
    source = Path(root) / project / "operators" / name / "scientific_operator.py"
    assert source.is_file(), f"saved L1 source missing: {source}"
    assert hashlib.sha256(source.read_bytes()).hexdigest() == SOURCE_HASHES[(project, name)]
    spec = importlib.util.spec_from_file_location(f"{project}_{name}", source)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_pdrf_matches_both_declaration_modes_on_the_compared_domain():
    pdrf = _source_operator("PDRF", "plasma_k_projection")
    for kwargs in (
        {"k_grid": [0.0, 0.5, 1.0], "theta": np.pi / 4},
        {"kx_grid": [3.0, -3.0], "kz_grid": [4.0, 4.0]},
    ):
        source = pdrf.compute_plasma_k_projection(**kwargs)
        proposed = project_planar_wavevector(
            k_grid=kwargs.get("k_grid"),
            theta_rad=kwargs.get("theta"),
            kx_grid=kwargs.get("kx_grid"),
            kz_grid=kwargs.get("kz_grid"),
        )
        for key in ("kx", "kz", "k"):
            np.testing.assert_allclose(proposed[key], source[key], rtol=2e-14, atol=0)


def test_pdrk_overlap_requires_explicit_units_and_angle_conversion():
    pdrk = _source_operator("PDRK", "wavevector_projection")
    proposed = project_planar_wavevector(k_grid=[0.5], theta_rad=np.pi / 4)
    source = pdrk.scientific_operator(
        par=[1.0, 45.0, 0.0, 0.0], cwp=2.0, ipa=1, ipb=2
    )
    for key in ("kx", "kz", "k"):
        np.testing.assert_allclose(proposed[key][0], source[key], rtol=2e-14, atol=0)
    assert "par" not in proposed
    assert "par" in source
