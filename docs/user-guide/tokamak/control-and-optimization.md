# 时变驱动与优化

## 物理问题与计算层次

怎样表达电流、磁场、几何或辅助加热随时间的变化？怎样基于一个选定模型比较或优化驱动？
驱动输入、模型目标与求梯度/优化的数值算法处在不同层次：优化器可执行不代表物理目标已经得到验证。

## 时间波形

`Waveform(times, values, hold_left=True, hold_right=True, interpolation='linear')` 表示一项控制量随时间的输入。
`ScenarioWaveform(controls, name='custom')` 将多项具名控制组合在一起。
`apply_waveform_controls(machine, actuator, waveform, t)` 返回时刻 `t` 采样后的装置与驱动配置。

`times/t` 按物理时间 s 使用；`values` 的单位取决于控制名：
`Ip_MA` 为 MA、`Bt` 为 T、`R0/a` 为 m、`P_aux_MW` 为 MW，形状与组分控制使用其来源约定。
采样 `Ip_MA` 后写入 `MachineConfig.Ip` 时乘以 `1e6`。缺少某控制项时保留原配置值。

可选 `linear` 和 `step` 插值，默认两端保持。浮点构造与插值沿来源行为保留；
十进制时刻不一定是二进制数组中的精确中点。本版已有十进制中点严格误差检查失败记录，不能把理想插值值写成保证精确的结果。

以下仅为调用结构示例，不作为新增参考计算结果：

```python
import jax.numpy as jnp
from scirel.fusion.controls import Waveform, ScenarioWaveform, apply_waveform_controls

power = Waveform(times=jnp.asarray([0.0, 1.0]), values=jnp.asarray([0.0, 20.0]))
scenario = ScenarioWaveform(controls={"P_aux_MW": power})
machine_t, actuator_t = apply_waveform_controls(machine, actuator, scenario, t=0.5)
```

## 静态控制与自动微分

`apply_control_vector` 面向来源 pytree 配置应用物理控制向量，要求对应 pytree 类型与控制顺序。
本版公共模块没有同时导出全部 pytree 构造器；普通 `MachineConfig` 不可仅凭相似字段假定可代替其输入。
它属于高级兼容入口，完整公共构造与生命周期说明仍不足。

`autodiff_value_and_grad_pytree` 对选定约化目标计算值、指标和梯度。
`optimize_controls_optax` 使用 Optax 迭代物理控制，默认梯度路径为自动微分；有限差分是保留的调试对照路径。
参数包含边界、约束权重、迭代上限、学习率与可选梯度/更新范数上限，签名见 [调用参考](../api-reference.md)。

## 波形优化

`waveform_objective_from_z` 使用形状 `[控制项数, 控制点数]` 的无约束参数与边界映射形成物理波形目标，
可包含功率积分、光滑度和变化率惩罚。
`optimize_waveform_optax` 执行有界控制点优化，保留固定端点与有限迭代约定。

这四个优化入口在当前版本属于兼容接口，未形成完整独立科学资格。
实际使用必须同时明确目标函数、模型适用条件、初态、控制量单位、约束与停止条件；
不能只看到梯度有限或目标变化就断言物理控制策略成立。

相关功能：[状态演化](state-and-evolution.md)、[加热和诊断](heating-current-diagnostics.md)。
