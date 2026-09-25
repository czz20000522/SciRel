"""Bounded historical replay against the saved KN1DPy quadrature, when present.

The saved ``圆柱速度空间积分权重`` package sits in the re-review archive
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

from scirel.kinetic import make_cylindrical_velocity_quadrature

SOURCE_OPERATOR_SHA256 = "0a52064747e92b223bdc1c6f78ccdd8bc63a696edc64a7b9c903a6b0515fa0a6"

_ORDERED_KEYS = (
    "radial_measure",
    "radial_four_pi_measure",
    "dvx",
    "vr_left",
    "vr_right",
    "vx_left",
    "vx_right",
    "volume",
    "inv_dvx_ghost",
    "vx_over_dvx_ghost",
    "vr_over_dvr_ghost",
    "speed_squared",
)


def _source_operator():
    root = os.environ.get("SCIREL_KN1DPY_REVIEW_ROOT")
    if not root:
        pytest.skip(
            "SCIREL_KN1DPY_REVIEW_ROOT is not set; source-free contract tests remain active"
        )
    source = Path(root) / "operators" / "圆柱速度空间积分权重" / "scientific_operator.py"
    assert source.is_file(), f"saved operator bundle missing: {source}"
    assert (
        hashlib.sha256(source.read_bytes()).hexdigest() == SOURCE_OPERATOR_SHA256
    ), f"saved operator bytes drifted from the compared arm: {source}"
    spec = importlib.util.spec_from_file_location("kn1dpy_cylindrical_quadrature", source)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "vr, vx",
    [
        (np.array([0.5, 1.5]), np.array([-1.5, -0.5, 0.5, 1.5])),
        (np.array([0.5, 1.0, 4.0]), np.array([-2.0, -0.5, 0.5, 1.0, 2.5])),
    ],
)
def test_every_quadrature_field_is_reproduced(vr, vx):
    source = _source_operator()
    saved = source.make_cylindrical_velocity_quadrature(vr, vx)
    ours = make_cylindrical_velocity_quadrature(vr=vr, vx=vx)
    assert set(saved) == set(ours)
    for key in _ORDERED_KEYS:
        np.testing.assert_allclose(ours[key], saved[key], rtol=1e-15, atol=0.0)
    for key in (
        "positive_vx_indices",
        "positive_vx_first_index",
        "positive_vx_last_index",
        "negative_vx_indices",
        "negative_vx_first_index",
        "negative_vx_last_index",
    ):
        assert np.array_equal(np.asarray(ours[key]), np.asarray(saved[key])), key


def test_the_saved_implementation_accepts_a_nonfinite_mesh_this_asset_rejects():
    """The documented repair: the saved implementation propagated NaN silently."""
    source = _source_operator()
    vr = np.array([1.0, np.nan, 2.0])
    vx = np.array([-1.0, 0.0, 1.0])
    saved = source.make_cylindrical_velocity_quadrature(vr, vx)
    assert not all(np.all(np.isfinite(value)) for key in ("volume",) for value in [saved[key]])
    with pytest.raises(ValueError):
        make_cylindrical_velocity_quadrature(vr=vr, vx=vx)
