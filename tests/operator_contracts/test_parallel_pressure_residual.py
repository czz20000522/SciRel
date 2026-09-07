import numpy as np
import pytest

from scirel.diagnostics.parallel_pressure_residual import compute_parallel_pressure_residual, compute_parallel_pressure_residual as scientific_operator


# 验证：p_parallel/B 为常数时 RHS 与 p_perp 都应为零，检查必须通过。
def test_constant_parallel_to_field_ratio_satisfies_zero_perpendicular_pressure_relation():
    magnetic_field = np.array([[1.0, 1.3], [1.6, 2.0]])
    result = scientific_operator(4.0 * magnetic_field, np.zeros_like(magnetic_field), magnetic_field)
    assert result["passed"]
    assert np.allclose(result["rhs"], 0.0)
    assert result["max_relative_error"] < 1.0e-8


# 验证：严格模式必须把超容差残差提升为失败，而非只返回布尔标记。
def test_strict_mode_raises_for_parallel_equilibrium_violation():
    magnetic_field = np.array([1.0, 1.5, 2.0])
    with pytest.raises(ValueError):
        scientific_operator(magnetic_field, np.ones_like(magnetic_field), magnetic_field, strict=True)


def test_reviewed_relation_example():
    from scirel.diagnostics.parallel_pressure_residual import compute_parallel_pressure_residual
    import numpy as np

    # 乱序输入验证导数在 B-value space 计算、结果再映回原位置。
    B = np.array([3.0, 1.0, 2.0, 4.0])
    p_parallel = B * B
    p_perp = -B * B
    result = compute_parallel_pressure_residual(p_parallel, p_perp, B, rtol=1e-12)
    np.testing.assert_allclose(result["rhs"], -B * B, rtol=1e-12, atol=1e-12)
    np.testing.assert_allclose(result["error"], 0.0, atol=1e-12)
    assert result["passed"]
    assert result["max_relative_error"] <= 1e-12

    # B 没有数值跨度时，导数按合同置零。
    B_flat = np.ones(3)
    degenerate = compute_parallel_pressure_residual(
        np.array([2.0, 3.0, 4.0]), np.zeros(3), B_flat, rtol=0.0
    )
    np.testing.assert_allclose(degenerate["rhs"], 0.0)
    assert degenerate["passed"]

    # strict 模式必须把不满足关系的状态作为失败关闭。
    try:
        compute_parallel_pressure_residual(p_parallel, np.zeros_like(B), B, strict=True)
    except ValueError as exc:
        assert "equilibrium check failed" in str(exc)
    else:
        raise AssertionError("strict mode must reject an inconsistent perpendicular pressure")


def test_review_gate_rejects_an_empty_pressure_sample_set():
    import numpy as np
    import pytest

    empty = np.array([], dtype=float)
    with pytest.raises(ValueError, match="at least one sample"):
        compute_parallel_pressure_residual(empty, empty, empty)
