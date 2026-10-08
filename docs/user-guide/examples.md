# 可复现小例子

这些例子对测试材料中的 exact dev2 wheel 已有真实参考计算。它们检验加载、文件输入、数值调用与失败传播，
属于有限平台任务，不是完整等离子体物理验收。先按 [安装说明](version-and-installation.md) 启用 JAX 64 位。

## Q1 · 温度径向变化率

**自然语言问题**：等离子体小半径为 2 m，使用 4 个均匀径向单元，中心温度为 `[4,3,2,1] keV`。
用 SciRel 计算中心半径与温度径向梯度，解释磁轴约定，给出表格并保存 CSV、JSON 和 PNG。

调用代码见 [径向剖面](tokamak/radial-profiles.md)。该版实际结果：

| r / m | T / keV | dT/dr / (keV/m) |
| --- | --- | --- |
| 0.25 | 4 | 0 |
| 0.75 | 3 | -1.9999999999979998 |
| 1.25 | 2 | -1.9999999999979998 |
| 1.75 | 1 | -1.999999999996 |

## Q2 · 从文件读取剖面并补入边界

**自然语言问题**：读取上传的 `inputs/temperature.csv`，温度为 `[1,2,4,8] keV`。
小半径 1 m、4 个均匀单元。计算梯度，并以 `edge_value=10 keV` 补入边界用于绘图；解释中心点和边界点。

```python
import csv
import jax
jax.config.update("jax_enable_x64", True)
import jax.numpy as jnp
from scirel.fusion.grid import make_grid, radial_gradient, boundary_augmented_profile

with open("inputs/temperature.csv", newline="", encoding="utf-8") as f:
    temperature = jnp.asarray(
        [float(row["temperature_keV"]) for row in csv.DictReader(f)], dtype=jnp.float64
    )
rho, r, dr = make_grid(nr=4, a=1.0)
gradient = radial_gradient(temperature, rho, a=1.0)
rho_plot, temperature_plot = boundary_augmented_profile(rho, temperature, edge_value=10.0)
```

实际梯度为 `[0,5.999999999988001,11.999999999976001,15.999999999936001] keV/m`。
展示坐标为 `[0,0.125,0.375,0.625,0.875,1]`，温度为 `[1,1,2,4,8,10] keV`。
输出温度曲线有 6 个点；梯度仍有 4 个中心点，不能错误拼成相同长度。

## Q3 · 不支持的网格选择

**自然语言问题**：调用 SciRel 生成 `radial_grid='unsupported'` 的网格，报告真实异常，保留失败，不能换网格后宣称原任务成功。

```python
from scirel.fusion.grid import make_grid
make_grid(4, 2.0, radial_grid="unsupported")
```

实际预期为 `ValueError: Unknown radial_grid='unsupported'`。
这是异常传播的检验，不是产生数值结果的成功例子。

## 比较与交付

数值比较保留 `rtol=atol=2e-10`，不将展示时的四舍五入文本当作精确机器输出。
测试包 `expected/reference-results.json` 与 CSV 保存实际数值，PNG 是参考展示。
平台应使用安装的 SciRel 计算，再保存、展示与下载自己的结果；仅打开本指南或显示参考文件不能证明计算链路已跑通。
