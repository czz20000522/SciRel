"""Optional SHA-gated replay of the saved KN1DPy H(1s) recombination fit."""

from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path

import numpy as np
import pytest

from scirel.collisions import evaluate_atomic_hydrogen_1s_radiative_recombination_rate


_SHA256 = "ad71a46c865380793ee73e4ae267d536f0e0c8384929b1fff4bb18000c2e2528"


def _saved():
    root = os.environ.get("SCIREL_KN1DPY_REVIEW_ROOT")
    if not root:
        pytest.skip("SCIREL_KN1DPY_REVIEW_ROOT is not set")
    source = (Path(root) / "operators" / "原子氢1s辐射复合速率"
              / "scientific_operator.py")
    assert source.is_file()
    assert hashlib.sha256(source.read_bytes()).hexdigest() == _SHA256
    spec = importlib.util.spec_from_file_location("saved_h1s_recombination", source)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.evaluate_atomic_hydrogen_1s_radiative_recombination_rate


@pytest.mark.parametrize("temperature", [
    np.array([0.1, 0.3, 1.0, 5.0, 50.0, 500.0, 5000.0, 20100.0, 40000.0]),
    np.logspace(-1, 4, 12).reshape(3, 4),
])
def test_saved_finite_fit_replays_exactly(temperature):
    np.testing.assert_array_equal(
        evaluate_atomic_hydrogen_1s_radiative_recombination_rate(temperature),
        _saved()(temperature),
    )


@pytest.mark.parametrize("temperature", [-5.0, True, "10.0"])
def test_saved_clipping_or_coercion_is_rejected(temperature):
    assert np.isfinite(_saved()(temperature)).all()
    with pytest.raises(ValueError):
        evaluate_atomic_hydrogen_1s_radiative_recombination_rate(temperature)
