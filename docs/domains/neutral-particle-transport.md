# 中性粒子输运关系族草稿

状态:**开发期关系索引,待领域专家组织和确认**。本页只连接已有科学合同;精确端口、单位、失败行为与证据上限以链接的 exact document 为准,不构成认可或发布。合格 L1 交付根为空,KN1DPy 历史保存包只支持 provisional 有界开发比较。

## 能力与区别

以下资产覆盖 KN1DPy 谱系的中性粒子速度空间输运链:截面数据 → 碰撞矩阵装配 → Alpha 收缩 → Omega 弹性频率聚合 → 网格输运与代际推进。同页资产间存在真实的集成依赖(以 exact document 的 `version.dependencies` 声明为准),但页面不把集成链当作已验证的端到端科学求解器。

### 碰撞数据与几何

- [热速度标度](../../catalog/examples/scirel.kinetic.thermal-speed-scale.json):从 eV 温度与 amu 质量计算二阶矩热速度,是本族多数算子 `Vth` 归一化的共同上游约定(Tnorm 以 eV 声明)。
- [圆柱速度空间积分权重](../../catalog/examples/scirel.kinetic.cylindrical-velocity-quadrature.json):构造 `Vr2pidVr`/`dVx` 有限体积权重,供装配与聚合的求和;轴序与单位以该文档为准。

### 碰撞矩阵装配(输入载子 → (N,N) 矩阵)

- [原子四族碰撞矩阵装配](../../catalog/examples/scirel.kinetic.atomic-collision-matrix-assembly.json)与[分子四族碰撞矩阵装配](../../catalog/examples/scirel.kinetic.molecular-collision-matrix-assembly.json):从显式速度载子与热归一化装配原子 `SIG_CX/SIG_H_H/SIG_H_H2/SIG_H_P` 与分子 `SIG_CX/SIG_H2_H/SIG_H2_P/SIG_H2_H2`。两者的截面拟合经已集成的 `scirel.collisions` 截面叶求值(而非内嵌第二份公式):弹性六族与源内嵌拟合逐位一致,CX 两族存在已采样的 ~2.2e-15 相对差(标准化 `np.exp` vs 源 `np.e **`,rtol=1e-14 复放预算)。分子 `SIG_CX` 能量因子(无 0.5、无 `mu`)是源逐字保留的判别差异。弹性族的有界负元由带符号因子内在产生,如实复现、不 clamp;物理可接受性是开放专家问题。

### Alpha 收缩(矩阵 → 频率场)

- [原子 Alpha 收缩](../../catalog/examples/scirel.kinetic.atomic-alpha-contraction.json)与[分子 Alpha 收缩](../../catalog/examples/scirel.kinetic.molecular-alpha-contraction.json):把装配好的 SIG 矩阵与前驱分布按 legacy Fortran-order 载子收缩为 `(nvr,nvx,nx)` Alpha 频率场。分子臂登记源缺陷修复(`kinetic_h2.py:1204` 缺失的 Fortran-order 恢复 reshape);负密度运行时不拒绝;`ni_correct` 分支是源定义密度修正而非正密度门禁。

### Omega 弹性频率聚合(频率场 → 逐单元标量)

- [原子 Omega 聚合](../../catalog/examples/scirel.kinetic.atomic-omega-aggregation.json)与[分子 Omega 聚合](../../catalog/examples/scirel.kinetic.molecular-omega-aggregation.json):把弹性 Alpha 频率与分支时刻 SIG 再收缩聚合为逐单元 `Omega_*` 与总弹性频率;输出经源语义零钳制恒非负。两臂 Wperp 分支选择不对称(原子 `<=0` vs 分子 `<0`)、分子 H2-P/H2-H 除法在求和外/内,均为逐字保留的源语义。登记的 fail-closed 加固(正密度门控、有限正标量 `Vth`/容差、非有限输出拒绝)与保存臂的静默跳过/NaN 行为有意分歧;legacy `sign(0)=0` 在对称漂移差下的退化现在是合法输入被拒绝而非静默 NaN。

### 网格、输运与代际推进

- [自适应中性速度网格](../../catalog/examples/scirel.kinetic.adaptive-neutral-velocity-mesh.json)、[跨网格标量插值](../../catalog/examples/scirel.kinetic.cross-mesh-scalar-interpolation.json)与[跨网格分布插值](../../catalog/examples/scirel.kinetic.cross-mesh-distribution-interpolation.json):网格重构与跨网格映射。
- [中性上风空间推进系数](../../catalog/examples/scirel.kinetic.neutral-upwind-transport-coefficients.json)、[中性 Boltzmann RHS 组装](../../catalog/examples/scirel.kinetic.neutral-boltzmann-rhs.json)、[中性代际空间传播](../../catalog/examples/scirel.kinetic.neutral-generation-propagation.json)、[中性代际停止](../../catalog/examples/scirel.kinetic.neutral-generation-stopping.json)与[代际累计更新](../../catalog/examples/scirel.kinetic.generation-accumulation-update.json):代际推进链的组成部分;各自合同独立,页面不断言其组成即完整求解器。
- [中性总损失碰撞频率组装](../../catalog/examples/scirel.kinetic.neutral-total-collision-frequency.json)、[弹性频率通道求和](../../catalog/examples/scirel.kinetic.elastic-frequency-channels.json)、[弹性重生散射源聚合](../../catalog/examples/scirel.kinetic.elastic-regeneration-aggregation.json)、[原子/分子散射源归约](../../catalog/examples/scirel.kinetic.atomic-scattered-sources-reduction.json)与[分子散射源归约](../../catalog/examples/scirel.kinetic.molecular-scattered-sources-reduction.json):源项与通道聚合;其声明的 "species-pair Omega evaluations" 上游由上节 Omega 聚合资产补齐,组合到具体源序列仍属调用方责任。
- [平移 Maxwellian 种子](../../catalog/examples/scirel.kinetic.shifted-maxwellian-seed.json)与[轴对称中性矩归约](../../catalog/examples/scirel.kinetic.axisymmetric-neutral-moments.json):初值构造与矩诊断。

## 适用条件与待决

- **单位与归一化**:速度轴为 `v/vth`,`Tnorm` 以 eV 声明;SIG 矩阵与 Alpha/Omega 的"频率"输出受调用方装配测度约束,不是绝对 SI 频率。跨资产组合必须共享同一载子几何与权重;本页不隐含任何默认网格。
- **负元与钳制语义不一致是合同差异而非矛盾**:SIG/Alpha 族的有界负元如实复现不 clamp,Omega 族按源语义零钳制恒非负;不得从一方推断另一方。
- **Provenance 上限**:本页全部动理学资产源自 KN1DPy 保存包(严格 D1 资格已撤回,provisional);复放是历史开发证据,不是合格 L1 provenance。截面拟合经公共 `scirel.collisions` 叶复用,CX 族带已采样 ~2.2e-15 相对差与 rtol=1e-14 复放预算——采样证据不是连续全域上界。
- **登记的源文档冲突**:保存分子装配 operator.md 的 canonical 负元计数(2/2/4)与可复现计算(4/4/8)冲突,原因待专家审查。
- **fail-closed 加固清单**(对保存臂静默行为的有意分歧,均已在 exact documents 登记):正密度门控、标量 `Vth`/容差校验、非有限输出终检、密度为正的 Omega 调用前提。
- **专家待决**:负元/负密度的物理可接受性;legacy `sign` 是否归一化为带零值保护形态;`DeltaVx_tol`/`Wpp_tol` 钳制值与分子 `SIG_CX` 能量因子的物理合理性;原子臂 Wperp 累计矩分支(源 `#NOTE Not Tested Yet` 区域)的物理验证;CX 逐位复放的回退条件(重内嵌源拟合)。这些决定留给专家;无证据时维持分立合同,不在共享实现中擅自统一。
