# SciRel 首次整版待审 successor r9

状态：**开发期待审材料，不是科学认可或公开发行**。只有新 review manifest 对 Git tree、wheel、catalog、文档和测试证据完成绑定后，才构成确切冻结快照；上一份 [r8](review-version-2026-09-25-r8.md) 保持原样。

## 首次审核集合

目前仍没有上一可信版本。专家首次审核对象是 **68 个公共资产（56 个 Operator、12 个 TaskGraph）** 及组合合同，不只是 r8 到 r9 的改动。本轮新增 11 份已有关系的 exact documents 后，开发 catalog 为 `partial: 50/68`（42 个 Operator、8 个 TaskGraph），尚缺 **18** 份。原有 39 份文档的 `implementation_version` 更新是开发包绑定，不表示科学合同变动或专家认可。本轮没有修改科学 callable。

## 本轮科学材料

- [约化 Hall 漂移算子](../../catalog/examples/scirel.closures.reduced-hall-drift.json)与[Hall Picard 图](../../catalog/examples/scirel.equilibrium.reduced-hall-anisotropic-picard.json)：明确局部惯性迭代、mask/轴边界、磁通更新、广义 Ohm/动量诊断及终态检查顺序。图沿用已文档化的磁通导场和 Green 更新；其调用方压力闭合不由 SciRel 自动证明。
- [自由边界各向异性 Picard 图](../../catalog/examples/scirel.equilibrium.free-boundary-anisotropic-picard.json)及三份依赖文档：[环向电流](../../catalog/examples/scirel.equilibrium.anisotropic-toroidal-current.json)、[反馈](../../catalog/examples/scirel.equilibrium.anisotropic-picard-feedback.json)、[残差](../../catalog/examples/scirel.diagnostics.picard-flux-residual.json)。记录 `maxiter=0` 的终态计算、可选墙修正只更新 `psi`、终态闭合/电流重算和与其他 Picard 图不同的松弛合同。
- [直接参数反演图](../../catalog/examples/scirel.inference.direct-anisotropic-inversion.json)及四份依赖文档：[拉丁超立方采样](../../catalog/examples/scirel.inference.latin-hypercube-sampling.json)、[观测残差](../../catalog/examples/scirel.diagnostics.observation-residuals.json)、[单次试探](../../catalog/examples/scirel.inference.anisotropic-trial-evaluation.json)、[参数优化](../../catalog/examples/scirel.inference.anisotropic-parameter-optimization.json)。平衡求解与合成诊断仍是调用方端口；单次试探的异常会形成固定惩罚而非有效平衡。图 YAML 原把实际科学试探算子写成 glue，并把惩罚路径的 `equilibrium` 错写成必有 mapping；本轮按运行实现和既有测试更正静态合同，未改变运行代码。

[平衡领域草稿](../domains/anisotropic-picard-equilibrium.md)和[反演领域草稿](../domains/anisotropic-parameter-inference.md)给专家提供关系入口，不替代逐资产 exact documents。独立审阅发现并已修正反演图 YAML 的空值合同；对六份平衡相关文档未发现具体阻塞。

本轮未消费新合格 L1。第一阶段当前合格 D1 交付根为空；历史 Pleiades 来源映射可供开发比较，不能被解释为本版本已获专家认可。

## 专家待决与发行边界

- 各平衡图的调用方压力闭合、Green/墙响应、网格、单位、反馈和失败语义是否适用于具体物理任务；Hall 局部惯性与终态门槛是否满足目标适用域。
- 反演参数/观测的身份与单位、误差尺度、调用方求解/诊断版本、异常惩罚和收敛接纳规则。合成测试不能证明真实数据的可辨识性或全局最优。
- 尚缺的 18 份 exact documents、kinetic-mirror 等反向依赖、合格 L1 重冻后的来源资格、完整领域专家审核及公共分发许可证。

专家只认可部分内容时，必须在新开发 successor 剔除或返工并重冻，不改写 r9。`scripts/check.ps1 -Mode release` 仍关闭；内部 wheel 只可用于标明未获批准的开发验证。
