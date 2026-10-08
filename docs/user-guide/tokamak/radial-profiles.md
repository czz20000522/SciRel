# 径向剖面、坐标与边界

## 可以回答的问题

如何表示等离子体内部温度或密度随小半径的变化？某个剖面的径向梯度是多少？如何把磁轴和边缘值加入展示曲线？
这些是同一个径向剖面功能的不同步骤，分别使用网格、导数和边界补点接口。

## 物理量与坐标

本版使用归一化小半径 `rho = r/a`，其中 `a` 是等离子体小半径，单位 m。
`rho` 没有量纲；它不是本页默认定义的归一化磁通或磁通平方根。
温度输入常以 keV 表示，因此 `dT/dr` 的单位为 keV/m；一般场量 `y` 的导数单位为 `y` 的单位除以 m。

数值状态保存在单元中心。网格面有 `nr+1` 个，中心有 `nr` 个；中心、网格面和物理边界不能混为同一位置。

| 量 | 含义 | 形状与单位 |
| --- | --- | --- |
| `a` | 小半径 | 正标量，m |
| `rho` | 单元中心归一化位置 | `[nr]`，无量纲 |
| `r` | 单元中心物理半径 | `[nr]`，m |
| `dr` | 物理单元宽度 | 均匀网格为标量；非均匀网格为 `[nr]`，m |
| `y` | 温度、密度或其他剖面值 | 与 `rho` 等长的一维数组；单位由调用者给定 |

## 功能与实现入口

- **离散径向空间**：`make_rho_faces` 给出网格面，`make_grid` 给出单元中心与宽度。
- **求变化率**：`radial_gradient` 返回来源定义的 `dy/dr` 有限差分近似。
- **加入展示用边界**：`boundary_augmented_profile` 补入 `rho=0` 与 `rho=1`，返回 `nr+2` 个点。

入口均在 `scirel.fusion.grid`。完整参数和默认值见 [调用参考](../api-reference.md)。

均匀网格的面为 `i/nr`，中心是相邻面的平均值，物理中心为 `a*rho`。
可选 `edge_cluster_sqrt` 使用 `sqrt(max(1-(1-x)^p, 0))` 变换网格面；`p` 默认 2。
选择非均匀网格后必须按实际坐标求导，不能继续假定单元宽度都是 `a/nr`。

## 导数的边界与离散约定

`radial_gradient(y, rho, a)` 要求匹配的一维数组、`nr >= 2`、递增且位于 `(0,1)` 的中心坐标，以及正小半径。
当前来源实现采用：

```text
g[0] = 0                  # 复制首单元值作为磁轴 ghost 值
g[i] = (y[i+1]-y[i-1]) / (a*(rho[i+1]-rho[i-1]) + 1e-12)
g[-1] = (y[-1]-y[-2]) / (a*(rho[-1]-rho[-2]) + 1e-12)
```

第一项为零是所保留的离散边界约定，不是已经证明第一个单元中心的连续物理导数为零。
最后一项采用后向差分。分母的 `1e-12` 是实际实现保留的正则项，因此结果通常只近似简单算术值。
函数没有新增一套输入验证；域外数组可能出现原索引/形状行为，不能把这种返回当作有效剖面导数。

## 最小例子：温度下降剖面

```python
import jax
jax.config.update("jax_enable_x64", True)
import jax.numpy as jnp
from scirel.fusion.grid import make_grid, radial_gradient

rho, r, dr = make_grid(nr=4, a=2.0)
temperature = jnp.asarray([4.0, 3.0, 2.0, 1.0], dtype=jnp.float64)
gradient = radial_gradient(temperature, rho, a=2.0)
print(rho, r, dr, gradient)
```

预期 `rho=[0.125,0.375,0.625,0.875]`、`r=[0.25,0.75,1.25,1.75] m`、`dr=0.5 m`，
梯度约为 `[0,-2,-2,-2] keV/m`。该输入与材料 Q1 一致，参考数值已实际计算；比较保留 `rtol=atol=2e-10`。

## 展示边界与物理状态的区别

```python
from scirel.fusion.grid import boundary_augmented_profile
rho_plot, temperature_plot = boundary_augmented_profile(
    rho, temperature, edge_value=0.25
)
```

默认 `method='copy'`：磁轴显示值复制首单元值；若 `edge_value=None`，边缘显示值复制末单元值，
否则附加调用者给出的边缘值。`linear/quadratic/cubic` 是另外保留的外推选择，不是新的物理闭合。
补点用于绘图/诊断，不是守恒重网格或新的时间演化状态。

本页覆盖径向表示与有限差分；它不提供独立的输运方程求解或实验剖面拟合。
相关功能：[状态演化](state-and-evolution.md)、[平衡与输运](equilibrium-and-transport.md)。
