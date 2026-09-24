# SciRel 首次整版待审 successor r8

状态：**开发期冻结待审材料，不是专家科学认可或公开发行**。上一份 [r7](review-version-2026-09-25-r7.md) 的确切版本和冻结证据保持原样；本轮快照另以 review manifest 绑定代码树、wheel、catalog、文档和测试。

## 首次审核集合

目前仍没有上一可信版本。专家首次审核对象是 **68 个公共资产（56 个 Operator、12 个 TaskGraph）** 及组合合同，不只是 r7 到 r8 的差异。开发 catalog 新增三份文档后为 `partial: 39/68`（34 个 Operator、5 个 TaskGraph），尚缺 **29** 份 exact documents。原有 36 份文档随开发包做 `implementation_version` 机械更新，不表示科学合同更改或专家认可。

本轮为三项**已有**关系补 exact documents，未新增或修改科学 callable：

- [各向异性压强张量力平衡](../../catalog/examples/scirel.equilibrium.anisotropic-force-balance.json)：记录柱坐标 `div(P)`、`J_phi`、平行力和 firehose 裕度。其 `active_mask` 仅选择误差统计区域；把非活跃电流置零是图层显式操作，而非本算子隐含功能。
- [轴对称 Picard Green 更新](../../catalog/examples/scirel.equilibrium.axisymmetric-picard-update.json)：记录 cell current 的首间距面积约定、密集 Green 行列顺序和磁通松弛。前一轮 cell current 只用于变化诊断；不能与已有各向同性图的电流松弛混同。
- [各向异性 Picard 平衡图](../../catalog/examples/scirel.equilibrium.axisymmetric-anisotropic-picard.json)：依赖上述两算子及已文档化的磁通到极向场关系，保留调用方提供的 `pressure_closure(B,psi)`。每轮在闭合前检查最小场；**终态会先调用闭合并计算力，再检查最小场**。firehose/平行力门槛在终态执行，达到迭代上限但未收敛时返回最后状态。

[领域草稿](../domains/anisotropic-picard-equilibrium.md)列出适用条件和专家待决问题。`axisymmetric_picard_update` 也被当前 reduced-Hall 图使用；该图尚缺 exact document，本轮不宣称反向图审核闭合。独立审阅指出图文档最初把终态磁场检查写成回调前执行；已按源码修正，保留这一顺序作为专家可见合同。

本轮没有消费新合格 L1。第一阶段当前合格 D1 交付根为空；Pleiades 保存记录仅是历史开发来源映射，旧 `review_pending`/`admitted` 标签不授权本版本。

## 专家待决与发行边界

- 调用方压强闭合的科学身份和适用域、非均匀网格的首间距面积规则、接近零场的 gyrotropic 假设、终态低场时已调用闭合的副作用/失败顺序，以及 firehose 与平行力容限。
- 未收敛末态能否被后续图消费；reduced-Hall 及其他反向依赖需逐项核对版本、单位、反馈和失败语义。
- 其余 29 份 exact documents、合格 L1 重冻后的来源资格、完整领域专家审核与公共分发许可证。

专家只认可部分内容时，必须在新开发 successor 剔除或返工并重冻，不改写 r8。`scripts/check.ps1 -Mode release` 仍关闭；开发 wheel 可用于内部验证，不能自行晋级可信或公开发行。
