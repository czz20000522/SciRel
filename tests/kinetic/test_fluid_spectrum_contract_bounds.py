"""可观察边界回归：钉住合同与中文阅读层里两句关于返回形状的断言。

这两个测试只在构造上断言"现场能看到的形状与绑定"，不建立任何数值结论，也不改写
`solve_fluid_bonk` / `solve_fluid_em` 的行为：

- `scirel.kinetic.fluid-bonk-search` 的 supported/scope 声明 "source default78-frequency
  axis"，所以默认频率轴必须真的是 78 点（`np.arange(0.11, 3.95 + 0.025, 0.05)`）。
- `solve_fluid_em` 的末频别名：`matM`、`roots`、`w`、`eigen_diagnostics` 只对应最后一个
  输入频率；每频率数据留在 `kxx`、`spectra`、`selected_candidates`（即 `kx`）、
  `diagnostic_rows`。
"""

import numpy as np

from scirel.kinetic.fluid_spectrum import (
    assemble_fluid_em,
    derive_fluid_case,
    solve_fluid_bonk,
    solve_fluid_em,
)


def test_bonk_default_axis_count_matches_contract():
    state = derive_fluid_case("bonk", 2)
    wcn = float(np.asarray(state["wcn"]).item())
    result = solve_fluid_bonk(2)
    xx = np.asarray(result["xx"], float).ravel()
    assert xx.size == 78
    np.testing.assert_array_equal(xx, np.arange(0.11, 3.95 + 0.025, 0.05) * wcn)
    np.testing.assert_allclose(xx[0], 0.11 * wcn, rtol=0, atol=0)
    np.testing.assert_allclose(xx[-1], 3.96 * wcn, rtol=0, atol=0)


def test_em_terminal_aliases_only_bind_last_frequency():
    state = derive_fluid_case("em", 2)
    wn = float(np.asarray(state["wn"]).item())
    omegas = np.array([0.37, 0.83, 1.43]) * wn
    result = solve_fluid_em(2, 8, 0, omegas)

    # 每频率数据：三个频率各自一行/一格，不能被压成末频值。
    assert np.asarray(result["xx"], float).ravel().size == 3
    assert np.asarray(result["kxx"], complex).shape == (3, 5)
    assert result["spectra"].shape == (1, 3)
    assert result["selected_candidates"].shape == (1, 3)
    assert result["diagnostic_rows"].shape == (1, 3)
    for index in range(3):
        selected = np.asarray(result["selected_candidates"][0, index], complex).ravel()
        # 每频率存全部正实部候选；kxx 只取按 |Im| 排序后的前五个。
        assert selected.size >= 5
        np.testing.assert_array_equal(selected[:5], np.asarray(result["kxx"][index], complex))

    # 末频别名：只承载最后一个给定频率。
    np.testing.assert_allclose(float(np.asarray(result["w"]).item()), omegas[-1], rtol=0, atol=0)
    np.testing.assert_array_equal(
        np.asarray(result["roots"], complex).reshape(-1, 5),
        np.asarray(result["kxx"][-1:], complex),
    )
    np.testing.assert_array_equal(
        np.asarray(result["matM"], complex),
        np.asarray(assemble_fluid_em(state, omegas[-1], 8, 0)["M"], complex),
    )
    np.testing.assert_array_equal(
        np.asarray(result["eigen_diagnostics"]["eigenvalues"], complex),
        np.asarray(result["diagnostic_rows"][0, -1]["eigenvalues"], complex),
    )
