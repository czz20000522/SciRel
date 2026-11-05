import numpy as np
import pytest

from scirel.diagnostics.parallel_pressure_residual import (
    compute_parallel_pressure_residual,
    compute_parallel_pressure_residual as scientific_function,
)


# 验证：p_parallel/B 为常数时 RHS 与 p_perp 都应为零，检查必须通过。
def test_constant_parallel_to_field_ratio_satisfies_zero_perpendicular_pressure_relation():
    magnetic_field = np.array([[1.0, 1.3], [1.6, 2.0]])
    result = scientific_function(
        4.0 * magnetic_field, np.zeros_like(magnetic_field), magnetic_field, dp_parallel_dB=4.0
    )
    assert result["passed"]
    assert np.allclose(result["rhs"], 0.0)
    assert result["max_relative_error"] < 1.0e-8


# 验证：严格模式必须把超容差残差提升为失败，而非只返回布尔标记。
def test_strict_mode_raises_for_parallel_equilibrium_violation():
    magnetic_field = np.array([1.0, 1.5, 2.0])
    with pytest.raises(ValueError):
        scientific_function(
            magnetic_field,
            np.ones_like(magnetic_field),
            magnetic_field,
            strict=True,
            dp_parallel_dB=1.0,
        )


def test_reviewed_relation_example():
    from scirel.diagnostics.parallel_pressure_residual import compute_parallel_pressure_residual
    import numpy as np

    # 压力律 p_parallel=B² 给出显式固定ψ偏导2B，和空间点排序无关。
    B = np.array([3.0, 1.0, 2.0, 4.0])
    p_parallel = B * B
    p_perp = -B * B
    result = compute_parallel_pressure_residual(
        p_parallel, p_perp, B, rtol=1e-12, dp_parallel_dB=2.0 * B
    )
    np.testing.assert_allclose(result["rhs"], -B * B, rtol=1e-12, atol=1e-12)
    np.testing.assert_allclose(result["error"], 0.0, atol=1e-12)
    assert result["passed"]
    assert result["max_relative_error"] <= 1e-12

    # 同B的空间样本不能定义偏导，更不能把非零平行压强自动视作平衡。
    B_flat = np.ones(3)
    with pytest.raises(ValueError, match="fixed-flux derivative"):
        compute_parallel_pressure_residual(np.array([2.0, 3.0, 4.0]), np.zeros(3), B_flat, rtol=0.0)
    declared = compute_parallel_pressure_residual(
        np.array([2.0, 3.0, 4.0]),
        np.zeros(3),
        B_flat,
        rtol=0.0,
        dp_parallel_dB=np.array([2.0, 3.0, 4.0]),
    )
    np.testing.assert_allclose(declared["rhs"], 0.0)
    assert declared["passed"]

    # strict 模式必须把不满足关系的状态作为失败关闭。
    try:
        compute_parallel_pressure_residual(
            p_parallel, np.zeros_like(B), B, strict=True, dp_parallel_dB=2.0 * B
        )
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
