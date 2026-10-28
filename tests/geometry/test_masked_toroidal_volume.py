"""Direct regression tests for the explicit masked toroidal-volume relation."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from scirel.geometry import plasma_volume


_FIXTURE = json.loads(
    (Path(__file__).parents[1] / "fixtures/geometry/masked_toroidal_volume.json")
    .read_text(encoding="utf-8")
)


def _array(spec):
    values = spec["values"]
    dtype = np.bool_ if spec["dtype"] == "bool" else np.dtype(spec["dtype"])
    return np.asarray(values, dtype=dtype).reshape(spec["shape"])


@pytest.mark.parametrize("case", _FIXTURE["cases"], ids=lambda case: case["id"])
def test_declared_finite_grid_rows(case):
    if "mask" not in case:
        pytest.skip("state-only source row has no explicit public mask")
    R = _array(case["R"])
    mask = _array(case["mask"])
    if case["id"] == "mask_shape_failure":
        with pytest.raises(ValueError):
            plasma_volume(R, float(case["dR"]), float(case["dZ"]), mask)
        return
    expected = float(np.sum(2.0 * np.pi * R * float(case["dR"]) * float(case["dZ"]) * mask))
    with np.errstate(all="ignore"):
        observed = plasma_volume(R, float(case["dR"]), float(case["dZ"]), mask)
    if np.isnan(expected):
        assert np.isnan(observed)
    elif np.isposinf(expected):
        assert np.isposinf(observed)
    elif np.isneginf(expected):
        assert np.isneginf(observed)
    else:
        assert observed == expected


def test_mask_shape_failure_propagates_numpy_broadcast_error():
    case = next(case for case in _FIXTURE["cases"] if case["id"] == "mask_shape_failure")
    with pytest.raises(ValueError):
        plasma_volume(_array(case["R"]), float(case["dR"]), float(case["dZ"]), _array(case["mask"]))


def test_numeric_mask_and_zero_mask_preserve_measurement():
    R = np.array([[1.0, 1.5], [2.0, 2.5]])
    mask = np.array([[0.25, 0.0], [1.0, -0.5]])
    expected = 2.0 * np.pi * np.sum(R * mask) * 0.2 * 0.4
    assert plasma_volume(R, 0.2, 0.4, mask) == expected


def test_scalar_projection_is_float_and_inputs_are_not_mutated():
    R = np.array([[1.0, 2.0]], dtype=np.float32)
    mask = np.array([[True, False]])
    R_before, mask_before = R.copy(), mask.copy()
    result = plasma_volume(R, 0.5, 0.25, mask)
    assert isinstance(result, float)
    np.testing.assert_array_equal(R, R_before)
    np.testing.assert_array_equal(mask, mask_before)


def test_contract_example_value():
    R = np.array([[1.0, 1.0], [2.0, 2.0]])
    mask = np.array([[True, False], [True, False]])
    np.testing.assert_allclose(
        plasma_volume(R, 0.5, 0.25, mask),
        2.0 * np.pi * (1.0 + 2.0) * 0.5 * 0.25,
    )
