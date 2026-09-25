# 轴对称各向异性 Picard 平衡关系族草稿

状态：**开发期关系索引，待领域专家组织和确认**。以下只描述已实现合同与证据边界；不能据此认定来源已重新合格、科学适用性已获专家批准或可公开发行。

## 关系与组合

- [磁通导出极向场](../../catalog/examples/scirel.field.poloidal-field-from-flux.json)把当前 `[Z,R]` 磁通转换为 `B_R`、`B_Z` 和场强，是本图每轮及终态重算的输入。
- [各向异性压强张量力平衡](../../catalog/examples/scirel.equilibrium.anisotropic-force-balance.json)计算柱坐标 `div(P)`、环向电流密度、沿场力和 firehose 裕度。它的 `active_mask` 仅选择平行力误差的统计区域；算子**不**在非活跃单元置零 `J_phi`。
- [轴对称 Picard 单步](../../catalog/examples/scirel.equilibrium.axisymmetric-picard-update.json)把调用方传入的 `J_phi` 乘首个 R/Z 网格间距形成 cell current，经稠密 Green 矩阵形成候选磁通，并对**磁通**做松弛；前一轮电流只影响相对电流变化诊断。其与圆丝/镜像 Green 的制造输入已核对 `psi=R A_phi`、`Wb/rad` 及不乘 `2*pi` 的离源场，但含它的各平衡图和压力闭合还须做反向依赖审核。
- [各向异性 Picard 平衡图](../../catalog/examples/scirel.equilibrium.axisymmetric-anisotropic-picard.json)在每轮调用**调用方拥有**的 `pressure_closure(B,psi)`，规范化压强网格，使用 mask 抑制非活跃电流，再执行 Green 更新。它已在一组制造输入下以 `psi=R A_phi` 接入圆丝真空场和镜像 Green，压力回调必须按 `Wb/rad` 解释 `psi`；这不证明任意回调的物理适用性。达到 `tol` 或 `maxiter` 后，在返回磁通上重新计算场、闭合和力；终态最小场、active-cell firehose、严格平行力相容门槛可能拒绝结果。仅达到迭代上限而未收敛，则返回 `converged=false` 的末态，不自动重试。
- [约化 Hall 漂移闭合](../../catalog/examples/scirel.closures.reduced-hall-drift.json)把各向异性压力力、带电粒子状态与可选局部惯性迭代合成电流、速度、电场和诊断残差。[约化 Hall Picard 图](../../catalog/examples/scirel.equilibrium.reduced-hall-anisotropic-picard.json)复用磁通到场和轴对称 Green 更新，当前 `psi` 端口按 `R A_phi`（`Wb/rad`）解释；一组关闭 Hall 的制造输入已接通圆丝真空场、镜像 Green 和非零电流反馈，默认严格相容门禁未关闭。这不验证非零 Hall 分支或任意压力闭合。该图还有局部惯性、广义 Ohm 与动量相容性门槛；终态并不重复每轮的全部输入检查。它不是上述无 Hall 图的无损替代。
- [自由边界各向异性 Picard 图](../../catalog/examples/scirel.equilibrium.free-boundary-anisotropic-picard.json)组合[环向电流](../../catalog/examples/scirel.equilibrium.anisotropic-toroidal-current.json)、[电流反馈](../../catalog/examples/scirel.equilibrium.anisotropic-picard-feedback.json)、[磁通残差](../../catalog/examples/scirel.diagnostics.picard-flux-residual.json)、场强和可选导体边界修正。反馈叶与无墙图在一个单元电流、离源目标点的制造输入下，分别以 `Wb/rad`、`T`、`T` 对齐圆丝直接 `psi=R A_phi`、`BR`、`BZ`；`g_psi` 和可选墙 Green 均以 `Wb/rad/A` 解释，调用方闭合须按相同 `psi` 坐标定义。一个新增单步案例将真实 [Frank-Egedal 压强闭合](../../catalog/examples/scirel.kinetic.frank-egedal-pressure-closure.json)作为该端口，得到非零电流并在离源点与圆丝三场对照；闭合的轴/边参数使用传入的每弧度磁通坐标，不意味着任意参数或完整迭代平衡已验证。该图使用另一个调用方闭合端口、均匀 R/Z 网格和不同的反馈/终态语义；墙修正只改变磁通，不同步修正返回的 `BR/BZ`，所以墙分支不能宣称三场自洽，也不能与其他 Picard 图按名称合并。
- [表格压强插值](../../catalog/examples/scirel.closures.tabulated-pressure.json)只在调用方给定的一维 `psi` 表或二维 `(B,psi)` 表上插值得到平行/垂直压强；域外默认报错，外推仍须通过有限非负检查。它是压力律候选，不自行解决表的物理来源或跨图磁通单位。
- [Hall 双流体压强状态](../../catalog/examples/scirel.closures.hall-two-fluid-pressure.json)在调用方压力律、密度和电势上作单离子/电子分量组装；显式离子分量不核对其与电子分量是否合计为总压强。它不求 Hall 电流或平衡。
- [动理学镜端 Hall 组合图](../../catalog/examples/scirel.equilibrium.kinetic-mirror-hall-equilibrium.json)把 Hall 迭代中的当前 `B,psi=R A_phi`（`Wb/rad`）原样送入[网格镜端闭合](../../catalog/examples/scirel.kinetic.grid-mirror-kinetic-closure.json)作为压强回调，再返回约化 Hall 图的结果。镜端图把 `psi` 用作调用方剖面插值坐标；固定剖面的 `2*pi` 坐标重标度回归通过，但任意 `psi` 回调必须由调用方按传入坐标重新定义。外层只绑定端口，反馈由 Hall 子图拥有；一组 `0.5 R²` 真空磁通函数和制造径向密度剖面已用两个真实子图完成**合成对角 Green** 反馈和严格相容性检查，但没有真实圆丝/镜像 Green 联算、同输入源码对照或真实装置物理验收。

本图和[历史各向同性压力磁通图](../../catalog/examples/scirel.equilibrium.isotropic-pressure-flux.json)都用 Picard 反馈，但科学输入、压力模型、松弛位置、网格约束、收敛诊断和失败行为不同，不能按“平衡求解器”名称合并。前者的压力闭合是未标准化的调用方端口；把某个已保存动理学闭合接入它，仍要核对场、磁通、剖面、单位和边界，并审查对应嵌套 TaskGraph，不能视为本图已覆盖所有闭合模型。

## 证据与待决

直接测试包含常压零力极限、制造的旋转场和变量压强梯度、cell-area/flux-relax 算术，以及图内动态 mask、终态重算、解析电流和若干失败路径。它们没有证明真实装置的压强闭合或 Green 矩阵适用性，也没有证明所有极端有限输入可产生有限输出。历史 Pleiades 来源映射仍是开发证据；当前合格 L1 交付根为空。

专家待决：各调用方压强闭合的科学身份和可接受域、网格与 Green/墙响应的物理约定、接近零场的 gyrotropic 模型边界、Hall/惯性和 firehose 门槛、相容性容限、未收敛末态的下游资格，以及当前来源与许可证。free-boundary 无墙分支的单位对齐不解决墙修正后 `psi` 与 `BR/BZ` 的不一致；kinetic-mirror 图仍须核对嵌套镜端各 `psi` 剖面的物理定义、非零 Hall 与真实 Green 的共同适用域；两个制造输入都不能自动授权完整磁镜平衡。均匀压强制造输入曾出现绝对力与电场残差约 `1e-12`、相对相容性误差 `0.207/0.090` 的消减敏感性；这一条件下默认严格门槛拒绝结果，不能用单个案例改写普遍容差。
