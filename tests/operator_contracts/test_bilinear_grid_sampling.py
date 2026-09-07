import numpy as np
import pytest

from scirel.geometry.bilinear_grid_sampling import sample_rectilinear_field, sample_rectilinear_field as scientific_operator


def _grid():
    r_grid, z_grid = np.meshgrid(np.array([1.0, 2.0, 4.0]), np.array([-1.0, 1.0]))
    return r_grid, z_grid, 3.0 * r_grid - 2.0 * z_grid + 1.0


# 验证：双线性插值必须精确恢复线性 R-Z 场，并保持 quantity[Z,R] 轴序。
def test_recovers_linear_field_at_interior_and_grid_points():
    r_grid, z_grid, quantity = _grid()
    points = np.array([[1.5, 0.0], [4.0, 1.0]])
    result = scientific_operator(r_grid, z_grid, quantity, points)
    assert np.allclose(result["samples"], [5.5, 11.0])


# 验证：越出边界的诊断点不得被静默夹取。
def test_rejects_outside_diagnostic_point():
    r_grid, z_grid, quantity = _grid()
    with pytest.raises(ValueError):
        scientific_operator(r_grid, z_grid, quantity, np.array([[0.9, 0.0]]))


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
