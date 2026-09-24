# 各向同性压力平衡与点诊断关系族草稿

状态：**开发期关系索引，待领域专家组织和确认**。本页不批准科学模型或来源资格；精确端口、数值约定、失败语义和测试上限以链接的 exact documents 为准。

## 能力边界

- [压力磁通状态](../../catalog/examples/scirel.equilibrium.pressure-flux-state.json)从调用方给定的中平面径向压力和当前磁通构造 `P(psi)` 样条、导数和边界磁通。它要求一整行精确 `Z=0`、首个精确零压力边界，以及足够的严格递增磁通前缀；这不是任意剖面拟合器。
- [各向同性 Picard 单步](../../catalog/examples/scirel.equilibrium.isotropic-picard-step.json)从当前压力导数、旧电流和稠密 Green 矩阵计算下一磁通与残差。它不自行构造压力状态，也不决定迭代停止。
- [有界压力磁通平衡图](../../catalog/examples/scirel.equilibrium.isotropic-pressure-flux.json)组合上述两算子，逐轮重建压力状态并回传磁通与电流；`maxiter` 是有限上限，不收敛返回末态和明确失败标记。`maxiter=0` 仍建立初始压力表示，不执行单步。它只覆盖历史各向同性模型，不得推断各向异性闭合已被支持。
- [平衡合成点诊断图](../../catalog/examples/scirel.diagnostics.equilibrium-synthesis-diagnostics.json)使用已文档化的[双线性 R-Z 采样](../../catalog/examples/scirel.geometry.bilinear-grid-sampling.json)，从调用方**已经提供**的平衡状态抽取磁通环式及 Thomson 式局域预测。它不求平衡，也不直接依赖上述 Picard 图；没有请求的输出键缺席，不产生仪器响应、噪声或谱线。

平衡图输出不能仅凭字段名接到诊断图：后者要求调用方明确提供同一 `[Z,R]` 网格上的 `equilibrium.psi`，若请求 Thomson 分支，还需要 `p_parallel`、`p_perp` 以及可选剖面。压力磁通图只返回 `pressure_of_psi` 表示，**不**返回诊断图所需的二维压强场。跨图桥接若涉及新剖面求值、物理闭合或单位变换，须作为有证据的关系另行实现和审核，不能藏在 glue 中。

## 证据与待决

现有直接测试覆盖小网格零/非零 Green 反馈、掩码、电流与迭代上限，以及诊断条件分支、双线性值、越界拒绝和只读输入。它们证明已测合同，不证明给定压力函数、Green 矩阵或输入平衡在真实装置上物理适用。现有 Pleiades 映射是历史开发来源；当前合格 L1 交付根为空，不能据此声称新生命周期的来源冻结或专家批准。

专家待决：各向同性压力模型的目标适用域和边界样本约定、Green 矩阵物理归一化、压力函数的可靠来源、非收敛末态能否供后续诊断、诊断字段的实际单位与仪器意义、跨图剖面关系、来源许可证。未经确认，两个 TaskGraph 保持独立科学身份。
