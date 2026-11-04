"""Optional SHA-gated replay of the saved KN1DPy Janev ionization fits."""

from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path

import numpy as np
import pytest

from scirel.collisions import evaluate_janev_electron_impact_ionization_rate


_SHA256 = "ff9b5f5cf854870608ce9e7e7ec8effe8718dbf5ddfa16b1bc90f42df908e3d1"


def _saved():
    root = os.environ.get("SCIREL_KN1DPY_REVIEW_ROOT")
    if not root:
        pytest.skip("SCIREL_KN1DPY_REVIEW_ROOT is not set")
    source = (Path(root) / "operators" / "Janev电子碰撞电离率"
              / "scientific_operator.py")
    assert source.is_file()
    assert hashlib.sha256(source.read_bytes()).hexdigest() == _SHA256
    spec = importlib.util.spec_from_file_location("saved_janev_ionization", source)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.evaluate_janev_electron_impact_ionization_rate


@pytest.mark.parametrize("species", ["H", "H2"])
def test_saved_finite_fit_replays_exactly(species):
    temperature = np.logspace(-2, 5, 32).reshape(8, 4)
    np.testing.assert_array_equal(
        evaluate_janev_electron_impact_ionization_rate(temperature, species),
        _saved()(temperature, species),
    )


@pytest.mark.parametrize("temperature", [-1.0, True, "10.0"])
def test_saved_clipping_or_coercion_is_rejected(temperature):
    assert np.isfinite(_saved()(temperature, "H")).all()
    with pytest.raises(ValueError):
        evaluate_janev_electron_impact_ionization_rate(temperature, "H")
