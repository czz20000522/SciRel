# 加热、电流与诊断

## 物理功能

把当前等离子体状态和外部驱动转换为模型的温度源、电流组成以及综合诊断量。
输出服务于所选约化模型；其中的代理、默认闭合和失败后备不代表实验标定结果。

## 加热与温度源

`total_heating_sources(rho, state, machine, actuator, sim, eq=None, dV_drho=None)` 返回 `(Se, Si, diag)`。
`Se/Si` 是电子和离子**温度源**，单位 keV/s；它们不是以 MW 表示的总功率。
所选配置中的辅助加热、欧姆加热、电子—离子交换、D–T alpha 加热和辐射损失参与来源组合。
输入功率、局部温度源与体积积分后的功率必须区分。

```python
from scirel.fusion.diagnostics import total_heating_sources
# state、rho 和所选模型配置由前面的初始化/几何步骤提供
Se, Si, source_diagnostics = total_heating_sources(
    rho, state, machine, actuator, sim
)
```

这是调用结构说明，所选完整源项模型未因这段代码获得独立科学资格。

## 电流组成

`current_components_from_state(rho, state, machine, actuator, sim, eq=None, q=None)` 返回
`(j_ind_or_ohm, j_bs, j_cd, j_total)`：感应/欧姆、自举、外部驱动和总电流密度分量。
入口保留来源的离散和通量约定；同名电流密度剖面不能直接当作装置总电流 `MachineConfig.Ip`。
本版尚未为此入口形成独立完整端口合同，不在本页猜补所有返回场的单位、符号和轴序。

## 综合诊断

`compute_diagnostics(state, machine, actuator=None, sim=None, include_equilibrium=True, *, rho=None, eq=None, current_components=None, heat_diag=None)`
返回来源诊断字典。可传入已计算的网格、几何、电流和热源结果，避免同一诊断重复求算。
未提供配置时使用来源默认配置；它可能重新计算几何和闭合，不能理解为只读取一个现成状态。

```python
from scirel.fusion.diagnostics import compute_diagnostics
diagnostics = compute_diagnostics(state, machine, actuator, sim)
```

部分来源诊断路径具有后备值，例如捕获回路电压计算异常后返回零。
“字典中有值”不能证明每个物理子过程均成功，必须结合所选模型、来源失败语义和实际任务记录解释。

上述三个入口都已列入本版公共调用参考，但详细科学资格仍受限。
相关功能：[状态演化](state-and-evolution.md)、[平衡与输运](equilibrium-and-transport.md)。
