import numpy as np
import pytest

from scirel.field.current_green_superposition import superpose_current_green_field, superpose_current_green_field as scientific_operator


# 验证：单一电流的三个响应均按源码 rank-1 规则逐点缩放。
def test_scalar_current_scales_rank_one_green_responses():
    result = scientific_operator(2.0, [1.0, 2.0], [3.0, 4.0], [-1.0, 5.0])
    assert np.allclose(result["psi"], [2.0, 4.0])
    assert np.allclose(result["BR"], [6.0, 8.0])
    assert np.allclose(result["BZ"], [-2.0, 10.0])


# 验证：多个 current set 必须沿第 0 Green 轴作 dot contraction。
def test_vector_current_contracts_green_source_axis():
    result = scientific_operator([2.0, -1.0], [[1.0, 3.0], [4.0, 5.0]], [[2.0, 1.0], [0.0, 6.0]], [[-1.0, 2.0], [3.0, 4.0]])
    assert np.allclose(result["psi"], [-2.0, 1.0])
    assert np.allclose(result["BR"], [4.0, -4.0])
    assert np.allclose(result["BZ"], [-5.0, 0.0])


# 验证：source axis 不匹配不能被广播为错误的磁场。
def test_rejects_wrong_green_source_axis():
    with pytest.raises(ValueError):
        scientific_operator([1.0, 2.0], [[1.0, 2.0]], [[1.0, 2.0]], [[1.0, 2.0]])


def test_reviewed_relation_example():
    import numpy as np
    from scirel.field.current_green_superposition import superpose_current_green_field

    currents = np.array([2.0, -1.0])
    gpsi = np.array([[1.0, 3.0], [4.0, 5.0]])
    gbr = np.array([[2.0, 1.0], [0.0, 6.0]])
    gbz = np.array([[-1.0, 2.0], [3.0, 4.0]])
    result = superpose_current_green_field(currents, gpsi, gbr, gbz)
    np.testing.assert_allclose(result["psi"], [-2.0, 1.0])
    np.testing.assert_allclose(result["BR"], [4.0, -4.0])
    np.testing.assert_allclose(result["BZ"], [-5.0, 0.0])
    basis = superpose_current_green_field([1.0, 0.0], gpsi, gbr, gbz)
    np.testing.assert_allclose(basis["psi"], gpsi[0])
