# SciRel 首次整版待审 successor r6

状态：**开发期冻结待审材料，不是科学认可或公开发行**。上一份 [r5](review-version-2026-09-25-r5.md) 的版本和证据保持原样；它不是可信基线。本轮的确切代码树、wheel、catalog、文档与测试证据由另存 review manifest 绑定。

## 首次审核集合

SciRel 仍无上一可信版本，因此专家首次审核对象是当前 **68 个公共资产（56 个 Operator、12 个 TaskGraph）** 及受影响的组合合同，不是只看 r5 到 r6 的 Git diff。`catalog/examples` 已有 **32** 份 exact documents，开发 catalog 为 `partial: 32/68`；还有 **36** 份缺科学合同文档，不能晋级完整可信版。既有 27 份文档随实现版本机械更新，不意味着科学行为或认可状态变化。

相对 r5，本轮为五项**已有** Operator 补 exact documents：

- [镜像对称等离子体磁通 Green 矩阵](../../catalog/examples/scirel.field.mirror-plasma-green.json)：固定对称 R-Z 网格、每安培响应，不含电流收缩或面积因子；与其他场关系的区别见[场领域草稿](../domains/axisymmetric-fields.md)。
- [磁通坐标标量剖面](../../catalog/examples/scirel.geometry.flux-surface-profile.json)和[折线 `dl/B` 测度/加权平均](../../catalog/examples/scirel.geometry.flux-surface-inverse-field-average.json)：不同坐标与计算步骤，详见[几何领域草稿](../domains/flux-coordinate-sampling.md)。前者被现有 grid-mirror-kinetic 组合图调用；该图尚缺 exact document，不能因此宣称组合链已经完整审核。
- [平行压强关系残差](../../catalog/examples/scirel.diagnostics.parallel-pressure-residual.json)和[火焰管/磁镜压强裕度](../../catalog/examples/scirel.diagnostics.firehose-mirror-margins.json)：按 `B` 值排序的样本导数，不是空间梯度；Pa 裕度与既有无量纲指标保持分立，详见[诊断领域草稿](../domains/anisotropic-pressure-diagnostics.md)。

没有新增或修改科学实现、直接测试或 TaskGraph；旧来源字节和先前待审快照没有改写。第一阶段当前合格 D1 交付根仍为空，保存的 Pleiades 等候选只能作为有界历史开发证据。旧 `admitted` 标签不授权本版本，内部 wheel 的可运行性不代替专家科学认可。

## 专家待决

- 五项新文档的科学适用域、来源资格、重复/变体关系和反向图依赖；尤其是折线路径能否代表完整磁面、B 值有限差分是否足以支撑目标诊断、Green 矩阵对称性构造的适用边界。
- 剩余 36 份 exact documents、现有 12 个 TaskGraph 的领域审阅、合格 L1 重冻后的来源核验，以及公共分发许可证。
- 专家只认可部分内容时，需在新的开发 successor 中剔除或返工并重新冻结；不能改写 r6 或把开发门禁通过当成可信晋级。`scripts/check.ps1 -Mode release` 仍关闭。
