import numpy as np
import pytest

from scirel.geometry.bilinear_grid_sampling import sample_rectilinear_field, sample_rectilinear_field as scientific_function


def _grid():
    r_grid, z_grid = np.meshgrid(np.array([1.0, 2.0, 4.0]), np.array([-1.0, 1.0]))
    return r_grid, z_grid, 3.0 * r_grid - 2.0 * z_grid + 1.0


# 验证：双线性插值必须精确恢复线性 R-Z 场，并保持 quantity[Z,R] 轴序。
def test_recovers_linear_field_at_interior_and_grid_points():
    r_grid, z_grid, quantity = _grid()
    points = np.array([[1.5, 0.0], [4.0, 1.0]])
    result = scientific_function(r_grid, z_grid, quantity, points)
    assert np.allclose(result["samples"], [5.5, 11.0])


# 验证：越出边界的诊断点不得被静默夹取。
def test_rejects_outside_diagnostic_point():
    r_grid, z_grid, quantity = _grid()
    with pytest.raises(ValueError):
        scientific_function(r_grid, z_grid, quantity, np.array([[0.9, 0.0]]))


def test_empty_query_and_invalid_later_point():
    r_grid, z_grid, quantity = _grid()
    result = scientific_function(r_grid, z_grid, quantity, np.empty((0, 2)))
    assert result["samples"].shape == (0,)

    with pytest.raises(ValueError, match="outside the R-Z grid"):
        scientific_function(r_grid, z_grid, quantity, [[1.5, 0.0], [4.1, 0.0]])


def test_reviewed_relation_example():
    from scirel.geometry.bilinear_grid_sampling import sample_rectilinear_field
    import numpy as np

    r_axis = np.array([1.0, 2.0, 4.0])
    z_axis = np.array([-1.0, 1.0, 2.0])
    R, Z = np.meshgrid(r_axis, z_axis)
    quantity = R * Z
    points = np.array([[1.5, 0.5], [3.0, -0.5]])
    result = sample_rectilinear_field(R, Z, quantity, points)
    np.testing.assert_allclose(result["samples"], points[:, 0] * points[:, 1])
    assert result["samples"].shape == (2,)


def test_nonseparable_field_matches_independent_four_corner_oracle():
    r_axis = np.array([0.0, 0.4, 1.7, 3.0])
    z_axis = np.array([-2.0, -0.5, 0.25, 1.0])
    r_grid, z_grid = np.meshgrid(r_axis, z_axis)
    quantity = np.array(
        [
            [0.2, -1.0, 2.5, 0.7],
            [1.4, 3.1, -0.2, 4.0],
            [-2.0, 0.4, 1.6, -3.2],
            [5.0, -0.8, 2.2, 1.1],
        ]
    )
    points = np.array([[0.2, -1.25], [1.1, 0.1], [2.6, 0.8], [3.0, 1.0]])

    expected = []
    for r_value, z_value in points:
        ri = int(np.clip(np.searchsorted(r_axis, r_value) - 1, 0, r_axis.size - 2))
        zi = int(np.clip(np.searchsorted(z_axis, z_value) - 1, 0, z_axis.size - 2))
        rf = (r_value - r_axis[ri]) / (r_axis[ri + 1] - r_axis[ri])
        zf = (z_value - z_axis[zi]) / (z_axis[zi + 1] - z_axis[zi])
        expected.append(
            (1.0 - rf) * (1.0 - zf) * quantity[zi, ri]
            + rf * (1.0 - zf) * quantity[zi, ri + 1]
            + (1.0 - rf) * zf * quantity[zi + 1, ri]
            + rf * zf * quantity[zi + 1, ri + 1]
        )

    result = scientific_function(r_grid, z_grid, quantity, points)
    np.testing.assert_allclose(result["samples"], expected, rtol=0.0, atol=1e-14)
