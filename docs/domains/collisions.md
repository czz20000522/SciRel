# 碰撞相关量

状态：能力导航初稿，待领域专家确认分类和典型问题；当前示例不能代表碰撞模型的整体覆盖。

## 科学问题与输入

现有样例中，热电子温度和静止能量以相同能量单位给出，结果是无量纲的热速度比，而不是以长度/时间表示的速度。更完整的碰撞率、碰撞算子与耦合问题仍待逐项盘点。

## 开发样例关系与组合

- [热电子归一化动量](../../catalog/examples/scirel.collisions.thermal-electron-momentum.json)给出该定义及直接测试的证据范围。
- [归一化动量映射](../../catalog/examples/scirel.collisions.normalized-momentum.json)是相关但不同的关系；不能仅凭名称将两者直接串接。端口和量纲以各自 exact document 为准。
- [Maxwellian 相对速度速率平均](../../catalog/examples/scirel.collisions.maxwellian-relative-speed-rate-average.json)在调用方圆柱速度网格和截面模型上计算逐粒子能量的 `<sigma v>`。历史 `*_mass_amu` 参数表示保存氢质量 `1.6726231e-27 kg` 的倍数；碰撞能量使用粒子质量，未提供约化质量模型。

这些链接来自 `catalog/examples/` 开发 pilot，不表示专家已认可或可公开发布。

## 证据、限制与待整理项

热电子归一化动量文档明确排除将其直接作为归一化动量映射的 `vnorm`：那会重复除以光速。速率平均可消费圆柱速度空间积分权重的 `volume`，但不验证截面模型或网格收敛。其它碰撞关系、跨资产的合法组合和适用域仍**未整理**，不能解释为已证实缺口。相对上一可信版的变化：待建立可信版后填写。
