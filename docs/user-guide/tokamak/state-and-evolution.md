# 状态初始化与时间演化

## 物理功能

用给定装置、驱动与模型配置建立温度、密度和电流相关初态，并在调用者持有的前驱状态上推进时间。
初态构造与求得自洽的平衡/输运解是不同事情：此版本的初始化包含剖面形状和约化重建启发式。

## 配置与常用单位

`MachineConfig` 表示装置、形状和组分，`ActuatorConfig` 表示外部驱动和边缘值，
`SimulationConfig` 表示网格、时间步长与模型选择。它们位于 `scirel.fusion.configuration`。

| 参数 | 含义 | 默认值与单位 |
| --- | --- | --- |
| `MachineConfig.R0` / `.a` | 大半径 / 小半径 | `6.2` / `2.0` m |
| `.Bt` / `.Ip` | 轴上真空环向场 / 指定总等离子体电流 | `5.3` T / `15e6` A |
| `.kappa` / `.delta` / `.Zeff` | 伸长率 / 三角形变 / 有效电荷 | `1.7` / `0.5` / `1.8`，无量纲 |
| `ActuatorConfig.P_aux_MW` | 辅助加热功率 | `50.0` MW |
| `.edge_Te_keV` / `.edge_Ti_keV` | 边缘电子 / 离子温度 | 各 `0.25` keV |
| `SimulationConfig.nr` / `.ntheta` | 径向 / 极向离散数量 | 显式选择所需分辨率 |
| `.dt` | 配置时间步长 | s；约化自适应步的实际时间可能更小 |

注意类构造器的 `Ip` 单位为 A；输入 JSON 或驱动波形中的 `Ip_MA` 使用 MA，加载/采样路径会换算，不能互换参数名后保持相同数值。

## 完整状态

`PlasmaState` 有七个字段，后继调用必须保留完整状态：

| 字段 | 含义 | 单位与选定形状 |
| --- | --- | --- |
| `Te`, `Ti` | 电子、离子温度 | keV，`[nr]` |
| `ne20` | 电子密度，以 `1e20 m^-3` 为单位 | `[nr]`；例如 `1.0` 表示 `1e20 m^-3` |
| `psi_ind` | 来源电流演化使用的极向磁通代理 | 默认 face 约定为 `[nr+1]`；保留来源通量约定 |
| `psi_edge` | 边缘/变压器通量边界状态 | 标量，来源通量约定 |
| `Phi_b_prev` | 上一步约化环向磁通 | Wb，标量 |
| `dV_drho_prev` | 上一步体积几何历史 | m³，`[nr]` |

不要仅取 `Te/Ti/ne20` 后造一个缺少几何历史的状态，也不要用捕获的答案代替真实前驱。

## 径向初态与单步推进

`initial_state(machine, actuator, sim)` 构造新的完整初态。`step(state, machine, actuator, sim)` 是兼容单步入口。
`initialize_step_cache` / `step_cached` 对昂贵子模型保留缓存与更新顺序，缓存属于相应状态和配置的生命周期。
缓存入口的完整科学与生命周期合同尚未形成独立详细资产文档，不能由函数存在推断任意缓存复用安全。

下列初始化例子来自该版已绑定合同，复用已有有限安装证据；它检查形状，不宣称自洽解已收敛：

```python
from dataclasses import replace
from scirel.fusion.configuration import MachineConfig, ActuatorConfig, SimulationConfig
from scirel.fusion.dynamics import initial_state

machine, actuator = MachineConfig(), ActuatorConfig()
sim = replace(SimulationConfig(), nr=4, ntheta=4, n_steps=1,
              transport_model="bohm_gyrobohm", pedestal_model="none",
              equilibrium_model="reduced_fixed_boundary")
state = initial_state(machine, actuator, sim)
assert state.Te.shape == (4,) and state.psi_ind.shape == (5,)
```

数值例子先按 [安装说明](../version-and-installation.md) 启用 JAX 64 位。

## 约化储能演化

`initial_state_0d` 与 `zero_d_step_with_dt` 以约化储能更新配合径向剖面重建。
它们仍返回径向状态，不能把“0D”理解为无须剖面和历史字段。

所保留的一步关系为冻结功率下的 `dW/dt = P_net - W/tau_E`，对应半解析更新：

```text
W_new = exp(-dt_eff/(tau_E+1e-12))*W
        + (1-exp(-dt_eff/(tau_E+1e-12)))*tau_E*P_net
```

实现还有储能下限、约化约束时间代理和剖面重建；该关系不表示完整托卡马克动力学已经得到验证。
`dt_eff` 根据来源约束时间代理取上限，可能小于 `sim.dt`。物理历史、图和积分必须累计实际返回值：

```python
from scirel.fusion.dynamics import initial_state_0d, zero_d_step_with_dt
sim0 = replace(sim, simulation_model="0d_fast")
state0 = initial_state_0d(machine, actuator, sim0)
state1, dt_eff_s = zero_d_step_with_dt(state0, machine, actuator, sim0)
physical_time = float(dt_eff_s)
assert 0 < physical_time <= sim0.dt
```

该例子沿用已绑定合同的有限初始化/一步证据。任意长轨迹、所有选择器和独立物理正确性尚未据此建立。

## 输入文件

`load_static_input(path)` 返回 `(machine, actuator, sim)`；`load_waveform_input(path)` 另外返回波形。
JSON 使用 `machine`、`actuator`、`simulation` 和可选 `waveform` 分区；未知配置键沿原实现抛出 `ValueError`。
加载路径还可能解析时间离散和 G-EQDSK 形状，因此配置读取成功不能代替所选模型的依赖/计算验证。
