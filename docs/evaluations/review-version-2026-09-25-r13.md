# SciRel 首次整版待审 successor r13

状态：**开发期待审材料，不是科学认可或公开发行**。r12 冻结快照保持原样。本轮不修改科学 callable 或 TaskGraph 运行代码，补齐当前六份缺失的 exact documents、两个领域草稿中的接线边界，并新增外层公开图的直接端口回归；内部构建版本为 `0.1.0.dev15`。

## 首次审核范围与本轮增量

目前没有上一可信版本。专家首次审核仍需覆盖 **68 个公共资产（56 Operator、12 TaskGraph）**、反向依赖及组合合同，而不只是 r12 到 r13 的差异。开发 catalog 为 `complete: 68/68`；这里的 complete 仅指当前公共资产的 exact-document 覆盖，不表示完整科学能力、专家认可或可信发行。既有 62 份文档仅机械更新 `implementation_version`，不因此产生新的科学证据。

本轮补齐 [Hall 双流体压强](../../catalog/examples/scirel.closures.hall-two-fluid-pressure.json)、[镜端双极电势](../../catalog/examples/scirel.closures.mirror-ambipolar-potential.json)、[表格压强](../../catalog/examples/scirel.closures.tabulated-pressure.json)、[镜不变量分布](../../catalog/examples/scirel.kinetic.mirror-invariant-distribution.json)、[网格镜端闭合图](../../catalog/examples/scirel.kinetic.grid-mirror-kinetic-closure.json)和[动理学镜约化 Hall 图](../../catalog/examples/scirel.equilibrium.kinetic-mirror-hall-equilibrium.json)。两张图的文档列出嵌套依赖及图内状态、顺序和边界；catalog 反向依赖可供专家从改变的关系追踪下游。领域草稿见[镜端动理学与准中性](../domains/mirror-kinetics-and-quasineutrality.md)及[各向异性 Picard 平衡](../domains/anisotropic-picard-equilibrium.md)，由专家决定最终领域结构。

## 验证与证据上限

独立工程审阅核对六份文档、依赖反向链接和覆盖语义，未报告阻断发现；这不是领域专家认可。全套测试 **864 passed、43 skipped**；68 份文档源码态的结构、签名和示例验证通过。内部 wheel `0.1.0.dev15` 的安装态相关测试 **52 passed**，68 份文档安装态签名和示例验证通过。确切 wheel、catalog 摘要与环境限制见冻结快照的 `test-evidence.md`。

外层 Hall 图新增回归只验证注入的动理学图和 Hall 图之间的当前 `B,psi` 端口传递；**未**运行真实两图端到端数值、共同收敛或物理验收。网格镜端图需要同一参考剖面同时支持一维端态行和二维局部网格；固定二维数组未必可直接接入。端塞外屏蔽只作用于选定的顶层字段，嵌套返回的原始矩和诊断仍有全网格值。Hall 双流体压强不自动核对显式离子分量与总压强的相容性。测试没有证明任意输入下的模型适用性。

本轮没有消费新的合格 L1：第一阶段合格交付根仍为空。历史 Pleiades 等来源记录只可作为开发对照，不是新一轮已核验冻结原料或本版本科学认可。合格 D1 到来后应比较现有开发基线与未发布候选，按关系族和依赖闭包整合。

## 专家与跨线待决

- 首次 68 资产的模型、单位、边界、适用域、来源许可证、科学测试及组合反向依赖；文档覆盖不代替逐项科学判断。
- 镜端 `psi` 历史 `Wb` 标签与真空场 `psi = R A_phi` 的 `Wb/rad` 约定，及网格剖面在嵌套图中的一维/二维端口适配。
- 真实网格镜端闭合与 Hall 反馈联算、共同收敛、端损失与局部准中性的一致性，以及未收敛末态的下游资格。
- 版本级专家认可与可信晋级尚未实现；公开发行和 `scripts/check.ps1 -Mode release` 继续阻断。

专家只认可部分内容时，应在隔离开发版剔除或返工，再验证并冻结 successor；不得改写本快照。
