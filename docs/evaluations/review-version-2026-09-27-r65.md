# SciRel KN1DPy terminal molecular diagnostics family r65

状态:开发期冻结待审(`pending_unapproved`),不是领域专家认可、可信版本或公开发行。本版是 r64(`c8c3a988b75ba622b616371a2762c5c79e59c989`,快照 `build/verification/review-2026-09-27-r64-convergence-v3`)的 successor;既有快照原样保留。合格 L1 交付根本轮复核为空,未消费任何合格 L1 输入。

## 性质:六项新 operator(终态分子诊断家族)

全部逐位复现保存 formal 实现;无修复。六项为:

1. `scirel.kinetic.terminal-flux-velocity-reduction`(`reduce_terminal_molecular_flux_velocity`):GammaxH2 轴向通量与 VxH2 平均流速
2. `scirel.kinetic.terminal-pressure-temperature-reduction`(`reduce_terminal_molecular_pressure_temperature`):pH2 压强与 TH2 温度
3. `scirel.kinetic.terminal-heat-flux-reduction`(`reduce_terminal_molecular_heat_flux`):qxH2 随机热通量与 qxH2_total 总热通量
4. `scirel.kinetic.terminal-energy-transfer-reduction`(`reduce_terminal_molecular_energy_transfer`):QH2 能量转移率
5. `scirel.kinetic.terminal-ion-state-reduction`(`reduce_terminal_molecular_ion_state`):nHP/THP/NuDis/NuE 离子态
6. `scirel.kinetic.terminal-conservation-diagnostic`(`reduce_qh2_total_conservation_diagnostic`):QH2_total 无量纲守恒误差

## 科学条件与依赖

前五个算子（flux/velocity、pressure/temperature、heat flux、energy transfer、ion state）共享同一柱坐标速度/空间网格合同；输入为 caller-owned terminal fH2 分布及柱坐标权重；输入合同：有限非负分布、正热速度、非零空间步长。

第六项（conservation diagnostic）仅接受 `axial_position_m`、`total_heat_flux_profile_w_m2`、`total_energy_transfer_rate_profile_w_m3` 三组有限同形 1-D 序列（至少两点、非零轴向间距），不接收 fH2 分布、速度网格或热速度。

- 无修复:保存 formal operator 逐字移植(含 make_dvr_dvx 环形面积/轴向宽度、积分循环、守恒差比)

## 组合证据

- `test_composition_heat_flux_energy_transfer_to_conservation_diagnostic`:将 heat_flux 输出 `total_heat_flux_profile_w_m2` 与 energy_transfer 输出 `total_energy_transfer_rate_profile_w_m3` 传入 conservation diagnostic,断言有限 [nx] 误差 profile
- `test_conservation_diagnostic_analytic_oracle_linear_flux`:线性 qx(x)=a*x+b、常数 Q=a 时误差精确为零(analytic oracle)

## 相对 r64 的增量

- r64: convergence/accumulation family(4 项),120 资产 dev38
- r65: terminal molecular diagnostics family(6 项),126 资产 dev39
- 版本 `0.1.0.dev38` → `0.1.0.dev39`

## 验证(全部 pwsh 7.6.6)

- 源码态全仓:**1424 passed, 43 skipped, 0 failed**(r64: 1410,+14;log `1424 passed, 43 skipped, 7 warnings in 217.30s`)
- 126/126 文档源码态与安装态校验通过,含示例执行
- 安装态全树:**1283 passed, 184 skipped, 0 failed**(log `1283 passed, 184 skipped, 7 warnings in 203.10s`)
- catalog `build/catalog/r65`:`complete: 126/126`,root digest `sha256:434249fe5f6df457b712992182a0d5631918a1002861db9d415723fcd86e3fca`
- 内部 wheel `scirel-0.1.0.dev39-py3-none-any.whl`,SHA-256 `be5a2a2b40461ded5c486d9c9689ceaaed987923b9ba428da73ab59ca1eef9b8`

## 边界与待决

- 不宣称合格 L1 消费、外部物理正确性、专家认可、可信晋级、公开发行
- 继续缓付:SIG 矩阵、分子 sigv 表、Franck-Condon 源、平移 Maxwellian 矩补偿、壁面源序列
- 许可证状态均为 `pending-human-decision`
