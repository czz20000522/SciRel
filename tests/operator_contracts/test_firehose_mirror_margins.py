import numpy as np

from scirel.diagnostics.firehose_mirror_margins import MU0, compute_firehose_mirror_margins, compute_firehose_mirror_margins as scientific_operator


# 验证：常压且非零场时，两个裕度须解析地等于 B²/mu0，并稳定为真。
def test_constant_pressures_produce_positive_magnetic_margins():
    magnetic_field = np.array([1.0, 1.5, 2.0])
    result = scientific_operator(np.ones(3), np.ones(3), magnetic_field)
    expected = magnetic_field * magnetic_field / MU0
    assert np.allclose(result["firehose_margin"], expected)
    assert np.allclose(result["mirror_margin"], expected)
    assert result["firehose_stable"] and result["mirror_stable"]


# 验证：压强各向异性足够大时，firehose 判据必须反映负裕度。
def test_firehose_instability_is_reported():
    result = scientific_operator(np.array([1.0e8, 1.0e8]), np.zeros(2), np.ones(2))
    assert not result["firehose_stable"]
    assert result["min_firehose_margin"] < 0.0


def test_reviewed_relation_example():
    from scirel.diagnostics.firehose_mirror_margins import compute_firehose_mirror_margins
    import numpy as np

    MU0 = 4.0e-7 * np.pi
    # 输入故意乱序；实现必须先在 B-value space 排序求导，再映回原顺序。
    B = np.array([2.0, 1.0, 3.0, 1.5])
    slope = 3.0
    p_perp = 5.0 + slope * B
    p_parallel = p_perp + 2.0
    result = compute_firehose_mirror_margins(p_parallel, p_perp, B)
    np.testing.assert_allclose(result["firehose_margin"], B * B / MU0 - 2.0)
    np.testing.assert_allclose(result["mirror_margin"], B * B / MU0 - slope * B)
    assert result["firehose_stable"]
    assert result["mirror_stable"]
    assert np.isclose(result["min_firehose_margin"], np.min(B * B / MU0 - 2.0))

    # 当所有 B 相同时，value-space 没有跨度，导数按合同置零。
    B_flat = np.full(3, 2.0)
    degenerate = compute_firehose_mirror_margins(
        np.full(3, 7.0), np.array([1.0, 4.0, 9.0]), B_flat
    )
    np.testing.assert_allclose(degenerate["mirror_margin"], 4.0 / MU0)


def test_review_gate_rejects_duplicate_nondegenerate_field_samples():
    import numpy as np
    import pytest

    magnetic_field = np.array([1.0, 1.0, 2.0])
    p_perp = np.array([0.0, 1.0, 4.0])
    with pytest.raises(ValueError, match="must be unique"):
        compute_firehose_mirror_margins(p_perp, p_perp, magnetic_field)
