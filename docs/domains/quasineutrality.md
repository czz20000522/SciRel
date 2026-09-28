# 准中性电子闭包

状态：开发期能力导航，尚未获得领域专家认可；本页不代替逐项科学合同。

## 关系与输入

- [准中性参考电子密度](../../catalog/examples/scirel.closures.quasineutral-reference-density.json)将单一正离子参考数密度乘以正电荷态倍率，返回参考电子数密度。零密度可用；有限输入的乘积溢出会失败。
- [玻尔兹曼电子态与准中性残差](../../catalog/examples/scirel.closures.boltzmann-quasineutrality.json)在调用方提供的电势、电子热能、参考态与离子密度上评价电子密度、压力及三类残差。指数剪裁与零密度 `tiny` 地板是数值合同的一部分；极端有限输入的派生输出未做有限性复查。
- [准中性电势二分求根](../../catalog/examples/scirel.closures.quasineutral-potential.json)对调用方残差回调进行有界扩括区与二分；活跃表面同时满足括区宽度和残差容差才返回，非活跃表面保留参考电势但仍返回其残差。
- [镜端双极损失电势闭合](../../catalog/examples/scirel.closures.mirror-ambipolar-potential.json)在指定端势上评价单离子/电子单向端损失通量，或逐磁通面有界求解电荷态加权通量平衡；评价模式的 `converged` 不代表电流平衡。

前三项准中性关系都使用 NumPy 广播。广播只证明数组 shape 相容；坐标、物理状态与单一离子假设仍由调用方负责。残差中的 `charge_residual_m3` 是电荷态加权的**数密度**差，单位为 `m^-3`，不是 `C/m^3`。

## 组合与证据

镜面准中性 TaskGraph 还消费[双温镜约束速度矩](../../catalog/examples/scirel.kinetic.mirror-constrained-moments.json)和[双温镜总压强状态组装](../../catalog/examples/scirel.kinetic.mirror-total-pressure.json)。前者从调用方剖面计算离子密度与各向异性压强，可选择双端塞损失锥求积；后者只检查压强字段，离子/电子密度和残差原样透传。[镜面准中性图](../../catalog/examples/scirel.closures.mirror-quasineutral-closure.json)显式声明五个叶子、局部电势反馈与有界停止条件，求解失败不返回终态。现有直接测试与图测试证明选定输入上的可执行关系，不构成完整物理闭包校验或专家批准。相对上一可信版的变化待建立可信版后填写。

[网格镜端动理学闭合](../../catalog/examples/scirel.kinetic.grid-mirror-kinetic-closure.json)在调用方的 R-Z 网格上选择参考与端塞行，通过磁通剖面插值映射端态，再调用镜面准中性图。端塞电势可规定或分别求解；默认只屏蔽端塞外的指定顶层密度、压强和电荷残差字段，原始矩与端态诊断保留全网格。磁通坐标须由调用方统一约定。

[约化 Hall 漂移闭合](../../catalog/examples/scirel.closures.reduced-hall-drift.json)在给定极向场、各向异性压强、电子态和等离子体掩码上评价环向电流、物种漂移及局部惯性修正。其速度和广义 Ohm 诊断使用更严格的活跃掩码；返回值不证明整体平衡或低密度区域的模型适用性。

[Hall 双流体压强状态](../../catalog/examples/scirel.closures.hall-two-fluid-pressure.json)把调用方的总压强律、密度、电子压强与电势广播为组分状态；默认离子压强为总量减电子分量，显式覆盖值不校验求和一致性。

[约化 Hall 各向异性 Picard 图](../../catalog/examples/scirel.equilibrium.reduced-hall-anisotropic-picard.json)在调用方提供的压强闭合与 Green 响应上反馈磁通，逐轮调用极向场、Hall 漂移和磁通更新三个叶子，达到容差或迭代上限后复算终态。外层未收敛可返回带 `converged=false` 的终态；内层惯性未收敛会抛错。真空场文档的 `Wb` 与本图要求的 `Wb/rad` 接线仍待科学裁决。

[动理学镜端 Hall 平衡组合](../../catalog/examples/scirel.equilibrium.kinetic-mirror-hall-equilibrium.json)把当前 Hall 图的磁场与磁通传给网格镜端动理学闭合，并把其返回状态作为每轮压强闭合。外层只绑定两个子图，磁通反馈仍由 Hall 子图控制；调用方必须保证动理学剖面、离子参数和 `psi=R A_phi` 坐标约定一致，组合器不会自动换算。
