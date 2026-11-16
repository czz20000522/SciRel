import numpy as np
import pytest
from fractions import Fraction

from scirel._result import Result

from scirel.numerics.interpolate.bilinear_grid_sampling import (
    sample_rectilinear_field,
    sample_rectilinear_field as scientific_function,
)


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


# 验证：返回的是单键命名结果，映射取值与属性取值为同一数组。
def test_returns_a_named_single_key_result_mapping():
    r_grid, z_grid, quantity = _grid()
    result = scientific_function(r_grid, z_grid, quantity, np.array([[1.5, 0.0]]))
    assert type(result) is Result
    assert isinstance(result, dict)
    assert list(result) == ["samples"]
    assert result.samples is result["samples"]
    assert result.samples.shape == (1,)
    assert result.samples.dtype == np.float64


def test_empty_query_and_invalid_later_point():
    r_grid, z_grid, quantity = _grid()
    result = scientific_function(r_grid, z_grid, quantity, np.empty((0, 2)))
    assert result["samples"].shape == (0,)

    with pytest.raises(ValueError, match="outside the R-Z grid"):
        scientific_function(r_grid, z_grid, quantity, [[1.5, 0.0], [4.1, 0.0]])


def test_reviewed_relation_example():
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


@pytest.mark.parametrize("r_sign,z_sign", [(1.0, 1.0), (-1.0, 1.0), (1.0, -1.0)])
def test_affine_center_survives_an_overflowing_coordinate_span(r_sign, z_sign):
    """The center of a symmetric finite interval has exact half weights."""
    r_axis = np.array([-1e308, 1e308])
    z_axis = np.array([-1e308, 1e308])
    r_grid, z_grid = np.meshgrid(r_axis, z_axis)
    values = r_sign * np.array([[-1.0, 1.0], [-1.0, 1.0]])
    values += z_sign * np.array([[-1.0, -1.0], [1.0, 1.0]])
    with np.errstate(all="raise"):
        result = scientific_function(r_grid, z_grid, values, [[0.0, 0.0]])
    np.testing.assert_allclose(result["samples"], [0.0], rtol=0.0, atol=1e-14)


def test_overflowing_z_span_preserves_original_center_witness():
    r_grid, z_grid = np.meshgrid([1.0, 2.0], [-1e308, 1e308])
    with np.errstate(all="raise"):
        result = scientific_function(r_grid, z_grid, [[-1.0, -1.0], [1.0, 1.0]], [[1.5, 0.0]])
    np.testing.assert_allclose(result["samples"], [0.0], rtol=0.0, atol=1e-14)


def test_tiny_coordinate_fraction_keeps_its_representable_field_contribution():
    large = float.fromhex("0x1p+1023")
    small = float.fromhex("0x1p-1022")
    r_grid, z_grid = np.meshgrid([0.0, large], [0.0, 1.0])
    with np.errstate(all="raise"):
        result = scientific_function(r_grid, z_grid, [[0.0, large], [0.0, large]], [[small, 0.5]])
    np.testing.assert_allclose(result["samples"], [small], rtol=1e-14, atol=0.0)


def test_tiny_tensor_product_weight_can_have_a_finite_contribution():
    axis = [0.0, float.fromhex("0x1p+600")]
    r_grid, z_grid = np.meshgrid(axis, axis)
    # q(R,Z)=2^-200 R Z. Each coordinate fraction is 2^-600;
    # their product underflows, but multiplying by q11=2^1000 gives 2^-200.
    with np.errstate(all="raise"):
        result = scientific_function(
            r_grid,
            z_grid,
            [[0.0, 0.0], [0.0, float.fromhex("0x1p+1000")]],
            [[1.0, 1.0]],
        )
    np.testing.assert_allclose(result["samples"], [float.fromhex("0x1p-200")], rtol=1e-14, atol=0.0)


def test_constant_maximum_field_remains_finite_at_interior_and_nodes():
    r_grid, z_grid = np.meshgrid([0.0, 1.0], [0.0, 1.0])
    maximum = np.finfo(float).max
    points = [[0.1, 0.1], [0.5, 0.5], [0.0, 0.0], [1.0, 1.0]]
    with np.errstate(all="raise"):
        result = scientific_function(r_grid, z_grid, np.full((2, 2), maximum), points)
    np.testing.assert_allclose(result["samples"], maximum, rtol=1e-14, atol=0.0)


def test_near_endpoint_keeps_the_small_complementary_weight():
    left, right = 0.3, 1.1
    query = np.nextafter(right, left)
    height = 1e300
    # This affine field falls to zero at the right endpoint. Form its value
    # directly from the original coordinate differences, not 1-rounded_fraction.
    expected = float(
        (Fraction(right) - Fraction(float(query)))
        * Fraction(height)
        / (Fraction(right) - Fraction(left))
    )
    r_grid, z_grid = np.meshgrid([left, right], [0.0, 1.0])
    result = scientific_function(r_grid, z_grid, [[height, 0.0], [height, 0.0]], [[query, 0.5]])
    np.testing.assert_allclose(result["samples"], [expected], rtol=1e-14, atol=0.0)


def test_large_opposite_corners_do_not_erase_the_small_net_sample():
    r_grid, z_grid = np.meshgrid([0.0, 1.0], [0.0, 1.0])
    # At the center each corner contributes one quarter, so cancellation leaves
    # exactly 1/4 despite the two opposite 1e300 corner values.
    result = scientific_function(r_grid, z_grid, [[1e300, 1.0], [-1e300, 0.0]], [[0.5, 0.5]])
    np.testing.assert_allclose(result["samples"], [0.25], rtol=1e-14, atol=0.0)
