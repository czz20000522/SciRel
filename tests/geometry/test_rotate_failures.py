"""The rotate shape contract also applies before a last-axis index exists."""

import numpy as np
import pytest

from scirel.geometry import rotate


@pytest.mark.parametrize("mode", ("warn", "ignore", "raise"))
@pytest.mark.parametrize(
    "points,angle,pivot",
    [
        ([[1e308, 1e308]], 0.0, (-1e308, -1e308)),
        ([[1.3e308, 1.3e308]], 45.0, (0.0, 0.0)),
        ([[0.0, 0.0]], 180.0, (1e308, 0.0)),
    ],
)
def test_finite_rotation_overflow_raises_without_mutating_inputs(mode, points, angle, pivot):
    points = np.array(points)
    pivot = np.array(pivot)
    before_points, before_pivot = points.copy(), pivot.copy()
    points.flags.writeable = pivot.flags.writeable = False
    with np.errstate(over=mode, invalid=mode):
        settings = np.geterr()
        with pytest.raises(FloatingPointError):
            rotate(points, angle, pivot)
        assert np.geterr() == settings
    np.testing.assert_array_equal(points, before_points)
    np.testing.assert_array_equal(pivot, before_pivot)


@pytest.mark.parametrize("mode", ("warn", "ignore", "raise"))
@pytest.mark.parametrize("bad", (np.nan, np.inf, -np.inf))
@pytest.mark.parametrize("parameter", ("pts", "pivot", "angle"))
def test_nonfinite_rotation_input_still_raises_value_error(mode, bad, parameter):
    arguments = {"pts": [[1.0, 0.0]], "angle": 0.0, "pivot": (0.0, 0.0)}
    arguments[parameter] = bad if parameter == "angle" else [bad, 0.0]
    with np.errstate(over=mode, invalid=mode):
        with pytest.raises(ValueError, match="finite"):
            rotate(**arguments)


@pytest.mark.parametrize("mode", ("warn", "ignore", "raise"))
@pytest.mark.parametrize("shape", ((2,), (0, 2), (2, 0, 2), (2, 2), (2, 3, 2)))
@pytest.mark.parametrize("dtype", (np.int64, np.float32, np.float64))
def test_representable_rotation_preserves_values_shape_and_float64(mode, shape, dtype):
    points = np.ones(shape, dtype=dtype)
    before = points.copy()
    points.flags.writeable = False
    with np.errstate(over=mode, invalid=mode):
        result = rotate(points, 0.0, pivot=(0.5, -0.5))
    assert result.shape == shape
    assert result.dtype == np.dtype(np.float64)
    np.testing.assert_array_equal(result, before)
    np.testing.assert_array_equal(points, before)


@pytest.mark.parametrize("mode", ("warn", "ignore", "raise"))
def test_large_representable_rotation_is_not_rejected(mode):
    points = np.array([[1e308, -1e308]])
    pivot = np.array([1e308, -1e308])
    with np.errstate(over=mode, invalid=mode):
        result = rotate(points, 90.0, pivot)
    np.testing.assert_array_equal(result, points)
    assert result.dtype == np.dtype(np.float64)


@pytest.mark.parametrize("point", (1.0, np.array(1.0), np.array(1.0, dtype=object)))
def test_scalar_points_raise_the_declared_shape_error(point):
    with pytest.raises(ValueError, match="final dimension"):
        rotate(point, 0.0)


@pytest.mark.parametrize("shape", ((2,), (0, 2), (2, 2), (2, 3, 2)))
def test_valid_last_axis_is_preserved_for_single_empty_and_batched_points(shape):
    points = np.zeros(shape)
    before = points.copy()
    result = rotate(points, 0.0)
    assert result.shape == shape
    np.testing.assert_array_equal(result, before)
    np.testing.assert_array_equal(points, before)
