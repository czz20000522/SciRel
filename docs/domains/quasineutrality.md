# 准中性电子闭包

状态：开发期能力导航，尚未获得领域专家认可；本页不代替逐项科学合同。

## 关系与输入

- [准中性参考电子密度](../../catalog/examples/scirel.closures.quasineutral-reference-density.json)将单一正离子参考数密度乘以正电荷态倍率，返回参考电子数密度。零密度可用；有限输入的乘积溢出会失败。
- [玻尔兹曼电子态与准中性残差](../../catalog/examples/scirel.closures.boltzmann-quasineutrality.json)在调用方提供的电势、电子热能、参考态与离子密度上评价电子密度、压力及三类残差。指数剪裁与零密度 `tiny` 地板是数值合同的一部分；极端有限输入的派生输出未做有限性复查。
- [准中性电势二分求根](../../catalog/examples/scirel.closures.quasineutral-potential.json)对调用方残差回调进行有界扩括区与二分；活跃表面同时满足括区宽度和残差容差才返回，非活跃表面保留参考电势但仍返回其残差。

三项关系都使用 NumPy 广播。广播只证明数组 shape 相容；坐标、物理状态与单一离子假设仍由调用方负责。残差中的 `charge_residual_m3` 是电荷态加权的**数密度**差，单位为 `m^-3`，不是 `C/m^3`。

## 组合与证据

镜面准中性 TaskGraph 还消费[双温镜约束速度矩](../../catalog/examples/scirel.kinetic.mirror-constrained-moments.json)和[双温镜总压强状态组装](../../catalog/examples/scirel.kinetic.mirror-total-pressure.json)。前者从调用方剖面计算离子密度与各向异性压强，可选择双端塞损失锥求积；后者只检查压强字段，离子/电子密度和残差原样透传。五个叶子均有独立 exact document，但图的状态、反馈、停止与失败传播仍需独立核对。现有直接测试与图测试证明选定输入上的可执行关系，不构成完整物理闭包校验或专家批准。相对上一可信版的变化待建立可信版后填写。
