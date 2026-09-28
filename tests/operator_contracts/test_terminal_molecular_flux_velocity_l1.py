"""Optional bounded replay against the saved KN1DPy terminal H2 operator."""

from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path

import numpy as np
import pytest

from scirel.kinetic import reduce_terminal_molecular_flux_velocity


_SHA256 = "73dfe7df71e537f35c69d9ac7470303501fb933c43eced6772e915498f873ea9"


def _saved():
    root = os.environ.get("SCIREL_KN1DPY_REVIEW_ROOT")
    if not root:
        pytest.skip("SCIREL_KN1DPY_REVIEW_ROOT is not set")
    source = (Path(root) / "operators" / "终态分子通量与轴向速度归约"
              / "scientific_operator.py")
    assert source.is_file()
    assert hashlib.sha256(source.read_bytes()).hexdigest() == _SHA256
    spec = importlib.util.spec_from_file_location("saved_terminal_flux", source)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.reduce_terminal_molecular_flux_velocity


@pytest.mark.parametrize("with_zero_weights", [False, True])
def test_saved_finite_carriers_replay_exactly(with_zero_weights):
    vx = np.array([-1.0, 0.0, 2.0])
    f = np.array([[[1.0, 2.0], [2.0, 1.0], [3.0, 0.5]],
                  [[0.5, 1.0], [1.0, 2.0], [4.0, 3.0]]])
    radial_weight = np.array([1.0, 2.0])
    axial_width = np.array([0.5, 1.0, 0.25])
    if with_zero_weights:
        radial_weight[0] = 0.0
        axial_width[1] = 0.0
    arguments = (vx, 5000.0, f, radial_weight, axial_width)
    saved = _saved()(*arguments)
    current = reduce_terminal_molecular_flux_velocity(*arguments)
    assert saved.keys() == current.keys()
    for key in saved:
        np.testing.assert_array_equal(current[key], saved[key])


def test_saved_boolean_coercion_is_a_documented_input_repair():
    vx = np.array([-1.0, 0.0, 2.0])
    f = np.ones((2, 3, 1))
    arguments = (vx, 5000.0, f, np.array([True, True]), np.ones(3))
    assert np.all(np.isfinite(_saved()(*arguments)["flux_profile_m2_s"]))
    with pytest.raises(ValueError, match="real numeric"):
        reduce_terminal_molecular_flux_velocity(*arguments)
