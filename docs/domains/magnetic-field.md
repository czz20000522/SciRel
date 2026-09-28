# 磁场与线圈

状态：能力导航初稿，待领域专家确认分类和典型问题；不代表磁平衡或线圈物理的完整覆盖。

## 科学问题与输入

现有样例涉及给定圆形电流丝或矩形线圈截面，以及目标圆柱坐标 `R-Z` 网格时，计算轴对称**真空**磁通和极向磁场。线圈几何、驱动电流、网格及其单位和轴序以各 exact document 为准。

## 开发样例关系与组合

- [圆形电流丝 Green 响应](../../catalog/examples/scirel.field.circular-filament-green.json)描述加权电流丝到轴对称真空响应的叶子关系。
- [稠密轴对称 Green 响应](../../catalog/examples/scirel.field.dense-axisymmetric-green.json)逐列保留圆丝源的磁通与极向场响应，源权重无电流或面积含义；奇异项遵循零值约定。其磁通列与圆丝核数值一致，但两份公共文档的 `Wb/A` 与 `Wb/rad/A` 标签仍待科学裁决。
- [镜像等离子体磁通 Green 矩阵](../../catalog/examples/scirel.field.mirror-plasma-green.json)在等间距、关于零反射对称的 R-Z 网格上，以轴向反射索引扩展首平面圆丝响应；矩阵按 `[Z,R]` 的 C 顺序展开，返回值不含电流或面积因子。
- [圆丝真空场与径向磁通积分](../../catalog/examples/scirel.field.filament-vacuum-field.json)先叠加理想圆丝磁场，再从首个径向网格点梯形积分 `R B_Z`；其 `psi` 以该网格点为零位，不能与逐点绝对 Green 响应不经参考值调整就直接比较。
- [理想导体边界磁通校正](../../catalog/examples/scirel.field.ideal-conductor-boundary.json)对调用方给定的采样与 Green 矩阵做截断 SVD，返回等效边界电流、场磁通校正和残差。它只检查矩阵维度，不证明采样矩阵与两组 Green 响应的物理一致性。
- [多线圈真空场](../../catalog/examples/scirel.field.multi-coil-vacuum-field.json)是组合 TaskGraph，依赖矩形线圈离散、Green 响应和电流叠加；准确端口及边见其 exact document。
- [磁通坐标标量剖面插值](../../catalog/examples/scirel.geometry.flux-surface-profile.json)对调用方提供的成对样本排序、去重和线性插值，支持显式常值端点；它不构造物理磁通面，也不换算 `Wb` 与 `Wb/rad`。
- [轴对称磁通导出极向场](../../catalog/examples/scirel.field.poloidal-field-from-flux.json)从调用方 `psi = R A_phi` 的 R-Z 网格值离散恢复 `B_R`、`B_Z` 和幅值，包含明确的轴上规则；它不解决真空场输出 `Wb` 与平衡侧 `Wb/rad` 标签之间尚待裁决的接线问题。
- [轴对称 Picard 磁通 Green 更新](../../catalog/examples/scirel.equilibrium.axisymmetric-picard-update.json)以首个网格间距形成单元电流，用稠密 Green 矩阵产生候选磁通，再对磁通而非电流做一次松弛；这是单步更新，求解循环由调用方负责。
- [轴对称各向异性压强张量力平衡](../../catalog/examples/scirel.equilibrium.anisotropic-force-balance.json)在调用方给定的 R-Z 场与压强网格上计算张量散度、环向电流和沿场力诊断；活动掩码只影响诊断 RMS，函数不自行裁决压力闭包或低场物理有效性。
- [各向异性压强环向电流分解](../../catalog/examples/scirel.equilibrium.anisotropic-toroidal-current.json)两次调用上述力平衡关系，以全压强态与各向同性 `p_perp` 对照的差值定义各向异性分项；分项名称不表示独立离散的纯曲率公式。
- [Picard 磁通状态相对残差](../../catalog/examples/scirel.diagnostics.picard-flux-residual.json)比较相邻二维磁通状态的 L2 变化，采用 `1e-30 Wb` 分母地板；自由边界图将其用于停止判断，但这不裁决 `Wb/rad` 状态与 `Wb` 合同的接线。

这些链接来自 `catalog/examples/` 开发 pilot，不表示专家已认可或可公开发布。

## 证据、限制与待整理项

前两项真空场文档不证明等离子体电流响应、材料效应、三维非轴对称线圈或奇异自场；剖面插值也不证明调用方的物理坐标约定或样本单值性。磁通导出极向场的数值回归不构成真空场到平衡链路的磁通约定裁决。领域层面的平衡任务、跨资产接线证据及更多来源项目的关系仍**未整理**，不能据此断言缺失。相对上一可信版的变化：待建立可信版后由专家填写。
