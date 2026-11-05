import numpy as np
import pytest

from scirel.field.current_green_superposition import (
    superpose_current_green_field,
    superpose_current_green_field as scientific_function,
)


# 验证：单一电流的三个一维响应均按 rank-1 规则逐点缩放。
def test_scalar_current_scales_rank_one_green_responses():
    result = scientific_function(2.0, [1.0, 2.0], [3.0, 4.0], [-1.0, 5.0])
    assert np.allclose(result["psi"], [2.0, 4.0])
    assert np.allclose(result["BR"], [6.0, 8.0])
    assert np.allclose(result["BZ"], [-2.0, 10.0])


# 验证：电流向量沿 Green 矩阵的第二轴（source 列）收缩，target 行保持不变。
def test_vector_current_contracts_green_source_columns():
    result = scientific_function(
        [2.0, -1.0],
        [[1.0, 4.0], [3.0, 5.0]],
        [[2.0, 0.0], [1.0, 6.0]],
        [[-1.0, 3.0], [2.0, 4.0]],
    )
    assert np.allclose(result["psi"], [-2.0, 1.0])
    assert np.allclose(result["BR"], [4.0, -4.0])
    assert np.allclose(result["BZ"], [-5.0, 0.0])


# 验证：非方阵输出沿 target 轴，source 列数必须等于 currents.size。
def test_matrix_contraction_preserves_target_axis():
    gpsi = [[1.0, 3.0], [4.0, 5.0], [2.0, 0.0]]
    zeros = [[0.0, 0.0], [0.0, 0.0], [0.0, 0.0]]
    result = scientific_function([2.0, -1.0], gpsi, zeros, zeros)
    assert result["psi"].shape == (3,)
    np.testing.assert_allclose(result["psi"], [-1.0, 3.0, 4.0])


# 验证：第二轴不是 source 轴时不能被广播为错误的磁场。
def test_rejects_wrong_green_source_axis():
    with pytest.raises(ValueError, match="source axis"):
        scientific_function(
            [1.0, 2.0],
            [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]],
            [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]],
            [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]],
        )


def test_unrepresentable_contraction_fails_closed():
    with pytest.raises(FloatingPointError, match="not representable"):
        scientific_function([1e308], [[-3.6e9]], [[0.0]], [[0.0]])
    with pytest.raises(FloatingPointError, match="not representable"):
        scientific_function(1e308, [-3.6e9], [0.0], [0.0])


def test_reviewed_relation_example():
    currents = np.array([2.0, -1.0])
    gpsi = np.array([[1.0, 4.0], [3.0, 5.0]])
    gbr = np.array([[2.0, 0.0], [1.0, 6.0]])
    gbz = np.array([[-1.0, 3.0], [2.0, 4.0]])
    result = superpose_current_green_field(currents, gpsi, gbr, gbz)
    np.testing.assert_allclose(result["psi"], [-2.0, 1.0])
    np.testing.assert_allclose(result["BR"], [4.0, -4.0])
    np.testing.assert_allclose(result["BZ"], [-5.0, 0.0])
    basis = superpose_current_green_field([1.0, 0.0], gpsi, gbr, gbz)
    np.testing.assert_allclose(basis["psi"], gpsi[:, 0])
