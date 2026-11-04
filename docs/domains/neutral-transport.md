# 中性粒子输运

状态：开发期叶子关系导航，待领域专家划定完整输运问题；不代表 KN1D 代际迭代、碰撞闭合或完整终端诊断已经整合。

## 开发样例关系

- [中性物种热速度标度](../../catalog/examples/scirel.kinetic.thermal-speed-scale.json)从 eV 温度和以保存氢质量为基准的质量因子计算 m/s 速度；历史参数名 `mass_amu` 不表示标准原子质量单位。
- [自适应中性速度网格](../../catalog/examples/scirel.kinetic.adaptive-neutral-velocity-mesh.json)按调用方温度和请求能量生成对称的归一化 `vr`、`vx` 网格；cap 只筛选归一化温度总体，正请求能量仍插点。重复插点会使保存网格无法进入严格递增的积分权重，SciRel 对此失败关闭。
- [跨网格标量插值](../../catalog/examples/scirel.kinetic.cross-mesh-scalar-interpolation.json)在两个物种的一维空间网格之间线性插值标量剖面；源网格范围外严格置零，命中节点须形成连续索引块。边界警告只报告截断，不改变结果。
- [跨网格分布插值](../../catalog/examples/scirel.kinetic.cross-mesh-distribution-interpolation.json)以圆柱速度单元重叠权重及空间线性插值转移三维分布，可执行有上限的保存矩补偿并作密度重标定。补偿不保证结果非负，下游需核对该前提。
- [中性上风空间推进系数](../../catalog/examples/scirel.kinetic.neutral-upwind-transport-coefficients.json)按空间步长、轴向速度、碰撞频率与源分布构造正向和反向的六个离散推进系数。
- [单代中性分布传播](../../catalog/examples/scirel.kinetic.neutral-generation-propagation.json)接收六个推进系数，分别计算首次入射与散射代际的双向传播；入射边界只用于正向速度，负向速度的右边界固定为零。
- [中性代际停止判据](../../catalog/examples/scirel.kinetic.neutral-generation-stopping.json)以本代与累计密度各自最大值之比判定普通截断或 seed 相对停止；它只返回决定，不推进下一代。
- [中性代际累计状态更新](../../catalog/examples/scirel.kinetic.generation-accumulation-update.json)将单代分布和密度追加到显式状态，保留分布的有符号单元及非负密度；不修改调用方状态。
- [中性外层种子收敛](../../catalog/examples/scirel.kinetic.outer-seed-convergence.json)用前后密度的最大绝对差除以当前最大密度，并以严格大于 `10*truncate` 判定 seed 重入。
- [KN1DPy 顶层外层收敛](../../catalog/examples/scirel.kinetic.kn1d-outer-convergence.json)使用同一比值形式，但顶层重入阈值是 `truncate`，与内层 seed 关系分离。
- [中性 Boltzmann RHS 组装](../../catalog/examples/scirel.kinetic.neutral-boltzmann-rhs.json)把源项、碰撞损失与热速度按保存的有符号关系组装为 RHS；不求解输运方程。
- [弹性频率三通道求和](../../catalog/examples/scirel.kinetic.elastic-frequency-channels.json)按调用方顺序求和三个已归一化频率剖面。
- [中性总损失频率组装](../../catalog/examples/scirel.kinetic.neutral-total-collision-frequency.json)合成基本、弹性、管壁与可选电荷交换损失；零管径单元沿用保存的零壁损失规则。
- [简化电荷交换散射源](../../catalog/examples/scirel.kinetic.simple-charge-exchange-source.json)用上代分布和调用方权重逐空间单元收缩 CX 速率，再缩放目标分布；保留带符号目标和上代输入。
- [弹性重生散射源聚合](../../catalog/examples/scirel.kinetic.elastic-regeneration-aggregation.json)按通道映射顺序累计频率剖面与重生分布乘积，要求各通道共用速度网格。
- [原子双通道散射源归约](../../catalog/examples/scirel.kinetic.atomic-scattered-sources-reduction.json)按 CX、弹性顺序合并两个带符号源场。
- [分子三通道散射源归约](../../catalog/examples/scirel.kinetic.molecular-scattered-sources-reduction.json)按管壁、CX、弹性顺序合并三个带符号源场。
- [原子氢 Alpha 频率收缩](../../catalog/examples/scirel.kinetic.atomic-alpha-contraction.json)将调用方给出的四个 SIG 矩阵与离子种子、分子及原子中性分布按 Fortran 顺序收缩；不在内部组装碰撞矩阵。
- [分子氢 Alpha 频率收缩](../../catalog/examples/scirel.kinetic.molecular-alpha-contraction.json)将三个 SIG 矩阵与 H2+、H、H+ 分布收缩；`ni_correct` 决定 H+ 密度是否按 `max(n-nHP, 0)` 修正。原始来源的 CX reshape 缺陷已在 exact document 中登记。
- [单代中性分布密度归约](../../catalog/examples/scirel.kinetic.generation-density-reduction.json)按调用方提供的柱坐标权重和轴向单元宽度，将 `(nvr, nvx, nx)` 分布归约为 `(nx,)` 密度；它不构造速度网格或求解输运方程。
- [入射中性边界通量归一化](../../catalog/examples/scirel.kinetic.incoming-boundary-flux-normalization.json)按正向轴向速度半空间的预缩放通量，将调用方的边界形状缩放到目标通量的绝对值；目标为零时返回零尺度与零边界。
- [空间源形状归一化](../../catalog/examples/scirel.kinetic.spatial-source-shape-normalization.json)用调用方空间坐标的梯形积分将非负源剖面归一化，并返回原始积分。
- [圆柱速度空间积分权重](../../catalog/examples/scirel.kinetic.cylindrical-velocity-quadrature.json)从归一化 `vr`、`vx` 网格构造 ghost 面、环形径向测度、体积权重和差分系数；`volume` 可作为 Maxwellian 速率平均的 `cylindrical_volume` 输入。
- [平移 Maxwellian 离散种子](../../catalog/examples/scirel.kinetic.shifted-maxwellian-seed.json)在调用方速度网格和体积权重上构造逐 shift 归一化指数初值，保留来源的严格内部 `-80` clamp；输出尚未经过离散矩补偿。
- [轴对称中性分布矩归约](../../catalog/examples/scirel.kinetic.axisymmetric-neutral-moments.json)在调用方分布与圆柱积分权重上归约密度、轴向流、压力、温度、应力和随机热通量；`sigma_zz = sigma_yy` 与零密度切片的 `source_default` 值沿用保存实现，仍待专家确认。
- [终态分子轴向通量与流速](../../catalog/examples/scirel.kinetic.terminal-flux-velocity-reduction.json)在显式热速度和非负柱坐标权重上归约两项剖面；与九矩关系的正权重域重叠，但允许零权重单元且不计算高阶矩。
- [终态分子压力与温度](../../catalog/examples/scirel.kinetic.terminal-pressure-temperature-reduction.json)按显式质量比、热速度和柱坐标权重归约中心二阶矩；正权重域与九矩关系重叠，允许部分零权重且不计算应力或热通量。
- [终态分子随机与总热通量](../../catalog/examples/scirel.kinetic.terminal-heat-flux-reduction.json)按显式质量比和热速度计算中心随机通量与总能量通量；随机项在正权重域与九矩关系重叠，总量为本变体新增字段。
- [终态分子能量转移率](../../catalog/examples/scirel.kinetic.terminal-energy-transfer-reduction.json)由调用方给出的带符号 Boltzmann RHS、终态分布和外部源归约 loss、热、动量与总能量转移；不在内部组装 RHS 或闭合守恒诊断。
- [终态分子离子密度与温度](../../catalog/examples/scirel.kinetic.terminal-ion-state-reduction.json)按显式密度、离子温度和 11 通道反应表计算 H2+ 密度、温度及两项频率；输出可由调用方衔接分子 Alpha 收缩，速率表单位仍待专家核对。
- [终态分子总能量守恒诊断](../../catalog/examples/scirel.kinetic.terminal-conservation-diagnostic.json)对调用方给出的总热通量轴向差分和总能量转移率相邻均值计算全局归一化误差；最后节点约定为零，不验证上游物理归一化。

跨网格分布插值复用圆柱速度空间积分权重。其余二十九项没有直接 callable 依赖；单代传播由调用方传入上风推进系数，停止判据由调用方传入累计密度，Boltzmann RHS 接收各上游源项，这些函数不在内部调用其他资产。Alpha 收缩接收调用方矩阵，未绑定矩阵来源或完整碰撞图。累计更新只处理一次显式状态转移；重入决定未绑定反馈顺序或迭代上限，不能被解释为完整 TaskGraph。边界归一化接收调用方提供的热速度和柱坐标权重。自适应网格、积分权重、种子与矩归约的端口组合由直接测试覆盖。链接指向 `catalog/examples/` 开发 pilot 的 exact documents，不代表专家批准或公开发布。

## 证据与待整理项

有效实数输入上的有限保存点与摘要锁定的 KN1DPy 归档实现精确相等；SciRel 对非实数输入、热速度派生质量下溢、密度溢出、累计状态不一致以及非有限输入和输出采用已声明的失败合同。来源项目的 whole-source D1 资格已撤回，有限点比较不能替代重新冻结、科学审核或许可证决定。其余中性输运算子、组合顺序、反馈状态和停止上限仍待逐项核对。
