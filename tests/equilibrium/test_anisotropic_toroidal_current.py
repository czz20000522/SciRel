import numpy as np
import pytest

from scirel.equilibrium.anisotropic_toroidal_current import (
    compute_anisotropic_toroidal_current,
    compute_anisotropic_toroidal_current as scientific_function,
)


def _grid():
    return np.meshgrid(np.linspace(0.2, 0.5, 5), np.linspace(-0.2, 0.2, 4))


# 验证：恒定压强且均匀磁场时，两个物理贡献都必须为零。
def test_constant_pressure_has_zero_toroidal_current():
    r_grid, z_grid = _grid()
    result = scientific_function(
        r_grid,
        z_grid,
        np.zeros_like(r_grid),
        np.ones_like(r_grid),
        np.ones_like(r_grid),
        np.ones_like(r_grid),
    )
    assert np.allclose(result["gradp_term"], 0.0)
    assert np.allclose(result["anisotropy_curvature_term"], 0.0)
    assert np.allclose(result["j_phi"], 0.0)


# 验证：BR=0、BZ=1 时 p_perp=R 的压力梯度项应为 d(p_perp)/dR=1。
def test_radial_perpendicular_pressure_gradient_sets_gradp_term():
    r_grid, z_grid = _grid()
    result = scientific_function(
        r_grid, z_grid, np.zeros_like(r_grid), np.ones_like(r_grid), r_grid, r_grid
    )
    assert np.allclose(result["gradp_term"], 1.0)
    assert np.allclose(result["anisotropy_curvature_term"], 0.0)
    assert np.allclose(result["j_phi"], 1.0)


def test_axis_column_and_negative_pressure_contract():
    r_grid, z_grid = np.meshgrid(np.linspace(0.0, 0.4, 5), np.linspace(-0.2, 0.2, 4))
    br = np.zeros_like(r_grid)
    bz = np.ones_like(r_grid)
    pressure = 1.0 + r_grid
    result = scientific_function(r_grid, z_grid, br, bz, pressure, pressure)
    np.testing.assert_array_equal(result["j_phi"][:, 0], 0.0)
    np.testing.assert_array_equal(result["gradp_term"][:, 0], 0.0)
    np.testing.assert_array_equal(result["anisotropy_curvature_term"][:, 0], 0.0)

    with pytest.raises(ValueError, match="grid axes and pressures"):
        scientific_function(r_grid, z_grid, br, bz, -pressure, pressure)


def test_reviewed_relation_example():
    import numpy as np

    r_grid, z_grid = np.meshgrid(np.linspace(0.2, 0.5, 5), np.linspace(-0.2, 0.2, 4))
    br = np.zeros_like(r_grid)
    bz = np.full_like(r_grid, 2.0)
    p_perp = 3.0 + r_grid
    isotropic = compute_anisotropic_toroidal_current(r_grid, z_grid, br, bz, p_perp, p_perp)
    np.testing.assert_allclose(isotropic["anisotropy_curvature_term"], 0.0)
    np.testing.assert_allclose(isotropic["gradp_term"], 0.5)
    np.testing.assert_allclose(isotropic["j_phi"], 0.5)

    # A constant-magnitude field with a Z-varying direction has non-zero
    # anisotropic curvature current even though grad(B)=0.
    r_grid, z_grid = np.meshgrid(np.linspace(0.2, 0.5, 5), np.linspace(-0.5, 0.5, 101))
    theta = 0.4 * z_grid
    br = 2.0 * np.sin(theta)
    bz = 2.0 * np.cos(theta)
    p_perp = np.full_like(r_grid, 3.0)
    full = compute_anisotropic_toroidal_current(
        r_grid, z_grid, br, bz, np.full_like(r_grid, 4.0), p_perp
    )
    expected_anisotropy = 0.2 * np.cos(theta)
    np.testing.assert_allclose(full["gradp_term"], 0.0, atol=1.0e-12)
    np.testing.assert_allclose(
        full["anisotropy_curvature_term"][2:-2],
        expected_anisotropy[2:-2],
        rtol=2.0e-5,
        atol=1.0e-6,
    )
    np.testing.assert_allclose(
        full["j_phi"],
        full["gradp_term"] + full["anisotropy_curvature_term"],
    )
