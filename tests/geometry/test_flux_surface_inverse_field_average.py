# 测试命令：python -m pytest test_scientific_function.py -q -p no:cacheprovider
import numpy as np
import pytest

from scirel.geometry.flux_surface_inverse_field_average import (
    compute_flux_surface_inverse_field_average,
    compute_flux_surface_inverse_field_average as scientific_function,
)


def _inputs():
    r = np.linspace(0.0, 1.0, 5)
    z = np.linspace(-1.0, 1.0, 5)
    R, Z = np.meshgrid(r, z)
    line = np.array([[0.2, -0.5], [0.4, 0.0], [0.6, 0.5]])
    return R, Z, line


def test_constant_field_has_analytic_inverse_b_measure_and_average():
    R, Z, line = _inputs()
    result = scientific_function(R, Z, np.full_like(R, 2.0), line, np.full_like(R, 3.0))
    length = float(np.sum(np.linalg.norm(np.diff(line, axis=0), axis=1)))
    assert result["dl_B"] == pytest.approx(length / 2.0)
    assert result["flux_surface_average"] == pytest.approx(3.0)


def test_quantity_is_optional_and_no_quantity_returns_only_measure():
    R, Z, line = _inputs()
    result = scientific_function(R, Z, np.full_like(R, 4.0), line)
    assert set(result) == {"dl_B"}
    length = float(np.sum(np.linalg.norm(np.diff(line, axis=0), axis=1)))
    assert result["dl_B"] == pytest.approx(length / 4.0)


def test_rejects_nonpositive_field_and_outside_line():
    R, Z, line = _inputs()
    with pytest.raises(ValueError, match="strictly positive"):
        scientific_function(R, Z, np.zeros_like(R), line)
    with pytest.raises(ValueError, match="inside"):
        scientific_function(R, Z, np.full_like(R, 2.0), [[-0.1, 0.0], [0.2, 0.0]])


def test_reviewed_relation_example():
    from scirel.geometry.flux_surface_inverse_field_average import (
        compute_flux_surface_inverse_field_average,
    )
    import numpy as np

    r = np.linspace(0.0, 1.0, 5)
    z = np.linspace(-1.0, 1.0, 5)
    R, Z = np.meshgrid(r, z)
    B = 1.0 + R
    line = np.array([[0.0, 0.0], [0.5, 0.0], [1.0, 0.0]])
    result = compute_flux_surface_inverse_field_average(R, Z, B, line, B)
    np.testing.assert_allclose(result["dl_B"], 17.0 / 24.0, rtol=1e-12)
    np.testing.assert_allclose(result["flux_surface_average"], 24.0 / 17.0, rtol=1e-12)

    # 反向遍历同一折线不改变 dl/B 或加权平均；端点位于网格边界。
    reversed_result = compute_flux_surface_inverse_field_average(R, Z, B, line[::-1], B)
    np.testing.assert_allclose(reversed_result["dl_B"], result["dl_B"], rtol=1e-12)
    np.testing.assert_allclose(
        reversed_result["flux_surface_average"], result["flux_surface_average"], rtol=1e-12
    )

    # 常磁场下 dl/B 应退化为折线总长度除以 B。
    polyline = np.array([[0.0, -1.0], [0.5, 0.0], [1.0, -1.0]])
    constant = compute_flux_surface_inverse_field_average(R, Z, np.full_like(R, 2.0), polyline)
    expected_length = 2.0 * np.sqrt(0.5**2 + 1.0**2)
    np.testing.assert_allclose(constant["dl_B"], expected_length / 2.0, rtol=1e-12)


def test_review_gate_rejects_degenerate_path_and_undersized_cubic_grid():
    import numpy as np
    import pytest

    r = np.linspace(0.0, 1.0, 4)
    z = np.linspace(-1.0, 1.0, 4)
    r_grid, z_grid = np.meshgrid(r, z)
    magnetic_field = np.ones_like(r_grid)
    repeated = np.array([[0.5, 0.0], [0.5, 0.0]])
    with pytest.raises(ValueError, match="nondegenerate polyline"):
        compute_flux_surface_inverse_field_average(r_grid, z_grid, magnetic_field, repeated)

    small_r_grid, small_z_grid = np.meshgrid(np.linspace(0.0, 1.0, 3), z)
    with pytest.raises(ValueError, match="at least four points per axis"):
        compute_flux_surface_inverse_field_average(
            small_r_grid,
            small_z_grid,
            np.ones_like(small_r_grid),
            np.array([[0.0, 0.0], [1.0, 0.0]]),
        )
