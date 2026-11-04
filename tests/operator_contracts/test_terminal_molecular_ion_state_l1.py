"""Optional bounded replay against the saved KN1DPy terminal H2+ operator."""

from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path

import numpy as np
import pytest

from scirel.kinetic import reduce_terminal_molecular_ion_state


_SHA256 = "a04b3049e4d33af713eb5632f88135777e683f7df257dfc061c8a853c06edb57"


def _saved():
    root = os.environ.get("SCIREL_KN1DPY_REVIEW_ROOT")
    if not root:
        pytest.skip("SCIREL_KN1DPY_REVIEW_ROOT is not set")
    source = (Path(root) / "operators" / "终态分子离子密度与温度归约"
              / "scientific_operator.py")
    assert source.is_file()
    assert hashlib.sha256(source.read_bytes()).hexdigest() == _SHA256
    spec = importlib.util.spec_from_file_location("saved_terminal_ion", source)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.reduce_terminal_molecular_ion_state


@pytest.mark.parametrize("zero_molecular_density", [False, True])
def test_saved_finite_carriers_replay_exactly(zero_molecular_density):
    rates = np.array(
        [[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 1.0, 2.0, 3.0, 4.0],
         [0.4, 0.3, 0.2, 0.1, 0.6, 0.5, 0.7, 4.0, 3.0, 2.0, 1.0]]
    ) * 1e-18
    molecular = np.array([4.0e17, 5.0e17])
    if zero_molecular_density:
        molecular[0] = 0.0
    arguments = (
        molecular, np.array([1.0e18, 2.0e18]), np.array([2.0, 3.0]),
        2.0, np.array([4.0, 5.0]), rates, np.array([1.0, 3.0]),
    )
    saved = _saved()(*arguments)
    current = reduce_terminal_molecular_ion_state(*arguments)
    assert saved.keys() == current.keys()
    for key in saved:
        np.testing.assert_array_equal(current[key], saved[key])


def test_saved_boolean_coercion_is_a_documented_input_repair():
    rates = np.zeros((1, 11))
    rates[:, 7:11] = 1e-18
    arguments = ([1.0], [1.0e18], [2.0], 1.0, [1.0], rates, [True])
    assert np.isfinite(_saved()(*arguments)["molecular_ion_density_m3"]).all()
    with pytest.raises(ValueError, match="real numeric"):
        reduce_terminal_molecular_ion_state(*arguments)
