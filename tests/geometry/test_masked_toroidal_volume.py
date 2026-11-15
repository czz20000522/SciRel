"""Direct regression tests for the explicit masked toroidal-volume relation."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from scirel.geometry import plasma_volume


_FIXTURE = json.loads(
    (Path(__file__).parents[1] / "fixtures/geometry/masked_toroidal_volume.json").read_text(
        encoding="utf-8"
    )
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


def test_broadcast_radius_column_across_mask_cells():
    radius = np.array([[1.0], [2.0]])
    mask = np.ones((2, 3), dtype=bool)
    # Six cells: three at R=1 and three at R=2. Independent ring-cell measure.
    expected = 2.0 * np.pi * (3.0 * 1.0 + 3.0 * 2.0) * 0.5 * 0.25
    actual = plasma_volume(radius, 0.5, 0.25, mask)
    np.testing.assert_allclose(actual, expected, rtol=1e-14, atol=0.0)


@pytest.mark.parametrize(
    "radius, mask, weighted_radius_sum",
    [
        ([[1.0, 1.0, 1.0], [2.0, 2.0, 2.0]], [[True], [False]], 3.0),
        ([[1.0], [2.0]], [[True, False, True]], 6.0),
        ([1.0, 2.0, 3.0], [[True], [False]], 6.0),
        ([[1.0], [2.0]], [[[True, False, True]], [[False, True, False]]], 9.0),
        (2.0, [[True, False], [True, True]], 6.0),
        ([[1.0, 2.0]], True, 3.0),
        ([[1.0], [2.0]], np.empty((2, 0), dtype=bool), 0.0),
    ],
    ids=[
        "mask-column-expands",
        "both-operands-expand",
        "radius-vector-expands",
        "mask-adds-leading-axis",
        "scalar-radius-expands",
        "scalar-mask-expands",
        "empty-common-shape",
    ],
)
def test_broadcast_cell_sums_preserve_inputs_and_float(radius, mask, weighted_radius_sum):
    R = np.asarray(radius, dtype=float)
    core_mask = np.asarray(mask, dtype=bool)
    R_before, mask_before = R.copy(), core_mask.copy()
    R.flags.writeable = core_mask.flags.writeable = False
    # Independently counted included radii, before applying the ring-cell measure.
    expected = 2.0 * np.pi * weighted_radius_sum * 0.5 * 0.25

    result = plasma_volume(R, 0.5, 0.25, core_mask)

    assert isinstance(result, float)
    np.testing.assert_allclose(result, expected, rtol=1e-14, atol=0.0)
    np.testing.assert_array_equal(R, R_before)
    np.testing.assert_array_equal(core_mask, mask_before)


@pytest.mark.parametrize("dtype", [np.int64, np.float32, np.float64])
@pytest.mark.parametrize(
    "weights, weighted_radius_sum",
    [([-1, 0, 2], 3.0), ([-2, 0, 1], -3.0), ([-1, 0, 1], 0.0)],
    ids=["positive-sum", "negative-sum", "cancellation"],
)
def test_broadcast_signed_weights_are_not_clipped(dtype, weights, weighted_radius_sum):
    R = np.array([[1.0], [2.0]])
    mask = np.array([weights], dtype=dtype)
    R_before, mask_before = R.copy(), mask.copy()
    # Each weight applies to both radii: (1 + 2) times the sum of the weights.
    expected = 2.0 * np.pi * weighted_radius_sum * 0.5 * 0.25

    result = plasma_volume(R, 0.5, 0.25, mask)

    assert isinstance(result, float)
    np.testing.assert_allclose(result, expected, rtol=1e-14, atol=0.0)
    np.testing.assert_array_equal(R, R_before)
    np.testing.assert_array_equal(mask, mask_before)


@pytest.mark.parametrize("radius_shape, mask_shape", [((2, 1), (3, 3)), ((2, 3), (2, 2))])
def test_truly_incompatible_shapes_raise_without_mutating_inputs(radius_shape, mask_shape):
    R = np.ones(radius_shape)
    mask = np.ones(mask_shape, dtype=bool)
    R_before, mask_before = R.copy(), mask.copy()

    with pytest.raises(ValueError):
        plasma_volume(R, 0.5, 0.25, mask)

    np.testing.assert_array_equal(R, R_before)
    np.testing.assert_array_equal(mask, mask_before)


@pytest.mark.parametrize(
    "radius, weights, dR, dZ, expected",
    [
        (np.nan, [1.0, 1.0, 1.0], 0.5, 0.25, np.nan),
        (np.inf, [1.0, 1.0, 1.0], 0.5, 0.25, np.inf),
        (-np.inf, [1.0, 1.0, 1.0], 0.5, 0.25, -np.inf),
        (np.inf, [1.0, 0.0, 1.0], 0.5, 0.25, np.nan),
        (1.0, [1.0, np.nan, 1.0], 0.5, 0.25, np.nan),
        (1.0, [1.0, np.inf, 1.0], 0.5, 0.25, np.inf),
        (1.0, [1.0, -np.inf, 1.0], 0.5, 0.25, -np.inf),
        (1.0, [1.0, 1.0, 1.0], np.nan, 0.25, np.nan),
        (1.0, [1.0, 1.0, 1.0], 0.5, np.inf, np.inf),
    ],
    ids=[
        "nan-radius",
        "positive-infinite-radius",
        "negative-infinite-radius",
        "infinity-times-zero-weight",
        "nan-weight",
        "positive-infinite-weight",
        "negative-infinite-weight",
        "nan-radial-spacing",
        "infinite-vertical-spacing",
    ],
)
def test_broadcast_nonfinite_arithmetic_propagates(radius, weights, dR, dZ, expected):
    R = np.array([[radius], [2.0]])
    mask = np.array([weights])
    R_before, mask_before = R.copy(), mask.copy()

    with np.errstate(invalid="ignore"):
        result = plasma_volume(R, dR, dZ, mask)

    assert isinstance(result, float)
    if np.isnan(expected):
        assert np.isnan(result)
    else:
        assert result == expected
    np.testing.assert_array_equal(R, R_before)
    np.testing.assert_array_equal(mask, mask_before)
