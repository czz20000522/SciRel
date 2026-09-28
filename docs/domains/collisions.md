# 碰撞相关量

状态：能力导航初稿，待领域专家确认分类和典型问题；当前示例不能代表碰撞模型的整体覆盖。

## 科学问题与输入

现有样例中，热电子温度和静止能量以相同能量单位给出，结果是无量纲的热速度比，而不是以长度/时间表示的速度。更完整的碰撞率、碰撞算子与耦合问题仍待逐项盘点。

## 开发样例关系与组合

- [热电子归一化动量](../../catalog/examples/scirel.collisions.thermal-electron-momentum.json)给出该定义及直接测试的证据范围。
- [归一化动量映射](../../catalog/examples/scirel.collisions.normalized-momentum.json)是相关但不同的关系；不能仅凭名称将两者直接串接。端口和量纲以各自 exact document 为准。
- [Maxwellian 相对速度速率平均](../../catalog/examples/scirel.collisions.maxwellian-relative-speed-rate-average.json)在调用方圆柱速度网格和截面模型上计算逐粒子能量的 `<sigma v>`。历史 `*_mass_amu` 参数表示保存氢质量 `1.6726231e-27 kg` 的倍数；碰撞能量使用粒子质量，未提供约化质量模型。
- [原子氢电荷交换截面](../../catalog/examples/scirel.collisions.atomic-hydrogen-charge-exchange-cross-section.json)给出 H 与 H+ 的 Janev 拟合及可选 Freeman–Jones 分支，两个分支有各自的能量截断区间。
- [原子氢电荷交换速率系数](../../catalog/examples/scirel.collisions.atomic-hydrogen-charge-exchange-rate-coefficient.json)按温度和撞击能量评价独立的双变量拟合；它不是上述截面的运行时 Maxwellian 积分，超出拟合区间沿用端点剪裁。
- [分子氢电荷交换截面](../../catalog/examples/scirel.collisions.molecular-hydrogen-charge-exchange-cross-section.json)给出 H2 与 H2+ 的 Janev 拟合，不能与原子氢同名通道互换。
- [原子氢弹性截面](../../catalog/examples/scirel.collisions.atomic-hydrogen-elastic-cross-section.json)保留 H–H 动量转移和黏滞两组不同系数。
- [原子氢与分子氢弹性截面](../../catalog/examples/scirel.collisions.atomic-molecular-hydrogen-elastic-cross-section.json)保留保存实现的前置单例输出轴。
- [质子与原子氢弹性截面](../../catalog/examples/scirel.collisions.proton-atomic-hydrogen-elastic-cross-section.json)保留 10 eV 处严格分支产生的零值及前置单例输出轴；该断点仍待专家判定。
- [质子与分子氢弹性截面](../../catalog/examples/scirel.collisions.proton-molecular-hydrogen-elastic-cross-section.json)给出 H2–H+ 的动量转移拟合。
- [分子氢弹性截面](../../catalog/examples/scirel.collisions.molecular-hydrogen-elastic-cross-section.json)保留 H2–H2 的同一拟合及 `viscosity=True` 的来源回退语义。
- [原子氢四族碰撞矩阵](../../catalog/examples/scirel.collisions.atomic-hydrogen-collision-matrices.json)在归一化柱坐标速度网格上组装 CX、H–H、H–H2 与 H–H+ 的 SIG 核；截面绑定上列四个独立算子。
- [分子氢四族碰撞矩阵](../../catalog/examples/scirel.collisions.molecular-hydrogen-collision-matrices.json)组装 CX、H2–H、H2–H+ 与 H2–H2 的 SIG 核；分子 CX 保留与原子侧不同的完整能量因子。
- [原子氢弹性 Omega 聚合](../../catalog/examples/scirel.collisions.atomic-hydrogen-omega-frequencies.json)从分布、Alpha 场与 H–H 矩阵归约三个频率通道；零速度差和零垂直矩显式失败。
- [分子氢弹性 Omega 聚合](../../catalog/examples/scirel.collisions.molecular-hydrogen-omega-frequencies.json)保留 H2–H 求和内除法和与原子侧不同的零累计矩分支。

这些链接来自 `catalog/examples/` 开发 pilot，不表示专家已认可或可公开发布。

## 证据、限制与待整理项

热电子归一化动量文档明确排除将其直接作为归一化动量映射的 `vnorm`：那会重复除以光速。速率平均可消费圆柱速度空间积分权重的 `volume`，但不验证截面模型或网格收敛。七项截面、两项矩阵和两项 Omega 聚合仍是保存公式的开发期重装，物理截面外部校验、矩阵守恒或正定性 oracle 尚未完成。其它碰撞关系、跨资产的合法组合和适用域仍**未整理**，不能解释为已证实缺口。相对上一可信版的变化：待建立可信版后填写。
