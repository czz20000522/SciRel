# 磁场与线圈

状态：能力导航初稿，待领域专家确认分类和典型问题；不代表磁平衡或线圈物理的完整覆盖。

## 科学问题与输入

现有样例涉及给定圆形电流丝或矩形线圈截面，以及目标圆柱坐标 `R-Z` 网格时，计算轴对称**真空**磁通和极向磁场。线圈几何、驱动电流、网格及其单位和轴序以各 exact document 为准。

## 开发样例关系与组合

- [圆形电流丝 Green 响应](../../catalog/examples/scirel.field.circular-filament-green.json)描述加权电流丝到轴对称真空响应的叶子关系。
- [多线圈真空场](../../catalog/examples/scirel.field.multi-coil-vacuum-field.json)是组合 TaskGraph，依赖矩形线圈离散、Green 响应和电流叠加；准确端口及边见其 exact document。
- [磁通坐标标量剖面插值](../../catalog/examples/scirel.geometry.flux-surface-profile.json)对调用方提供的成对样本排序、去重和线性插值，支持显式常值端点；它不构造物理磁通面，也不换算 `Wb` 与 `Wb/rad`。
- [轴对称磁通导出极向场](../../catalog/examples/scirel.field.poloidal-field-from-flux.json)从调用方 `psi = R A_phi` 的 R-Z 网格值离散恢复 `B_R`、`B_Z` 和幅值，包含明确的轴上规则；它不解决真空场输出 `Wb` 与平衡侧 `Wb/rad` 标签之间尚待裁决的接线问题。
- [轴对称 Picard 磁通 Green 更新](../../catalog/examples/scirel.equilibrium.axisymmetric-picard-update.json)以首个网格间距形成单元电流，用稠密 Green 矩阵产生候选磁通，再对磁通而非电流做一次松弛；这是单步更新，求解循环由调用方负责。

这些链接来自 `catalog/examples/` 开发 pilot，不表示专家已认可或可公开发布。

## 证据、限制与待整理项

前两项真空场文档不证明等离子体电流响应、材料效应、三维非轴对称线圈或奇异自场；剖面插值也不证明调用方的物理坐标约定或样本单值性。磁通导出极向场的数值回归不构成真空场到平衡链路的磁通约定裁决。领域层面的平衡任务、跨资产接线证据及更多来源项目的关系仍**未整理**，不能据此断言缺失。相对上一可信版的变化：待建立可信版后由专家填写。
