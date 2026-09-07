import numpy as np
import pytest

from scirel.field.permanent_ring_filaments import discretize_permanent_ring, discretize_permanent_ring as scientific_operator


# 验证：未旋转时必须保持两侧各 8 条、linspace Z 顺序和 source-default signs。
def test_unrotated_source_layout_and_default_weight_signs():
    result = scientific_operator(2.0, 3.0, 4.0, 2.0)
    expected_z = np.linspace(2.0, 4.0, 8)
    np.testing.assert_allclose(result["rz_pts"][:8, 0], 0.0)
    np.testing.assert_allclose(result["rz_pts"][8:, 0], 4.0)
    np.testing.assert_allclose(result["rz_pts"][:8, 1], expected_z)
    np.testing.assert_allclose(result["rz_pts"][8:, 1], expected_z)
    np.testing.assert_allclose(result["default_weights"][:8], -1.0)
    np.testing.assert_allclose(result["default_weights"][8:], 1.0)


# 验证：90 degree 正角按 source row-vector 矩阵使左侧中点转到 centroid 上方（顺时针 R--Z 图约定）。
def test_rotation_is_about_centroid_with_source_row_vector_direction():
    result = scientific_operator(2.0, 3.0, 4.0, 2.0, mu_hat_deg=90.0)
    # Original first point (0,2); relative vector (-2,-1) -> (-1,2) by row-vector matrix.
    np.testing.assert_allclose(result["rz_pts"][0], [1.0, 5.0], atol=1.0e-14)
    # The centroid remains invariant under rotation.
    np.testing.assert_allclose(np.mean(result["rz_pts"], axis=0), [2.0, 3.0], atol=1.0e-14)


# 验证：非正矩形尺寸不是可用的 source geometry，必须在资产边界 fail closed。
@pytest.mark.parametrize("width,height", [(0.0, 1.0), (1.0, 0.0), (-1.0, 1.0)])
def test_rejects_degenerate_or_negative_dimensions(width, height):
    with pytest.raises(ValueError):
        scientific_operator(1.0, 0.0, width, height)


def test_reviewed_relation_example():
    import numpy as np
    from scirel.field.permanent_ring_filaments import discretize_permanent_ring

    result = discretize_permanent_ring(2.0, 3.0, 4.0, 2.0)
    expected_z = np.linspace(2.0, 4.0, 8)
    np.testing.assert_allclose(result["rz_pts"][:8, 0], 0.0)
    np.testing.assert_allclose(result["rz_pts"][8:, 0], 4.0)
    np.testing.assert_allclose(result["rz_pts"][:8, 1], expected_z)
    np.testing.assert_allclose(result["rz_pts"][8:, 1], expected_z)
    np.testing.assert_allclose(result["default_weights"][:8], -1.0)
    np.testing.assert_allclose(result["default_weights"][8:], 1.0)
    assert np.sum(result["default_weights"]) == 0.0
    rotated = discretize_permanent_ring(2.0, 3.0, 4.0, 2.0, mu_hat_deg=90.0)
    np.testing.assert_allclose(rotated["rz_pts"][0], [1.0, 5.0], atol=1.0e-14)
    np.testing.assert_allclose(np.mean(rotated["rz_pts"], axis=0), [2.0, 3.0], atol=1.0e-14)
