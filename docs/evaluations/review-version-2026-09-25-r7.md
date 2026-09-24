# SciRel 首次整版待审 successor r7

状态：**开发期冻结待审材料，不是专家科学认可或公开发行**。上一份 [r6](review-version-2026-09-25-r6.md) 的版本、目录和证据保持原样。本轮确切代码树、wheel、catalog、文档和测试由另存的 review manifest 绑定。

## 首次审核集合

SciRel 尚无上一可信版本。专家首次审核对象仍是当前 **68 个公共资产（56 个 Operator、12 个 TaskGraph）** 及组合合同，而不是仅看 r6 到 r7 的 Git diff。`catalog/examples` 现有 **36** 份 exact documents（32 个 Operator、4 个 TaskGraph），开发 catalog 为 `partial: 36/68`；其余 **32** 份仍缺科学合同文档，不能晋级完整可信版。旧有 32 份文档的 `implementation_version` 机械更新，不表示科学行为改变或获得认可。

相对 r6，本轮为四项**已有**公共资产补 exact documents，未新增或修改科学 callable：

- [各向同性压力磁通平衡图](../../catalog/examples/scirel.equilibrium.isotropic-pressure-flux.json)及其[压力磁通状态](../../catalog/examples/scirel.equilibrium.pressure-flux-state.json)、[Picard 单步](../../catalog/examples/scirel.equilibrium.isotropic-picard-step.json)：首次把现有有界反馈及两个算子的精确合同作为依赖闭包放入开发 catalog。`maxiter=0` 仍构造初始压力状态，有限不收敛返回末态；这些关系不覆盖各向异性平衡。
- [平衡合成点诊断图](../../catalog/examples/scirel.diagnostics.equilibrium-synthesis-diagnostics.json)：只依赖已文档化的双线性 R-Z 采样；根据请求采样给定平衡场。未请求的 `flux_loops`/`thomson` 输出键缺席，而非 `null`。它不求平衡，且不能无新科学关系地直接消费压力磁通图的 `P(psi)` 表示。

[领域草稿](../domains/isotropic-equilibrium-and-observations.md)记录两图的不同责任、可组合条件、证据上限和未决问题。已执行 direct tests、文档运行时签名及示例、全套科学回归和内部 wheel source-free 使用检查；具体结果以快照 `test-evidence.md` 为准。独立审阅对照实现、图 YAML、直接测试和 provenance，未发现具体阻塞，但不替代领域专家判断。

本轮没有消费新合格 L1。第一阶段当前合格 D1 交付根为空；Pleiades 保存记录仅是历史开发来源映射，旧 `review_pending` 或 `admitted` 标签不是本版本科学批准。

## 专家待决与发行边界

- 压力函数和精确零压力边界的物理适用域、Green 矩阵的归一化与方向、Picard 非收敛末态的下游使用，以及诊断输出的实际单位和仪器解释。
- 压力磁通图并不产生诊断图要求的二维压强场；跨图剖面投影若要复用，需独立科学关系与证据，不应仅凭相似字段名接线。
- 尚缺的 32 份 exact documents、全体图及反向依赖的专家审查、合格 L1 重新冻结后的来源核验和公共分发许可证。

专家只认可部分内容时，应在新开发 successor 剔除或返工并重冻，不改写 r7。`scripts/check.ps1 -Mode release` 仍关闭；开发 wheel 可用于内部验证，不能自行晋级可信或公开发行。
