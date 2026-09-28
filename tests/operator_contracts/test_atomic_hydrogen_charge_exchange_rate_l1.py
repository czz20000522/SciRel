"""Optional SHA-gated replay of the saved KN1DPy atomic-H CX rate fit."""

from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path

import numpy as np
import pytest

from scirel.collisions import evaluate_atomic_hydrogen_charge_exchange_rate


_SHA256 = "9a0037c238cc9fc99eabfa17984368d954c56ef9aa651e47967b5b1c273a1bfa"


def _saved():
    root = os.environ.get("SCIREL_KN1DPY_REVIEW_ROOT")
    if not root:
        pytest.skip("SCIREL_KN1DPY_REVIEW_ROOT is not set")
    source = (Path(root) / "operators" / "原子氢电荷交换Maxwellian速率系数"
              / "scientific_operator.py")
    assert source.is_file()
    assert hashlib.sha256(source.read_bytes()).hexdigest() == _SHA256
    spec = importlib.util.spec_from_file_location("saved_atomic_cx_rate", source)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.evaluate_atomic_hydrogen_charge_exchange_rate


@pytest.mark.parametrize("temperature,energy", [
    (np.array([0.1, 0.3, 1.0, 5.0, 50.0, 500.0, 5000.0, 20100.0, 40000.0]),
     np.array([0.15, 0.7, 3.0, 30.0, 300.0, 3000.0, 20100.0, 1.0, 60000.0])),
    (np.logspace(0, 3, 12).reshape(3, 4),
     np.logspace(-1, 3, 12).reshape(3, 4)),
])
def test_saved_finite_fit_replays_exactly(temperature, energy):
    np.testing.assert_array_equal(
        evaluate_atomic_hydrogen_charge_exchange_rate(temperature, energy),
        _saved()(temperature, energy),
    )


@pytest.mark.parametrize("temperature,energy", [
    (np.array([-5.0]), np.array([1.0])),
    (np.array([2.0]), np.array([-1.0])),
    (np.array([True]), np.array([1.0])),
])
def test_saved_coercion_or_clipping_is_rejected_by_maintained_contract(
    temperature, energy,
):
    assert np.isfinite(_saved()(temperature, energy)).all()
    with pytest.raises(ValueError):
        evaluate_atomic_hydrogen_charge_exchange_rate(temperature, energy)
