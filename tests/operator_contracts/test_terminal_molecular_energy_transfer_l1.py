"""Optional bounded replay against the saved KN1DPy terminal transfer operator."""

from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path

import numpy as np
import pytest

from scirel.kinetic import reduce_terminal_molecular_energy_transfer


_SHA256 = "da8da87c2030fadcb2c21cd7ae064398dbf91aeb461a591d11a641ccdc5b44b3"


def _saved():
    root = os.environ.get("SCIREL_KN1DPY_REVIEW_ROOT")
    if not root:
        pytest.skip("SCIREL_KN1DPY_REVIEW_ROOT is not set")
    source = (Path(root) / "operators" / "终态分子能量转移率归约"
              / "scientific_operator.py")
    assert source.is_file()
    assert hashlib.sha256(source.read_bytes()).hexdigest() == _SHA256
    spec = importlib.util.spec_from_file_location("saved_terminal_transfer", source)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.reduce_terminal_molecular_energy_transfer


@pytest.mark.parametrize("with_zero_weights", [False, True])
def test_saved_finite_carriers_replay_exactly(with_zero_weights):
    vr = np.array([0.25, 0.75])
    vx = np.array([-1.0, 0.25, 1.5])
    f = np.array([[[1.0, 0.8], [0.6, 0.5], [0.3, 0.2]],
                  [[0.7, 0.6], [0.5, 0.4], [0.2, 0.1]]])
    rhs = np.array([[[0.2, -0.1], [-0.3, 0.4], [0.1, 0.2]],
                    [[-0.2, 0.3], [0.5, -0.4], [-0.1, 0.1]]])
    radial_weight = np.array([0.4, 0.9])
    widths = np.array([0.3, 0.5, 0.8])
    if with_zero_weights:
        radial_weight[0] = 0.0
        widths[1] = 0.0
    arguments = (vr, vx, 1.5, 2.2e4, f, rhs, radial_weight, widths,
                 np.array([0.05, -0.08]))
    saved = _saved()(*arguments)
    current = reduce_terminal_molecular_energy_transfer(*arguments)
    assert saved.keys() == current.keys()
    for key in saved:
        np.testing.assert_array_equal(current[key], saved[key])


def test_saved_boolean_coercion_is_a_documented_input_repair():
    arguments = (
        np.array([0.5]), np.array([-1.0, 1.0]), 1.0, 5000.0,
        np.ones((1, 2, 1)), np.array([[[0.2], [-0.1]]]),
        np.array([True]), np.ones(2), np.array([0.3]),
    )
    assert np.isfinite(_saved()(*arguments)["loss_rate_profile_m3_s"]).all()
    with pytest.raises(ValueError, match="real numeric"):
        reduce_terminal_molecular_energy_transfer(*arguments)
