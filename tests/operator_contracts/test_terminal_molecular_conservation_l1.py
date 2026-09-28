"""Optional bounded replay against the saved KN1DPy conservation operator."""

from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path

import numpy as np
import pytest

from scirel.kinetic import reduce_qh2_total_conservation_diagnostic


_SHA256 = "258ef36f7d265f5a7cc08f021cbf91fbd83ad9ce6876a1c56d1064655d4c2af3"


def _saved():
    root = os.environ.get("SCIREL_KN1DPY_REVIEW_ROOT")
    if not root:
        pytest.skip("SCIREL_KN1DPY_REVIEW_ROOT is not set")
    source = (Path(root) / "operators" / "终态分子总能量守恒诊断"
              / "scientific_operator.py")
    assert source.is_file()
    assert hashlib.sha256(source.read_bytes()).hexdigest() == _SHA256
    spec = importlib.util.spec_from_file_location("saved_terminal_conservation", source)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.reduce_qh2_total_conservation_diagnostic


@pytest.mark.parametrize("arguments", [
    (np.array([0.0, 0.02, 0.05, 0.08]), np.array([10.0, 8.0, 5.0, 4.0]),
     np.array([90.0, 70.0, 40.0, 20.0])),
    (np.array([2.0, 0.5, -1.0]), np.array([1.0, -3.5, -8.0]),
     np.array([3.0, 3.0, 3.0])),
])
def test_saved_finite_carriers_replay_exactly(arguments):
    saved = _saved()(*arguments)
    current = reduce_qh2_total_conservation_diagnostic(*arguments)
    assert saved.keys() == current.keys()
    for key in saved:
        np.testing.assert_array_equal(current[key], saved[key])


def test_saved_boolean_coercion_is_a_documented_input_repair():
    arguments = (np.array([False, True]), np.array([1.0, 2.0]),
                 np.array([1.0, 2.0]))
    assert np.isfinite(_saved()(*arguments)[
        "total_energy_conservation_error_profile_dimensionless"
    ]).all()
    with pytest.raises(ValueError, match="real numeric"):
        reduce_qh2_total_conservation_diagnostic(*arguments)
