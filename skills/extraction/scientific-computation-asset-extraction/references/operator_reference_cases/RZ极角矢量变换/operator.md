# RZ 极角矢量变换

## Summary
该算子在二维 Rho-Z 截面上，把矢量场从柱坐标截面分量 `(rho_component, z_component)` 投影到以原点为中心的极角分量 `(r_component, theta_component)`。它适用于磁面、场线或截面诊断中需要把局部矢量拆分为径向方向与极角方向的计算。

计算先由 `R = sqrt(Rho^2 + Z^2)` 和 `Theta = pi/2 + atan2(Z, Rho)` 定义极角坐标，再用二维正交基投影组合原始矢量分量。该算子只声明 Rho-Z 到 r/theta 的单向投影，不声明反向恢复。

## Scientific Role
这是二维轴对称截面上的物理坐标分量变换核。它把同一个矢量场表示从 Rho-Z 分量转换为局部径向/极角分量，便于后续沿磁面、场线或截面方向解释梯度、场量或诊断投影。

## Evidence References
- `pleiades/pleiades/analysis/helpers.py:290-298` (`transform_to_rtheta`): R/Theta 定义和 Rho-Z 到 r/theta 的矢量分量投影公式。

## Normalized Signature
`rz_to_rtheta(rho, z, rho_component, z_component) -> (radius, theta, r_component, theta_component)`

## Inputs
- rho: 含义：截面中的 Rho 坐标；形状：标量或任意一致数组形状；单位：长度单位；取值：有限实数。
- z: 含义：截面中的 Z 坐标；形状：与 `rho` 一致；单位：必须与 `rho` 一致；取值：有限实数。
- rho_component: 含义：矢量场在 Rho 方向上的分量；形状：与 `rho` 一致；单位：由上游矢量场决定；取值：有限实数。
- z_component: 含义：矢量场在 Z 方向上的分量；形状：与 `rho` 一致；单位：与 `rho_component` 一致；取值：有限实数。

## Outputs
- radius: 含义：由 Rho-Z 坐标得到的极角半径；形状：与输入一致；单位：与 `rho`/`z` 一致；取值：非负有限实数。
- theta: 含义：由 Rho-Z 坐标得到的极角；形状：与输入一致；单位：rad；取值：有限实数。
- r_component: 含义：矢量场径向分量；形状：与输入一致；单位：与输入矢量分量一致；取值：有限实数。
- theta_component: 含义：矢量场极角分量；形状：与输入一致；单位：与输入矢量分量一致；取值：有限实数。

## Boundaries
### Assumptions
- 所有坐标和矢量分量使用同一二维截面采样顺序。
- 角度约定为 `Theta = pi/2 + atan2(Z, Rho)`，不是标准数学极角。
- 矢量分量在同一正交截面基底中表达。

### Use Boundaries
- 适用于二维 Rho-Z 截面上的坐标和矢量分量转换。
- 只适用于从 Rho-Z 分量投影到 r/theta 分量；如果需要反向恢复，应单独确认角度约定。
- 不适用于完整三维非轴对称坐标变换，也不处理曲线坐标度量张量。
- 坐标原点处 `radius = 0` 时，数值公式仍可返回结果，但物理上的径向/极角方向退化，通常不应把原点结果用于方向敏感解释。

### Boundary Conditions
- 所有输入 shape 必须一致。
- 所有输入必须为有限实数。
- `atan2(0, 0)` 由 NumPy 约定返回 `0`，因此原点处 `theta = pi/2`；这是数值约定，不代表唯一物理方向。

## Validation Checks
- 用源码行号公式派生的代表性输入检查正向变换。
- 用二维正交投影的模长不变量检查矢量分量转换。
- 用 shape 不一致输入覆盖失败路径。

## Implementation Notes
- Agent 补充了输入 shape 和有限性校验；这些校验不改变核心投影公式，只把明显错误输入拒绝为显式异常。
