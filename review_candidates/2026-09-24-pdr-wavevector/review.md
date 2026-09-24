# 专家候选：x-z 平面实波矢投影

## 需作出的决定

建议新增 `scirel.geometry.planar-wavevector-projection`，以普通 Python callable
提供已采用逆米单位的实波矢模长/角度投影与成对分量模长计算。请判断这个科学身份、
SI 输入约定、两种声明方式和失败语义是否适合作为 SciRel 公共算子；如 PDRF
归一化输入需要专门换算，请要求补充该输入卡到 `1/m` 的明确映射再批准接线。
本候选不请求吸收 PDRK 的扫描状态机，也不请求更改任何已发布资产。

## 精确来源与关系

| 端点 | Exact L1 asset ID | Package digest | 已核对材料 |
| --- | --- | --- | --- |
| A | `PDRF:operator:plasma_k_projection` | `sha256:4bbb3dcd7ced270e1f41405cae7b9c727a4e253c994dfda6021dea2781fd691a` | `operator.md`, `scientific_operator.py`, 5 项直接测试, PDRF 框架图 N3、台账与报告 |
| B | `PDRK:operator:wavevector_projection` | `sha256:71b1b7790849f2839b9792d0a401f5ea3fb5ed621097c873f7e037b9a39dfc70` | `operator.md`, `scientific_operator.py`, 7 项直接测试, PDRK 框架图 N3、台账与报告 |

关系为 **有条件重叠**，不是两个完整算子的重复。A 的拟议动作是新增规范算子；
B 的拟议动作是暂留独立扫描变体，后续再审是否调用这个纯几何关系。
这两个动作与关系分类分开记录，不从重叠推导自动合并。

| 方面 | A / 拟议规范算子 | B | 可比较条件或差异 |
| --- | --- | --- | --- |
| 方向 | `k, theta -> kx, kz` 或 `kx, kz -> k` | 扫描选择器和可变 `par -> kx, kz, k, theta, par` | B 还有对数开关、逐点覆盖和状态输出，A 不处理。 |
| 坐标 | 背景场沿 z，实波矢在 x-z 平面；theta 为弧度 | 同一平面；theta 为度 | 极坐标几何关系相同，须显式 `deg -> rad`。 |
| 单位 | PDRF 合同写“来源程序波数单位”，可在归一化/SI 模式运行；提案要求调用者先给 `1/m` | `par` 中波数无量纲，`cwp` 以米给出；输出 `1/m` | 比较需要 `cwp>0` 且 `k_m_inv=abs(par[0])/cwp`。PDRF 的归一化输入卡换算未由本试验证明。 |
| 极坐标端口 | 一维 `k_grid`、标量 `theta_rad`；负模长拒绝 | 单点 `par[0]`、`par[1]`，可负扫描模长取绝对值 | 仅 `par[0]>=0`、无对数/状态更新影响、正归一化长度时能复用数值投影。 |
| 直角端口 | 成对一维 `kx_grid`,`kz_grid`，输出角度为 `None` | `ipa>2 && ipb>2` 时从 `par[2:4]/cwp` 取分量并反算角度 | 分量和模长可在显式映射后对照；角度输出合同不同。 |
| 零模长 | 保留输入角度 | `angle(0+0i)` 得 `0°` | 当输入角不为零，角度输出不等价，即使 `kx,kz,k` 都相同。 |
| 失败语义 | 有限非负模长、同长有限分量，否则 `ValueError` | `cwp!=0`、选择器/开关有效；负扫描模长可用 | B 的 `cwp<0` 虽被代码接受，却与“长度”语义及文档的非负模长声明冲突，留作 B 单独审查。 |
| 大分量数值 | 直角模长用 `hypot`，保持可表示的有限结果 | A 来源实现用 `sqrt(kx**2+kz**2)` | `kx=1e200,kz=0` 时 A 来源先溢出为 `inf`，提案返回 `1e200`；这是明确的数值行为变更。 |

端口映射只在上述条件下成立：B `par[0]/cwp -> A.k_grid[0]`，
`par[1]*pi/180 -> A.theta_rad`，B `kx/kz/k -> A.kx[0]/kz[0]/k[0]`；
直角分支是 `par[3]/cwp -> A.kx_grid[0]`、
`par[2]/cwp -> A.kz_grid[0]`。没有把该映射传递到其他算子或 TaskGraph。

## 公共 API 和依赖影响

拟议入口为 `scirel.geometry.planar_wavevector.project_planar_wavevector`
及领域导出 `scirel.geometry.project_planar_wavevector`。源码在
`proposal/planar_wavevector.py`，尚未进入维护包。它只使用现有 NumPy，
没有 SciRel 资产依赖。A 的反向图为 `fluid_dispersion_branch_sweep`；
B 的反向图为 `kinetic_dispersion_scan` 和 `pdrk_main_pipeline`。
这些图将来如改接规范算子，必须另审端口、扫描状态及全部图测试。

## 证据、限制与后续

`proposal/test_planar_wavevector.py` 直接加载两份冻结实现对照，观察到：
极坐标正模长的 `kx/kz/k` 在显式单位与角度映射后相合；直角分支的
通常有限分量和模长相合；零模长角度、负模长、`par` 状态、极端分量
溢出及负 `cwp` 的几何方向明确不同。
首次运行发现零模长角度差异，测试据此保留区分性断言；修正断言后
`7 passed`。这证明受测数值关系与差异，不证明两个完整合同等价，
也不证明来源模型在所有物理域正确。

PDRF/PDRK 的 D1 source parity 和严格冻结属于来源证据。当前 SciRel
科学树在 Git base 下未有同类公共 callable；14/62 开发 catalog 的缺项
没有用于推断此结论。本地可见的 77 条旧候选行也未检索到同一波矢输出，
但平台审核队列尚未重新核对。分发许可仍需人工确认。专家可批准这个有界
新算子、要求明确 PDRF 归一化换算后再审，或要求保留两个独立变体。
