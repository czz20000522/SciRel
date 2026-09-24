# SciRel 首次整版待审 successor r10

状态：**开发期待审材料，不是科学认可或公开发行**。r9 保留为开发历史；其 14 份 exact-document 清单 SHA-256 绑定了 Windows 工作树字节，却未在快照中保存该原始字节。JSON 科学记录与 catalog 相同，但仅凭 r9 目录和提交不能复验这些 raw-byte 摘要。本轮修正冻结器，在不可覆盖的 successor 内保存文档和审核说明原始字节，并逐项核对复制后的 catalog、wheel、测试证据和文档；不改写 r9。

## 首次审核范围

目前没有上一可信版本。专家首次审核仍覆盖 **68 个公共资产（56 Operator、12 TaskGraph）** 和组合合同，不是仅看 r9 到 r10 的文件 diff。本轮新增三份既有 Operator 的 exact documents，开发 catalog 达到 `partial: 53/68`（45 Operator、8 TaskGraph），尚缺 **15** 份。其余 50 份文档的 `implementation_version` 从 `0.1.0.dev11` 改为 `0.1.0.dev12` 是开发包绑定；除下列磁通单位合同外，不表示科学行为变化。本轮没有修改科学 callable 或 TaskGraph 运行代码。

## 本轮材料

- [准中性参考电子密度](../../catalog/examples/scirel.closures.quasineutral-reference-density.json)和[Boltzmann 电子态/准中性残差](../../catalog/examples/scirel.closures.boltzmann-quasineutrality.json)：补齐镜端准中性闭包的两个无依赖叶节点；文档限定广播、零密度、指数截断和派生数值的证据上限。
- [损失锥 Legendre 谱](../../catalog/examples/scirel.kinetic.loss-cone-spectrum.json)：补齐 Frank-Egedal 关系族的一个叶节点；文档明确有限求根扫描、默认截断近似、采样端点和未证明的谱完整性。
- [P4 磁通约定开发修正](p4-flux-convention-development-2026-09-25.md)：圆丝 Green、当前叠加、多线圈真空场和磁通导场的四份文档改为 `psi = R A_phi` / `Wb/rad`，每安培 Green 响应为 `Wb/rad/A`。新的独立场-磁通数值回归区分不乘 `2*pi` 的当前实现与错误的完整环连磁通接法。数值、签名和返回键没有变化；原 `Wb` 标签的消费者有单位解释兼容影响。
- [轴对称场领域草稿](../domains/axisymmetric-fields.md)限定上述开发合同的范围。其他稠密/镜像 Green、边界和各平衡图仍有旧单位标签，**不能据本轮材料把真空 `psi_vac` 直接接入平衡图或材料支撑**。

三份新文档有独立审阅，未发现具体合同不符；冻结器修复经独立复查和 CRLF/脱离 checkout/变更识别回归。受影响门禁因开发版本号变更运行全套：**862 passed、43 skipped**。53 份文档的源码态签名与示例校验通过。wheel、安装态与冻结目录的确切结果见该快照 `test-evidence.md`；这些工程证据不产生专家认可。

本轮没有消费新的合格 L1，第一阶段当前合格 D1 交付根为空。历史 Pleiades 和其他保存产物只能作为确切开发来源对照，不能据此声称第一阶段完整冻结或本版本科学批准。

## 专家与出库待决

- 首次 68 资产的模型、单位、几何、边界、适用域和反向依赖科学审核；新增三份文档后尚缺的 15 份 exact documents。
- 圆丝真空链之外的 Green/平衡磁通约定和 `2*pi`、参考边界、字段命名；出库侧需用本轮确切开发 wheel/catalog 复测 P4 真空预览，并继续阻断未经审查的平衡接线。
- 历史来源重新获得合格 D1 冻结后的资格、来源许可证、版本级可信晋级及公开发行授权。

专家只认可部分内容时须从开发 successor 剔除或返工，再重新构建和冻结；不能修改本快照的审核标签。`scripts/check.ps1 -Mode release` 仍保持阻断。
