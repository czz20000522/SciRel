# Frank-Egedal 压强闭合领域草稿

状态：**开发期领域索引草稿，待领域专家组织和确认**。本页只描述现有 SciRel callable 与直接测试支撑的关系；各端口、默认值和失败行为以 exact document 为准。

## 关系与组合

- [磁通径向包络](../../catalog/examples/scirel.kinetic.frank-egedal-radial-envelope.json)把二维 `psi` 相对轴值和边值归一化、截断到 `[0,1]`，返回 `(1-psi_normalized)^alpha`。它允许反向磁通区间；不重建磁面或判定轴/边界的物理位置。
- [损失锥分数阶 Legendre 谱](../../catalog/examples/scirel.kinetic.loss-cone-spectrum.json)在指定角向边界的有限数值扫描中给出模态 degree；[源模态投影](../../catalog/examples/scirel.kinetic.frank-egedal-source-projection.json)可使用调用方 degree，或按镜比求边界并调用谱算子，随后使用调用方幅度或有限求积得到 NBI 源系数。谱根的完整性与源模型适用性没有被证明。
- [热离子速度与俯仰矩](../../catalog/examples/scirel.kinetic.frank-egedal-hot-ion-moments.json)对二维磁场逐点作有限阶求积，计算平行、垂直和密度形状；平行/垂直压强形状以 `b=1` 的平行矩归一化，密度形状以 `b=1` 的密度矩归一化。返回的是无量纲形状，不是绝对压强或自洽粒子分布。
- [压强状态组装](../../catalog/examples/scirel.kinetic.frank-egedal-pressure-state.json)把径向包络、热离子形状与调用方的热压强、气体动力学和电子尺度组合成 `p_parallel`、`p_perp`；密度和电子温度在缺少相应尺度时可为 `None`。电子温度输入是能量 J，不是未换算的 K。
- [Frank-Egedal 压强闭合 TaskGraph](../../catalog/examples/scirel.kinetic.frank-egedal-pressure-closure.json)按径向包络、模态选择/投影、热离子矩和压强组装顺序连接上述关系，并返回中间 `closure_state`。这是一次有向组合，没有 Picard 或其他迭代反馈，也不求完整磁平衡。

## 接线与证据边界

图只接收调用方给定的二维 `[Z,R]` `psi`、同网格 `B` 和参数映射；它不从磁通计算磁场，也不检验输入是否属于同一个科学模型。旧图 YAML 曾把 `turning_b` 写为覆盖 `mirror_ratio`，与源模态和热矩实现不符；维护合同现已按现实现修正为两者同时存在时优先取 `mirror_ratio`，并用直接回归固定，历史描述差异仍可在 Git 中核对。`psi` 的历史单位标签为 `Wb`，不能未经核对就接到目前真空场链的 `Wb/rad` 约定。

直接测试覆盖选定径向截断、显式/自动 degree 分支、单个独立投影积分、`b=1` 的热矩归一化、可空输出、镜比参数优先级和部分错误输入。它们不证明任意镜比下谱的完整性、默认截断和求积误差、跨模型物理正确性或完整平衡可用性。保存的 Pleiades 候选只是历史开发来源；当前合格 D1 交付根仍为空，本版本没有领域专家认可。专家待决：参数优先级是否符合期望物理输入习惯、谱/求积适用域、`psi` 约定、压力/密度尺度来源、NBI 与气体/电子项模型边界，以及来源许可证。
