import numpy as np
import pytest

from scirel.diagnostics.pointwise_firehose_margin import (
    MU0,
    compute_pointwise_firehose_margin,
    compute_pointwise_firehose_margin as scientific_operator,
)


# 验证：逐点裕度对乱序数组样本按元素精确等于 B²/mu0 + p_perp - p_parallel。
def test_margin_matches_elementwise_closed_form_with_unsorted_samples():
    magnetic_field = np.array([2.0, 1.0, 3.0, 1.5])
    p_perp = 5.0 + 3.0 * magnetic_field
    p_parallel = p_perp + 2.0
    result = scientific_operator(p_parallel, p_perp, magnetic_field)
    np.testing.assert_array_equal(
        result["firehose_margin"],
        magnetic_field * magnetic_field / MU0 + p_perp - p_parallel,
    )


# 验证：单样本与全等 B 输入是本资产的正常输入域，无需任何导数或跨度前提。
def test_single_sample_and_all_equal_field_are_fully_supported():
    single = scientific_operator(810000.0, 740000.0, 0.93)
    assert float(single["firehose_margin"]) == 0.93 ** 2 / MU0 + 740000.0 - 810000.0
    flat = scientific_operator(
        np.array([650000.0, 820000.0, 990000.0]),
        np.array([600000.0, 690000.0, 780000.0]),
        np.ones(3),
    )
    np.testing.assert_allclose(
        flat["firehose_margin"], (np.ones(3) * np.ones(3) / MU0 + np.array([600000.0, 690000.0, 780000.0]) - np.array([650000.0, 820000.0, 990000.0]))
    )


# 验证：逐点值必须与组合诊断的 firehose_margin 字段逐位一致，旧数值合同原样保留。
def test_margin_is_bit_identical_to_combined_diagnostic_firehose_field():
    from scirel.diagnostics.firehose_mirror_margins import compute_firehose_mirror_margins

    rng = np.random.default_rng(20260927)
    magnetic_field = np.sort(rng.uniform(0.2, 2.5, size=7))
    p_perp = rng.uniform(1.0e4, 1.0e6, size=7)
    p_parallel = rng.uniform(1.0e4, 1.0e6, size=7)
    pointwise = scientific_operator(p_parallel, p_perp, magnetic_field)
    combined = compute_firehose_mirror_margins(
        p_parallel, p_perp, magnetic_field, dp_perp_dB=0.0
    )
    np.testing.assert_array_equal(pointwise["firehose_margin"], combined["firehose_margin"])


# 验证：结果只含 margin 本身——没有 mirror 分支、没有最小值、没有任何 stable 标志。
def test_result_carries_no_mirror_branch_and_no_stable_flag():
    result = scientific_operator(np.array([1.0e8]), np.zeros(1), np.ones(1))
    assert set(result.keys()) == {"firehose_margin"}
    for forbidden in ("mirror_margin", "mirror_stable", "firehose_stable",
                      "min_firehose_margin", "min_mirror_margin"):
        assert forbidden not in result


# 验证：负裕度必须原样返回，不得钳制、不得解释为任何标签。
def test_negative_margin_is_returned_faithfully_without_interpretation():
    result = scientific_operator(np.array([1.0e9]), np.zeros(1), np.ones(1))
    assert result["firehose_margin"][0] < 0.0
    np.testing.assert_allclose(
        result["firehose_margin"], np.ones(1) / MU0 - 1.0e9, rtol=1e-15
    )


# 验证：shape 不一致、空输入、非有限输入与非法 mu0 都必须被拒绝。
def test_invalid_inputs_are_rejected():
    good = np.ones(2)
    with pytest.raises(ValueError, match="same shape"):
        scientific_operator(np.ones(3), good, good)
    with pytest.raises(ValueError, match="nonempty"):
        scientific_operator(np.array([]), np.array([]), np.array([]))
    with pytest.raises(ValueError, match="finite"):
        scientific_operator(np.array([np.nan]), np.zeros(1), np.ones(1))
    with pytest.raises(ValueError, match="finite"):
        scientific_operator(good, np.array([np.inf, 0.0]), good)
    with pytest.raises(ValueError, match="positive and finite"):
        scientific_operator(good, good, np.zeros(2), mu0=0.0)
    with pytest.raises(ValueError, match="positive and finite"):
        scientific_operator(good, good, good, mu0=float("nan"))


# 验证：B²/mu0 磁张力项溢出 float64 时必须 fail closed，不得静默返回 Inf 裕度。
def test_overflowing_magnetic_tension_term_fails_closed():
    with pytest.raises(ValueError, match="must be finite"):
        scientific_operator(np.zeros(1), np.zeros(1), np.array([1.0e200]))


# 验证：0 维标量输入保持 0 维 float64 形状，供 adapter 以标量端口消费。
def test_scalar_inputs_preserve_zero_dimensional_shape():
    result = scientific_operator(650000.0, 600000.0, 1.0)
    assert result["firehose_margin"].shape == ()
    assert result["firehose_margin"].dtype == np.float64
    np.testing.assert_allclose(float(result["firehose_margin"]), 1.0 / MU0 - 50000.0)


# 验证：mu0 覆盖参数生效（与默认值的差恰为 B²/mu0 磁张力项的换算；SI 磁压是 B²/(2mu0)，不是本项）。
def test_mu0_override_changes_only_the_magnetic_tension_term():
    p_parallel, p_perp, b = 1.0e5, 2.0e5, 2.0
    default = scientific_operator(p_parallel, p_perp, b)["firehose_margin"]
    overridden = scientific_operator(p_parallel, p_perp, b, mu0=1.0e-6)["firehose_margin"]
    np.testing.assert_allclose(
        float(overridden) - float(default), b * b * (1.0 / 1.0e-6 - 1.0 / MU0), rtol=1e-15
    )


# 验证：非标量 mu0（含 0 维数组之外的 1 维数组与包装序列）必须在算术前被拒绝，
# 不得通过广播改变输出的标量/同形合同。
def test_nonscalar_mu0_is_rejected_before_arithmetic():
    for bad in (np.array([1.0]), [1.0], (1.0,), np.array([[1.25e-6]])):
        with pytest.raises(ValueError, match="scalar"):
            scientific_operator(1.0, 1.0, 1.0, mu0=bad)
