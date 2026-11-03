# 速度空间反应率积分

## Summary
该算子计算入射粒子与 Maxwellian 目标粒子之间的速度空间平均反应率 `<sigma v>`。输入包括入射粒子能量、入射粒子质量、目标温度、目标粒子质量，以及一个给定碰撞能量返回截面的函数；输出是每个入射能量对应的反应率数组。

核心计算流程是先构造归一化的轴向/径向速度网格，再归一化目标 Maxwellian 分布，随后在速度空间上积分 `sigma(E_rel) * v_rel * f_target`。该核适合中性粒子动理学、碰撞反应率、截面表评估等流程中，把微观截面函数转换成可用于流体/动理学源项的 `<sigma v>`。

## Scientific Role
这是反应率积分核。它把碰撞截面函数和目标 Maxwellian 分布组合为速度空间平均的反应率，用于中性粒子、离子、分子反应或电离/复合/电荷交换类源项计算。

## Evidence References
- `KN1DPy/KN1DPy/make_sigmav.py:6-62` (`make_sigmav`): `<sigma v>` 主流程，包括速度网格、目标分布归一化、相对速度和积分。
- `KN1DPy/KN1DPy/create_vr_vx_mesh.py:16-57` (`create_vr_vx_mesh`): 根据能量/温度范围构造归一化速度网格。
- `KN1DPy/KN1DPy/make_dvr_dvx.py:17-123` (`make_dvr_dvx`): 构造径向和轴向速度空间微分体积。

## Normalized Signature
`maxwellian_averaged_sigma_v(particle_energy_ev, particle_mass_amu, target_temperature_ev, target_mass_amu, sigma_function, velocity_bins=100) -> sigma_v`

## Inputs
- particle_energy_ev: 含义：入射粒子能量；形状：标量或 `(n_energy,)`；单位：eV；取值：正有限实数。
- particle_mass_amu: 含义：入射粒子质量数；形状：标量；单位：amu，以氢原子质量为基准；取值：正有限实数。
- target_temperature_ev: 含义：目标 Maxwellian 分布温度；形状：标量；单位：eV；取值：正有限实数。
- target_mass_amu: 含义：目标粒子质量数；形状：标量；单位：amu，以氢原子质量为基准；取值：正有限实数。
- sigma_function: 含义：碰撞能量到截面的函数；形状：输入为相对碰撞能量数组，输出同形状数组；单位：输入 eV，输出 m^2；取值：非负有限截面。
- velocity_bins: 含义：径向速度网格基准数量；形状：标量整数；单位：1；取值：至少为 2。

## Outputs
- sigma_v: 含义：每个入射能量对应的 Maxwellian 平均反应率；形状：`(n_energy,)`；单位：m^3/s；取值：非负有限实数。

## Boundaries
### Assumptions
- 目标粒子速度分布为各向同性 Maxwellian。
- 截面函数只依赖相对碰撞能量。
- 源码使用 `mH = 1.6726231e-27 kg` 和 `q = 1.602177e-19 C` 做 eV 与速度换算。

### Use Boundaries
- 适用于用截面函数生成反应率表或源项系数。
- 不适用于非 Maxwellian 目标分布、各向异性速度分布或需要量子态分辨输运的完整碰撞辐射模型。

### Boundary Conditions
- 能量、质量和目标温度必须为正有限值。
- 截面函数必须返回与输入碰撞能量同形状的非负有限数组。
- 速度网格数量必须至少为 2。

## Validation Checks
- 常数截面下，与 KN1DPy 源函数 `make_sigmav` 直接数值对照。
- 能量相关截面下，与 KN1DPy 源函数直接数值对照。
- 非正目标温度覆盖失败路径。

## Implementation Notes
- Agent 补充了输入正值、有限性和截面输出 shape 校验；主速度网格、Maxwellian 归一化、相对速度和积分公式保持源代码证据中的计算结构。
