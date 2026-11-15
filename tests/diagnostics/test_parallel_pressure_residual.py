from fractions import Fraction

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


def test_contract_rejects_an_empty_pressure_sample_set():
    import numpy as np
    import pytest

    empty = np.array([], dtype=float)
    with pytest.raises(ValueError, match="at least one sample"):
        compute_parallel_pressure_residual(empty, empty, empty)


def _raw_pressure_reference(p_parallel, p_perp, field, derivative, atol, rtol):
    """Complete rational relations from public inputs, never production intermediates."""
    pp, pt, b, dp, floor = (
        Fraction.from_float(float(value)) for value in (p_parallel, p_perp, field, derivative, atol)
    )
    rhs = pp - b * dp
    error = pt - rhs
    relative = abs(error) / max(abs(pt), abs(rhs), floor)
    return {
        "rhs": float(rhs),
        "error": float(error),
        "relative_error": float(relative),
        "passed": relative <= Fraction.from_float(float(rtol)),
    }


@pytest.mark.parametrize("field", ["rhs", "error", "relative_error", "passed"])
@pytest.mark.parametrize("compatible", [False, True])
@pytest.mark.parametrize("default_controls", [False, True])
def test_raw_product_cancellation_preserves_each_public_quantity(
    field, compatible, default_controls
):
    scale = 2.0**54 if default_controls else 1.0
    b = 1.0 + 2.0**-27
    derivative = scale * (1.0 - 2.0**-27)
    perp = scale * 2.0**-54 if compatible else 0.0
    atol = 1e-6 if default_controls else 2.0**-100
    rtol = 0.01 if default_controls else 1e-13
    expected = _raw_pressure_reference(scale, perp, b, derivative, atol, rtol)
    controls = {} if default_controls else {"atol": atol, "rtol": rtol}
    result = compute_parallel_pressure_residual(
        scale, perp, b, dp_parallel_dB=derivative, **controls
    )
    if field == "passed":
        assert result[field] is expected[field]
    else:
        np.testing.assert_allclose(result[field], expected[field], rtol=1e-13, atol=0)


@pytest.mark.parametrize("compatible", [False, True])
def test_strict_uses_the_uncancelled_pressure_relation(compatible):
    pp, b, derivative = 2.0**54, 1.0 + 2.0**-27, 2.0**54 - 2.0**27
    perp = 1.0 if compatible else 0.0
    if compatible:
        result = compute_parallel_pressure_residual(
            pp, perp, b, strict=True, dp_parallel_dB=derivative
        )
        assert result.passed
        np.testing.assert_allclose(result.rhs, 1.0, rtol=1e-13, atol=0)
        assert result.error == result.relative_error == 0.0
    else:
        with pytest.raises(ValueError, match="equilibrium check failed"):
            compute_parallel_pressure_residual(pp, perp, b, strict=True, dp_parallel_dB=derivative)


def test_independent_linear_pressure_law_with_broadcast_derivative():
    field = np.array([[4.0, 0.5, 2.0], [1.0, 2.0, 0.5]])
    pressure = 8.0 + 4.0 * field
    perpendicular = np.full_like(field, 8.0)
    snapshots = [value.copy() for value in (field, pressure, perpendicular)]
    result = compute_parallel_pressure_residual(pressure, perpendicular, field, dp_parallel_dB=4.0)
    np.testing.assert_allclose(result.rhs, 8.0, rtol=1e-13, atol=0)
    np.testing.assert_array_equal(result.error, 0.0)
    np.testing.assert_array_equal(result.relative_error, 0.0)
    np.testing.assert_array_equal(result.dp_parallel_dB, 4.0)
    assert result.passed
    assert result.max_relative_error == result.mean_relative_error == 0.0
    assert result.rhs is result["rhs"]
    for value, snapshot in zip((field, pressure, perpendicular), snapshots):
        np.testing.assert_array_equal(value, snapshot)


@pytest.mark.parametrize("compatible", [False, True])
def test_exactly_representable_subnormal_pressure_relation(compatible):
    tiny = float.fromhex("0x0.0000000000001p-1022")
    pp, b, derivative = 2.0 * tiny, 2.0**-500, 2.0**-574
    perp = tiny if compatible else 0.0
    expected = _raw_pressure_reference(pp, perp, b, derivative, tiny, 1e-13)
    assert expected["rhs"] == tiny
    result = compute_parallel_pressure_residual(
        pp, perp, b, atol=tiny, rtol=1e-13, dp_parallel_dB=derivative
    )
    for field in ("rhs", "error", "relative_error"):
        np.testing.assert_allclose(result[field], expected[field], rtol=1e-13, atol=0)
    assert result.passed is expected["passed"]


def test_intermediate_product_overflow_with_representable_public_quantities():
    pp, perp, b, derivative = 2.0**1023, -(2.0**1023), 2.0**600, 2.0**424
    expected = _raw_pressure_reference(pp, perp, b, derivative, 1e-6, 0.01)
    result = compute_parallel_pressure_residual(pp, perp, b, dp_parallel_dB=derivative)
    for field in ("rhs", "error", "relative_error"):
        np.testing.assert_allclose(result[field], expected[field], rtol=1e-13, atol=0)
    assert result.passed is expected["passed"]


@pytest.mark.parametrize(
    "pp,perp,b,derivative",
    [
        (-(2.0**1023), 0.0, 2.0, 2.0**1023),
        (2.0**1023, -(2.0**1023), 1.0, 0.0),
    ],
)
def test_genuinely_unrepresentable_required_pressure_output_is_rejected(pp, perp, b, derivative):
    with pytest.raises(FloatingPointError, match="finite"):
        compute_parallel_pressure_residual(pp, perp, b, dp_parallel_dB=derivative)


@pytest.mark.parametrize("field", ["rhs", "error", "relative_error", "passed"])
def test_second_subtraction_retains_the_complete_pressure_relation(field):
    # rhs rounds to -1, but the complete error is -2^-54, not -1-(-1)=0.
    pp, perp, b, derivative = 0.0, -1.0, 1.0 + 2.0**-27, 1.0 - 2.0**-27
    expected = _raw_pressure_reference(pp, perp, b, derivative, 1e-6, 0.0)
    result = compute_parallel_pressure_residual(pp, perp, b, rtol=0.0, dp_parallel_dB=derivative)
    if field == "passed":
        assert result[field] is expected[field]
    else:
        np.testing.assert_allclose(result[field], expected[field], rtol=1e-13, atol=0)


def test_strided_mixed_samples_recover_only_the_affected_relations():
    field = np.array([[1.0, 1.0 + 2.0**-27, 2.0]])[:, ::-1]
    pressure = np.array([[3.0, 1.0, 10.0]])[:, ::-1]
    derivative = np.array([[0.0, 1.0 - 2.0**-27, 1.0]])[:, ::-1]
    perpendicular = np.array([[3.0, 2.0**-54, 8.0]])[:, ::-1]
    snapshots = [value.copy() for value in (field, pressure, derivative, perpendicular)]
    result = compute_parallel_pressure_residual(
        pressure, perpendicular, field, dp_parallel_dB=derivative
    )
    for index in np.ndindex(field.shape):
        expected = _raw_pressure_reference(
            pressure[index], perpendicular[index], field[index], derivative[index], 1e-6, 0.01
        )
        for key in ("rhs", "error", "relative_error"):
            np.testing.assert_allclose(result[key][index], expected[key], rtol=1e-13, atol=0)
    assert result.passed
    for value, snapshot in zip((field, pressure, derivative, perpendicular), snapshots):
        np.testing.assert_array_equal(value, snapshot)


@pytest.mark.parametrize("small_output", ["rhs", "relative_error"])
def test_nonzero_required_output_below_float64_range_is_rejected(small_output):
    if small_output == "rhs":
        pp, perp, b, derivative, floor = 0.0, 1.0, 2.0**-600, 2.0**-600, 1e-6
    else:
        pp = float.fromhex("0x0.0000000000001p-1022")
        perp, b, derivative, floor = 0.0, 1.0, 0.0, 2.0**1023
    with pytest.raises(FloatingPointError, match="finite"):
        compute_parallel_pressure_residual(
            pp, perp, b, atol=floor, rtol=0.0, dp_parallel_dB=derivative
        )


@pytest.mark.parametrize("sign", [-1.0, 1.0])
@pytest.mark.parametrize("perp_exponent", [None, 968, 969, 970])
def test_complete_error_overflow_midpoint_and_finite_neighbors(sign, perp_exponent):
    # M+h rounds to M; the COMPLETE error reaches the overflow midpoint
    # at pt=-sign*h even though two successive subtractions can stay finite.
    maximum = float.fromhex("0x1.fffffffffffffp+1023")
    h = 2.0**969
    pp, derivative = sign * maximum, -sign * h
    perp = 0.0 if perp_exponent is None else -sign * 2.0**perp_exponent
    exact_rhs = Fraction.from_float(pp) - Fraction.from_float(derivative)
    exact_error = Fraction.from_float(perp) - exact_rhs
    assert float(exact_rhs) == sign * maximum
    if perp_exponent in (969, 970):
        if perp_exponent == 969:
            assert exact_error == -int(sign) * ((1 << 1024) - (1 << 970))
        with pytest.raises(OverflowError):
            float(exact_error)
        with pytest.raises(FloatingPointError, match="finite"):
            compute_parallel_pressure_residual(pp, perp, 1.0, dp_parallel_dB=derivative)
    else:
        expected = _raw_pressure_reference(pp, perp, 1.0, derivative, 1e-6, 0.01)
        result = compute_parallel_pressure_residual(pp, perp, 1.0, dp_parallel_dB=derivative)
        assert result.rhs == float(exact_rhs)
        assert result.error == float(exact_error)
        for key in ("rhs", "error", "relative_error"):
            np.testing.assert_allclose(result[key], expected[key], rtol=1e-13, atol=0)
        assert result.passed is expected["passed"]


@pytest.mark.parametrize("sign", [-1.0, 1.0])
def test_complete_rhs_overflow_midpoint_is_rejected(sign):
    maximum = float.fromhex("0x1.fffffffffffffp+1023")
    derivative = -sign * 2.0**970
    exact_rhs = Fraction.from_float(sign * maximum) - Fraction.from_float(derivative)
    assert exact_rhs == int(sign) * ((1 << 1024) - (1 << 970))
    with pytest.raises(OverflowError):
        float(exact_rhs)
    with pytest.raises(FloatingPointError, match="finite"):
        compute_parallel_pressure_residual(sign * maximum, 0.0, 1.0, dp_parallel_dB=derivative)


@pytest.mark.parametrize("sign", [-1.0, 1.0])
def test_upper_range_recovery_keeps_finite_mixed_strided_samples(sign):
    maximum = float.fromhex("0x1.fffffffffffffp+1023")
    pp = np.array([[sign * maximum, 3.0, sign * maximum]])[:, ::-1]
    perp = np.array([[0.0, 3.0, -sign * 2.0**968]])[:, ::-1]
    derivative = np.array([[-sign * 2.0**969, 0.0, -sign * 2.0**969]])[:, ::-1]
    field = np.ones_like(pp)
    snapshots = [value.copy() for value in (pp, perp, field, derivative)]
    expected_relative = np.empty_like(pp)
    result = compute_parallel_pressure_residual(pp, perp, field, dp_parallel_dB=derivative)
    for index in np.ndindex(pp.shape):
        expected = _raw_pressure_reference(
            pp[index], perp[index], field[index], derivative[index], 1e-6, 0.01
        )
        for key in ("rhs", "error", "relative_error"):
            np.testing.assert_allclose(result[key][index], expected[key], rtol=1e-13, atol=0)
        expected_relative[index] = expected["relative_error"]
    np.testing.assert_allclose(
        result.max_relative_error, np.max(expected_relative), rtol=1e-13, atol=0
    )
    np.testing.assert_allclose(
        result.mean_relative_error, np.mean(expected_relative), rtol=1e-13, atol=0
    )
    assert result.passed is False
    assert result.rhs is result["rhs"]
    for value, snapshot in zip((pp, perp, field, derivative), snapshots):
        np.testing.assert_array_equal(value, snapshot)
