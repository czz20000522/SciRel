# SciRel 首次整版待审 successor r5

状态：**开发期冻结待审材料，不是科学认可或公开发行**。上一份 [r4](review-version-2026-09-25-r4.md) 的确切快照与证据保持原样；r4 不是可信基线。本轮版本、代码树、wheel、catalog 和测试记录以另存 review manifest 为准。

## 首次审核集合

SciRel 仍无上一可信版本，故专家首次审核对象不是 r4 到 r5 的四份文档增量，而是当前 **68 个公共资产（56 个 Operator、12 个 TaskGraph）** 及其反向依赖与组合合同。`catalog/examples` 现有 **27** 份 exact documents，依赖闭合开发 catalog 为 `partial: 27/68`；**41** 份仍缺科学合同文档，不能晋级完整可信版。r4 的 23 份文档仅机械更新 implementation version；科学函数没有因该版本号变化获得新证据。

本轮为四项现有 field Operator 补 exact documents：[固定永磁环电流丝](../../catalog/examples/scirel.field.permanent-ring-filaments.json)、[理想导体边界修正](../../catalog/examples/scirel.field.ideal-conductor-boundary.json)、[圆丝网格真空场](../../catalog/examples/scirel.field.filament-vacuum-field.json)、[稠密 Green 矩阵](../../catalog/examples/scirel.field.dense-axisymmetric-green.json)。未新增或修改科学实现/TaskGraph。关系之间的输入权重、电流、矩阵列和磁通参考差异见[领域草稿](../domains/axisymmetric-fields.md)；它是专家组织讨论的材料，不替代逐项认可。

第一阶段当前合格 D1 交付根仍为空。既有 Pleiades、fluidBW 与其他保存候选均只作为有版本身份的历史开发证据；本轮没有把保存字节重新宣称为合格 L1。`provenance/admitted-assets.json` 的旧决定字段不授权本快照。内部开发 wheel 可以安装运行，但 `-Mode release` 仍关闭。

## 专家待决

- 四项 field 文档的物理条件、磁通约定、奇点处理和 Green 关系复用边界；特别是边界修正的 `S @ Gbf = Gbb` 一致性由调用方承担，当前实现不验证。
- 余下 41 份 exact documents 和 12 个 TaskGraph 的领域结构、科学闭包及反向依赖审核；合格 L1 重冻后的来源核验。
- 公共分发许可证。专家只认可部分内容时，需在新的开发 successor 中剔除或返工并重新冻结，不改写 r5；开发自动测试不能自行把版本晋级可信。
