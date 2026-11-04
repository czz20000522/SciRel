"""Optional bounded replay against the saved KN1DPy terminal heat operator."""

from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path

import numpy as np
import pytest

from scirel.kinetic import reduce_terminal_molecular_heat_flux


_SHA256 = "46e9c00fb9cce1f2d6e82efa83a176a91500ea06c00de4f224aa2a337bdf7aeb"


def _saved():
    root = os.environ.get("SCIREL_KN1DPY_REVIEW_ROOT")
    if not root:
        pytest.skip("SCIREL_KN1DPY_REVIEW_ROOT is not set")
    source = (Path(root) / "operators" / "终态分子随机与总热通量归约"
              / "scientific_operator.py")
    assert source.is_file()
    assert hashlib.sha256(source.read_bytes()).hexdigest() == _SHA256
    spec = importlib.util.spec_from_file_location("saved_terminal_heat", source)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.reduce_terminal_molecular_heat_flux


@pytest.mark.parametrize("with_zero_weights", [False, True])
def test_saved_finite_carriers_replay_exactly(with_zero_weights):
    vr = np.array([0.5, 1.0])
    vx = np.array([-1.0, 0.0, 2.0])
    f = np.array([[[1.0, 2.0], [2.0, 1.0], [3.0, 0.5]],
                  [[0.5, 1.0], [1.0, 2.0], [4.0, 3.0]]])
    radial_weight = np.array([1.0, 2.0])
    widths = np.array([0.5, 1.0, 0.25])
    if with_zero_weights:
        radial_weight[0] = 0.0
        widths[1] = 0.0
    arguments = (vr, vx, 1.0, 5000.0, f, radial_weight, widths)
    saved = _saved()(*arguments)
    current = reduce_terminal_molecular_heat_flux(*arguments)
    assert saved.keys() == current.keys()
    for key in saved:
        np.testing.assert_array_equal(current[key], saved[key])


def test_saved_boolean_coercion_is_a_documented_input_repair():
    arguments = (
        np.array([0.5]), np.array([-1.0, 1.0]), 1.0, 5000.0,
        np.ones((1, 2, 1)), np.array([True]), np.ones(2),
    )
    assert np.isfinite(_saved()(*arguments)["total_heat_flux_profile_w_m2"]).all()
    with pytest.raises(ValueError, match="real numeric"):
        reduce_terminal_molecular_heat_flux(*arguments)
