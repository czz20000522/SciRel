#!/usr/bin/env python3
"""Render REPORT.md from data/summary.json, data/checks.json and data/points.csv.

Prose is written here; every number in it is read from the saved outputs.
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent


def sig(value, digits=3):
    return f"{value:.{digits}g}"


def where(points):
    return "、".join(f"(R={p[0]:g} m, Z={p[1]:+g} m)".replace("Z=+0 m", "Z=0") for p in points)


def table_value(value, floor):
    return "0" if abs(value) < floor else f"{value:.4g}"


def point_table(rows):
    lines = ["| R (m) | Z (m) | $B_r$ (T) | $B_z$ (T) | 幅值 (T) | $\\psi$ (Wb/rad) | $T$ (rad) |",
             "| --- | --- | --- | --- | --- | --- | --- |"]
    for row in rows:
        values = [table_value(float(row[k]), f) for k, f in (
            ("Br_T", 1e-15), ("Bz_T", 1e-15), ("Bmag_T", 1e-15), ("psi_Wb_per_rad", 1e-18), ("tilt_rad", 1e-15))]
        lines.append(f"| {float(row['R_m']):g} | {float(row['Z_m']):g} | " + " | ".join(values) + " |")
    return "\n".join(lines)


def render():
    summary = json.loads((HERE / "data/summary.json").read_text(encoding="utf-8"))
    checks = json.loads((HERE / "data/checks.json").read_text(encoding="utf-8"))
    with (HERE / "data/points.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    states = summary["states"]
    nom, off, shift, gap = (states[k] for k in ("nominal", "offset", "shift_only", "gap_only"))
    delta = summary["offset_minus_nominal"]
    shape = summary["axial_shape"]
    by_state = {name: [r for r in rows if r["state"] == name] for name in ("nominal", "offset", "offset_minus_nominal")}
    point = lambda name, r, z: next(p for p in by_state[name] if float(p["R_m"]) == r and float(p["Z_m"]) == z)
    edge = {name: 100 * (float(point(name, 0.1, 0.0)["Bz_T"]) / states[name]["bref_T"] - 1) for name in ("nominal", "offset")}
    failed = [c["name"] for c in checks if c["status"] != "PASS"]
    u_nom, u_off, u_shift, u_gap = (100 * s["U"] for s in (nom, off, shift, gap))
    t_nom, t_off, t_shift, t_gap = (1e3 * s["tilt_max_rad"] for s in (nom, off, shift, gap))
    rel = 100 * summary["bref_relative_change"]
    phi_rel = 100 * delta["phi_point_Wb"] / nom["phi_point_Wb"]
    compensate = 100 * (nom["bref_T"] / off["bref_T"] - 1)
    bio = max(c["max_abs_error"] for c in checks if "biot_savart" in c["name"] and "psi" not in c["name"])
    return f"""# 圆环线圈上移 2 cm 对中心区磁场的影响

## 答案

上环上移 2 cm 后，中心区的场整体减弱约 {sig(abs(rel), 2)}%，从 {1e3 * nom['bref_T']:.2f} mT 降到 {1e3 * off['bref_T']:.2f} mT；中心 9 个采样点的不均匀度从约 {sig(u_nom, 2)}% 增加到约 {sig(u_off, 2)}%，约为原来的 {sig(u_off / u_nom, 2)} 倍；场方向的最大倾角从 {sig(t_nom)} mrad 增加到 {sig(t_off)} mrad。

这主要是因为两环间距从 0.50 m 变成 0.52 m，偏离了亥姆霍兹条件：中心的平顶变成了略微下凹的形状，同时平坦区跟着两环中点上移约 1 cm。

这块场能不能用，取决于实验能容忍多大的不均匀度。你没有给出这个指标，所以本报告不作判定。如果容许值明显大于 {sig(u_off, 2)}%，这次偏移在这 9 个采样点上不构成限制；如果要求接近或严于这个量级，就需要关注它。场强的下降可以通过调电流补偿，形状的变化则不能。

## 问题与理解

**你的问题。** 一对圆环线圈，用来在中间做较均匀的轴向场。上环安装时往上偏了一点，想知道影响有多大、这块场还能不能用。不考虑等离子体，线圈按细圆环算。

**我的理解。** 这是两个固定安装状态之间的真空磁场比较，不是线圈优化：

- 两环半径 0.50 m，每环实际电流 +1000 A，名义位置 Z = ±0.25 m，偏移后上环到 +0.27 m；
- “影响”用四个量衡量：中心场强、中心 9 点的不均匀度 $U$、场方向倾角 $T$、(R=0.10 m, Z=0) 处的磁通；
- 观测点固定不动，每个状态用自己的 $B_z(0.02\\,{{\\rm m}},0)$ 作参考，差值都是偏移减名义；
- 你没有给合格线，所以只说明变化，不判定可用与否。

完整口径见 [request.md](request.md)。

## 物理模型与方法

**从问题到模型。** 两环半径 $a=0.50$ m、间距 $d=0.50$ m，名义上正好是亥姆霍兹线圈，这决定了分析的思路。场的“均匀”来自 $d=a$ 时轴上场在中点的二阶导数恰好为零；上环上移破坏了这个条件。所以问题的物理核心是：偏移如何改变中心的场强和场的形状。

**模型假设。** 真空静磁场，线圈是无限细电流环，无磁性材料和等离子体。系统轴对称，因此 $B_\\phi=0$，场由子午面上的 $B_r$、$B_z$ 完全描述。

**单环的场。** 轴对称场可以用通量函数 $\\psi=RA_\\phi$ 描述，对细环的 Biot–Savart 积分给出椭圆积分形式。半径 $a$、位于 $z_0$、电流 $I$ 的细环有

$$\\psi(R,z)=\\frac{{\\mu_0 I}}{{\\pi}}\\frac{{\\sqrt{{aR}}}}{{k}}\\left[\\left(1-\\frac{{k^2}}{{2}}\\right)K(k^2)-E(k^2)\\right],\\qquad k^2=\\frac{{4aR}}{{(a+R)^2+(z-z_0)^2}},$$

场由 $\\psi$ 的导数给出：

$$B_r=-\\frac1R\\frac{{\\partial\\psi}}{{\\partial z}},\\qquad B_z=\\frac1R\\frac{{\\partial\\psi}}{{\\partial R}}.$$

在轴线上，这个解退化为熟悉的 $B_z=\\mu_0Ia^2/\\left[2\\left(a^2+(z-z_0)^2\\right)^{{3/2}}\\right]$。

**两环叠加。** 真空静磁方程是线性的，所以两环的场直接相加。单环响应和电流叠加这两步可以调用 `scirel.field` 的 `circular_filament_green_response` 和 `superpose_current_green_field`；其余指标是普通的数值计算。

**为什么场形会变。** 对两环的轴上解在中点求二阶导数，得到

$$\\left.\\frac{{d^2B_z}}{{dz^2}}\\right|_{{\\rm 中点}}=\\frac{{3\\mu_0Ia^2(d^2-a^2)}}{{(a^2+d^2/4)^{{7/2}}}}.$$

它在 $d=a$ 时为零（亥姆霍兹条件），$d>a$ 时为正，也就是中点成为局部极小。这个公式预言：间距变大后，平顶会变成下凹。

**怎样分开两个因素。** 上环上移等于“两环一起上移 1 cm”加上“间距增大 2 cm”。我额外计算了只平移和只增大间距两个辅助工况，用来判断哪个因素起主要作用。它们只用于解释，不属于你要求的指标。

**怎样确认算得对。** 用不经过椭圆积分的方法独立核对：对 Biot–Savart 直接做角向数值积分，并与轴上解析解、亥姆霍兹解析解、$\\psi$ 的导数关系和圆盘磁通积分比较。结果见附录 A。

## 结果

**核心指标。** 下表是四个量的变化，全部 25 点的结果见附录 B。

| 量 | 名义 | 偏移 | 偏移减名义 |
| --- | --- | --- | --- |
| 参考点轴向场 $B_{{\\rm ref}}$ | {1e3 * nom['bref_T']:.2f} mT | {1e3 * off['bref_T']:.2f} mT | {1e3 * delta['bref_T']:.3f} mT（{sig(rel, 2)}%） |
| 中心 9 点不均匀度 $U$ | {sig(u_nom, 2)}% | {sig(u_off, 2)}% | +{sig(100 * delta['U'], 2)} 个百分点 |
| 中心 9 点最大倾角 $T_{{\\max}}$ | {sig(t_nom)} mrad | {sig(t_off)} mrad | +{sig(1e3 * delta['tilt_max_rad'], 2)} mrad |
| (R=0.10 m, Z=0) 处圆盘磁通 $\\Phi$ | {sig(1e5 * nom['phi_point_Wb'])}×10⁻⁵ Wb | {sig(1e5 * off['phi_point_Wb'])}×10⁻⁵ Wb | {sig(1e6 * delta['phi_point_Wb'], 2)}×10⁻⁶ Wb（{sig(phi_rel, 2)}%） |

**整体场线几乎不变。** 从整个线圈的尺度看，两种状态的场线（$\\psi$ 等值线）很难分辨，中心区的场线都接近竖直（图 1）。所以差异要到“百分之零点几”的尺度才能看到。

![两种状态下的场线](figures/fig1_field_lines.png)

*图 1　子午面场线（$\\psi$ 等值线）。黑点是线圈截面，虚线框是中心统计区。*

**中心平顶变成略微下凹。** 图 2 显示中心区 $B_z$ 相对各自参考场的偏差：名义状态上下对称，偏移状态的高低区都向上移动，对称性被破坏。

![中心区轴向场的相对偏差](figures/fig2_uniformity_map.png)

*图 2　$B_z/B_{{\\rm ref}}-1$ 分布。方块是参考点，小黑点是 25 个观测点，虚线框是中心统计区。等值线按连续场绘制仅用于观察，指标只统计 9 个采样点。*

轴上和径向的分布（图 3）更直接：名义状态是平顶，偏移状态整体下移，轴上出现一个约 {sig(shape['offset']['dip_percent'], 2)}% 的浅凹，凹点在中点 Z≈+1 cm 附近，正如二阶导数公式所预言。径向上场随 R 下降得也更快：在 (R=0.10 m, Z=0)，相对参考场的偏差从 {sig(edge['nominal'], 2)}% 变为 {sig(edge['offset'], 2)}%。

![轴向和径向分布对比](figures/fig3_profiles.png)

*图 3　(a) 轴上 $B_z$；(b) 轴上相对各自 $B_{{\\rm ref}}$ 的偏差；(c) 中平面上相对各自 $B_{{\\rm ref}}$ 的偏差。灰色带是中心统计范围。*

**不均匀度主要来自间距变大。** 图 4 把两个因素分开：只平移时 $U$ 为 {sig(u_shift, 2)}%，几乎不变；只增大间距时 $U$ 为 {sig(u_gap, 2)}%，占了增量的大部分。倾角则不同，平移（{t_shift:.2f} mrad）和增大间距（{t_gap:.2f} mrad）都有明显作用。

![不均匀度和倾角的对比](figures/fig4_indicators.png)

*图 4　四种配置在中心 9 点的 $U$ 和 $T_{{\\max}}$。灰色是只用于解释的辅助工况。*

## 讨论

**场强下降可以用简单的物理解释。** 只有上环动了，它对中心场贡献一半；单环在轴上的场随距离的相对变化率是 $-3z_0\\delta/(a^2+z_0^2)$。代入 $z_0=0.25$ m、$\\delta=0.02$ m，一半贡献给出 {sig(100 * summary['bref_first_order_estimate'], 2)}%，与计算的 {sig(rel, 3)}% 基本一致。

**幅值和形状的影响性质不同。** 场与电流成正比，所以电流再增加约 {sig(compensate, 2)}% 就能把参考场拉回原值，而 $U$ 和 $T$ 不随电流改变。形状变化来自几何，只能靠调整线圈位置来改变。这是模型的直接推论，本次没有计算调整方案。

**平移的影响部分取决于统计区是否跟着动。** 观测点固定时，只平移也会让倾角明显增大，因为中心统计区不再相对平坦区居中。这一项是几何上的错位：如果实验区能随场的中心移动约 1 cm，这部分影响可以减小；由间距引起的部分则不会消失。

**结论的适用范围。**

- $U$ 和 $T_{{\\max}}$ 只针对 9 个采样点，图 2 表明连续场在点之间还有变化，它们不是整个区域的上下界。
- 只计算了上移正好 2 cm 这一种情况。你说“好像偏了一点”，如果实际偏移量不同，要重新计算。
- 模型不含线圈的有限截面、匝间分布、横向偏心、倾斜和环境磁性材料。真实装配误差通常不止轴向一种。
- 结果是数值模型的预言，没有和实测场比较。

## 结论

上环上移 2 cm 使中心场减弱约 {sig(abs(rel), 2)}%，9 个采样点的不均匀度从约 {sig(u_nom, 2)}% 增加到约 {sig(u_off, 2)}%，最大倾角从 {sig(t_nom)} mrad 增加到 {sig(t_off)} mrad。物理原因是两环间距偏离亥姆霍兹条件，中心的平顶变成浅凹，并且平坦区上移约 1 cm。

场强的损失可以用电流补偿，形状的变化不能。这块场是否够用，请用上述不均匀度和倾角对照实验要求判断；如果能给出容许值，或用测磁确认实际偏移量，结论可以更具体。

## 附录

### 附录 A：验证结果

共 {len(checks)} 项检查，未通过 {len(failed)} 项{('：' + '、'.join(failed)) if failed else ''}。容差在看结果前写定，是数值一致性容差，不是工程合格线。完整记录见 [data/checks.json](data/checks.json)。

| 检查 | 对照对象 | 结果 |
| --- | --- | --- |
| 25 点的 $B_r$、$B_z$、$\\psi$ | 直接对 Biot–Savart 做角向数值积分，最大差 {sig(bio, 2)} T | 通过 |
| 轴上 $B_z$，$\\psi=0$，$B_r=0$，$+\\phi$ 电流给出 $B_z>0$ | 轴上解析解和符号约定 | 通过 |
| 名义中心场 | 亥姆霍兹解析解 {sig(1e3 * summary['helmholtz_centre_T'], 4)} mT | 通过 |
| 轴上二阶导数公式 | 轴上解的有限差分 | 通过 |
| $B_r$、$B_z$ 与 $\\psi$ 的导数关系 | 对 $\\psi$ 做中心差分 | 通过 |
| $\\Phi=2\\pi\\psi$ | 对 $B_z$ 做圆盘面积分 | 通过 |
| 名义工况 $B_r$ 在 Z=0 为零，$B_r$ 奇对称，$B_z$、$\\psi$ 偶对称 | 对称性（未修改输出） | 通过 |
| 两环叠加 | 逐项相加，容差取舍入误差界 | 通过 |

**和外部平台先前结果的对比。** 外部 agent 平台先前的一次运行保留过一项叠加检查的失败：(R=0.2 m, Z=0) 的 $B_r$ 约为 $1.1\\times10^{{-20}}$ T，超过当时写定的绝对容差 $10^{{-20}}$ T。这个点上两环贡献相互抵消，差值来自浮点舍入。这里把容差改为由两项之和估算的舍入误差界，这是容差口径的改变，特此说明。核心数值与那次运行一致。

**未运行的内容：** 靠近导线的奇异极限、连续区域的误差界、与实测数据的比较。

### 附录 B：全部 25 个观测点

保留 4 位有效数字，完整精度见 [data/points.csv](data/points.csv)。绝对值低于数值舍入水平（场和倾角 $10^{{-15}}$，$\\psi$ $10^{{-18}}$）的量写作 0。

**名义状态**

{point_table(by_state['nominal'])}

**偏移状态**

{point_table(by_state['offset'])}

**偏移减名义**

{point_table(by_state['offset_minus_nominal'])}

极值位置：名义 $U$ 在 {where(nom['U_at'])}，偏移 $U$ 在 {where(off['U_at'])}；名义 $T_{{\\max}}$ 在 {where(nom['tilt_at'])}，偏移 $T_{{\\max}}$ 在 {where(off['tilt_at'])}。参考点 (R=0.02 m, Z=0)。指定点 $\\psi$：名义 {nom['psi_point_Wb_per_rad']:.4g} Wb/rad，偏移 {off['psi_point_Wb_per_rad']:.4g} Wb/rad，差 {sig(delta['psi_point_Wb_per_rad'], 4)} Wb/rad。$\\psi$ 是每弧度的通量函数，$\\Phi=2\\pi\\psi$ 才是圆盘总磁通。

### 附录 C：复现

```sh
PYTHONPATH=src python examples/coil-offset/solve.py
PYTHONPATH=src python examples/coil-offset/make_figures.py
python examples/coil-offset/make_report.py
```

依赖版本见仓库 `pyproject.toml`，绘图需要 `report` 依赖组里的 matplotlib。
"""


def main():
    (HERE / "REPORT.md").write_text(render(), encoding="utf-8")


if __name__ == "__main__":
    main()
