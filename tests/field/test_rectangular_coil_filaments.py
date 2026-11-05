import numpy as np
import pytest

from scirel.field.rectangular_coil_filaments import (
    discretize_rectangular_coil,
    discretize_rectangular_coil as scientific_function,
)


# 验证：未旋转时 source 的 for-ri/for-zi 顺序，Z 是内层索引而非 meshgrid 默认展平顺序。
def test_unrotated_rectangular_coil_preserves_source_filament_order():
    result = scientific_function(1.0, 2.0, nr=2, nz=3, dr=0.4, dz=0.2)
    expected = np.array([[0.8, 1.8], [0.8, 2.0], [0.8, 2.2], [1.2, 1.8], [1.2, 2.0], [1.2, 2.2]])
    np.testing.assert_allclose(result, expected)


# 验证：正 90 度按源码 row-vector 旋转；R 正方向的点绕质心转到负 Z 方向。
def test_positive_ninety_degree_rotation_uses_source_row_vector_sign():
    result = scientific_function(1.0, 2.0, nr=2, nz=1, dr=0.4, dz=0.2, angle_deg=90.0)
    np.testing.assert_allclose(result, np.array([[1.0, 2.2], [1.0, 1.8]]), atol=1.0e-14)


@pytest.mark.parametrize("keyword,value", [("nr", 0), ("nz", 1.5), ("dr", 0.0), ("dz", -0.1)])
# 验证：物理离散数量和间距不合法时 fail closed，避免产生空或反向矩形截面。
def test_rejects_invalid_filament_counts_or_spacings(keyword, value):
    values = {"r0": 1.0, "z0": 0.0, "nr": 2, "nz": 2, "dr": 0.1, "dz": 0.1}
    values[keyword] = value
    with pytest.raises(ValueError):
        scientific_function(**values)


def test_reviewed_relation_example():
    import numpy as np

    points = discretize_rectangular_coil(1.0, 2.0, nr=2, nz=3, dr=0.4, dz=0.2)
    expected = np.array(
        [
            [0.8, 1.8],
            [0.8, 2.0],
            [0.8, 2.2],
            [1.2, 1.8],
            [1.2, 2.0],
            [1.2, 2.2],
        ]
    )
    np.testing.assert_allclose(points, expected)
    assert np.isclose(np.ptp(points[:, 0]), (2 - 1) * 0.4)
    assert np.isclose(np.ptp(points[:, 1]), (3 - 1) * 0.2)
    rotated = discretize_rectangular_coil(1.0, 2.0, nr=2, nz=1, dr=0.4, dz=0.2, angle_deg=90.0)
    np.testing.assert_allclose(rotated, [[1.0, 2.2], [1.0, 1.8]], atol=1.0e-14)
