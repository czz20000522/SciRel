"""The rotate shape contract also applies before a last-axis index exists."""

import numpy as np
import pytest

from scirel.geometry import rotate


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
