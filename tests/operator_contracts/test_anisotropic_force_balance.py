import numpy as np
import pytest

from scirel.equilibrium.anisotropic_force_balance import _source_hypot, compute_anisotropic_force_balance, compute_anisotropic_force_balance as scientific_operator


def _grid():
    return np.meshgrid(np.linspace(0.0, 0.4, 5), np.linspace(-0.3, 0.3, 5))


def test_constant_isotropic_pressure_has_zero_force_and_current():
    r_grid, z_grid = _grid()
    result = scientific_operator(r_grid, z_grid, np.zeros_like(r_grid), np.ones_like(r_grid), np.full_like(r_grid, 2.0), np.full_like(r_grid, 2.0))
    for name in ("force_R", "force_Z", "parallel_force", "J_phi"):
        np.testing.assert_allclose(result[name], 0.0, atol=1.0e-12)
    np.testing.assert_allclose(result["firehose_margin"], 1.0)
    assert np.isfinite(result["parallel_force_error"])


def test_axis_rule_and_mask_shape_are_enforced():
    r_grid, z_grid = _grid()
    result = scientific_operator(r_grid, z_grid, np.zeros_like(r_grid), np.ones_like(r_grid), 1.0 + r_grid, 1.0 + z_grid**2)
    np.testing.assert_allclose(result["force_R"][:, 0], 0.0)
    np.testing.assert_allclose(result["J_phi"][:, 0], 0.0)
    with pytest.raises(ValueError, match="active_mask"):
        scientific_operator(r_grid, z_grid, np.zeros_like(r_grid), np.ones_like(r_grid), 1.0 + r_grid, 1.0 + z_grid**2, np.ones((2, 2), dtype=bool))


def test_source_hypot_preserves_finite_subnormal_and_large_results():
    result = _source_hypot(np.array([1.0e-308, 1.0e308]), np.array([1.0e-308, 1.0e308]))
    assert result[0] != 0.0
    assert np.isfinite(result[0]) and np.isfinite(result[1])
    np.testing.assert_array_equal(result, np.array([1.414213562373095e-308, 1.4142135623730951e308]))


def test_reviewed_relation_example():
    import numpy as np
    from scirel.equilibrium.anisotropic_force_balance import compute_anisotropic_force_balance

    r_grid, z_grid = np.meshgrid(np.linspace(0.2, 0.5, 5), np.linspace(-0.5, 0.5, 101))
    theta = 0.4 * z_grid
    b_r = 2.0 * np.sin(theta)
    b_z = 2.0 * np.cos(theta)
    result = compute_anisotropic_force_balance(
        r_grid,
        z_grid,
        b_r,
        b_z,
        np.full_like(r_grid, 4.0),
        np.full_like(r_grid, 3.0),
    )
    expected_force_r = 0.4 * np.cos(2.0 * theta) + np.sin(theta) ** 2 / r_grid
    expected_force_z = -0.8 * np.sin(theta) * np.cos(theta) + np.sin(theta) * np.cos(theta) / r_grid
    expected_j_phi = 0.2 * np.cos(theta)
    np.testing.assert_allclose(result["force_R"][2:-2], expected_force_r[2:-2], rtol=2.0e-5, atol=1.0e-6)
    np.testing.assert_allclose(result["force_Z"][2:-2], expected_force_z[2:-2], rtol=2.0e-5, atol=1.0e-6)
    np.testing.assert_allclose(result["J_phi"][2:-2], expected_j_phi[2:-2], rtol=2.0e-5, atol=1.0e-6)
    np.testing.assert_allclose(result["B"], 2.0)
    np.testing.assert_allclose(result["firehose_margin"], 1.0 - 4.0e-7 * np.pi / 4.0)

    # 变量压力的制造解独立检验压力梯度项，而不是只检验各向异性方向项。
    gradient_result = compute_anisotropic_force_balance(
        r_grid,
        z_grid,
        np.zeros_like(r_grid),
        np.full_like(r_grid, 2.0),
        3.0 + r_grid,
        3.0 + r_grid,
    )
    np.testing.assert_allclose(gradient_result["force_R"], 1.0, rtol=2.0e-12, atol=2.0e-12)
    np.testing.assert_allclose(gradient_result["force_Z"], 0.0, rtol=2.0e-12, atol=2.0e-12)
    np.testing.assert_allclose(gradient_result["J_phi"], 0.5, rtol=2.0e-12, atol=2.0e-12)
