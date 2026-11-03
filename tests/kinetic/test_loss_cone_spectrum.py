import numpy as np
import pytest

from scirel.kinetic.loss_cone_spectrum import solve_loss_cone_spectrum, solve_loss_cone_spectrum as scientific_function


# 验证：最低正本征值、分数 degree 转换和 xi=0 归一化必须保持源码离散合同。
def test_returns_ordered_normalized_loss_cone_modes():
    result = scientific_function(0.6, 3, grid_points=32)
    assert result["xi"].shape == (32,)
    assert result["eigenfunctions"].shape == (32, 3)
    assert np.all(np.diff(result["eigenvalues"]) > 0.0)
    assert np.allclose(result["eigenvalues"], result["degrees"] * (result["degrees"] + 1.0))
    assert np.allclose(result["eigenfunctions"][0], 1.0)


def test_hypergeometric_backend_accepts_paper_mode_count():
    result = scientific_function(np.sqrt(1.0 - 1.0 / 20.0), 14, backend="hypergeometric")
    assert result["degrees"].shape == (14,)
    assert result["backend"] == "hypergeometric"
    assert np.all(np.diff(result["degrees"]) > 0.0)


def test_rejects_unknown_backend():
    with pytest.raises(ValueError):
        scientific_function(0.6, 1, backend="unknown")


# 验证：损失锥端点和模式数不合法时必须 fail closed，而不是产生不受约束的谱。
@pytest.mark.parametrize("xi_tp, mode_count", [(0.0, 1), (1.0, 1), (0.5, 0)])
def test_rejects_invalid_loss_cone_domain(xi_tp, mode_count):
    with pytest.raises(ValueError):
        scientific_function(xi_tp, mode_count)


def test_reviewed_relation_example():
    import math
    import numpy as np
    from scipy.special import hyp2f1
    from scirel.kinetic.loss_cone_spectrum import solve_loss_cone_spectrum

    xi_tp = 0.6
    result = solve_loss_cone_spectrum(xi_tp, 2, grid_points=32, backend="hypergeometric")
    assert result["xi"].shape == (32,)
    assert result["eigenfunctions"].shape == (32, 2)
    assert result["xi"][0] == 0.0
    assert result["xi"][-1] == xi_tp * 31.0 / 32.0
    assert np.all(result["xi"] < xi_tp)
    assert np.allclose(result["eigenfunctions"][0], 1.0)
    assert np.all(np.diff(result["degrees"]) > 0.0)
    assert np.allclose(result["eigenvalues"], result["degrees"] * (result["degrees"] + 1.0))

    def independent_mode(degree, xi):
        def p(value):
            return hyp2f1(-degree, degree + 1.0, 1.0, (1.0 - value) / 2.0)
        def q(value):
            return 0.5 * math.pi / math.sin(math.pi * degree) * (
                math.cos(math.pi * degree) * p(value) - p(-value)
            )
        step = 1.0e-5
        matrix = np.array(
            [[p(0.0), q(0.0)],
             [(p(step) - p(-step)) / (2.0 * step), (q(step) - q(-step)) / (2.0 * step)]]
        )
        a_coeff, b_coeff = np.linalg.solve(matrix, np.array([1.0, 0.0]))
        return a_coeff * p(xi) + b_coeff * q(xi)

    # 独立重建边界值；最后一个采样点不是边界点，不能代替这个检查。
    for degree in result["degrees"]:
        assert abs(float(independent_mode(float(degree), xi_tp))) < 2.0e-8
