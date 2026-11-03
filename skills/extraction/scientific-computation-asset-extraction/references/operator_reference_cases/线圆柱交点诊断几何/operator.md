# 线圆柱交点诊断几何

## Summary
该算子计算一条三维参数直线与以机器坐标 z 轴为轴的圆柱面的交点。输入是直线上一点、直线方向向量，以及位于圆柱面上的参考点；参考点的 xy 半径定义圆柱半径。输出是交点坐标和直线参数 `t`，满足 `point = line_point + t * line_direction`。

这个核适合中性粒子分析器、视线、射线或粒子轨道诊断中的几何相交判断。它不处理完整探测器边界，也不判断交点是否落在有限长度圆柱段内，而是提供被上层诊断几何复用的无限圆柱面交点计算。

## Scientific Role
这是诊断几何中的线-圆柱相交核。它把粒子轨迹、视线或射线参数化路径映射到圆柱机器边界的相交位置，是探测器命中判断、孔径遮挡、边界穿越和轨迹几何过滤的基础计算单元。

## Evidence References
- `FIDASIM/src/fidasim.f90:8094-8137` (`line_cylinder_intersect`): 以参考点定义圆柱半径，计算二次方程判别式，选择最近正交点或最大非正交点，并返回交点。

## Normalized Signature
`line_cylinder_intersection(line_point, line_direction, cylinder_point) -> (point, t)`

## Inputs
- line_point: 含义：直线上的一个三维点；形状：`(3,)`；单位：cm，与 FIDASIM 几何坐标一致；取值：有限实数。
- line_direction: 含义：直线方向向量；形状：`(3,)`；单位：相对方向或每单位参数位移；取值：有限实数。
- cylinder_point: 含义：圆柱面上的参考点，其 xy 半径定义圆柱半径；形状：`(3,)`；单位：cm；取值：有限实数。

## Outputs
- point: 含义：按源码根选择规则得到的线-圆柱交点；形状：`(3,)`；单位：cm；取值：有限实数。
- t: 含义：直线参数，满足 `point = line_point + t * line_direction`；形状：标量；单位：由 `line_direction` 参数化决定；取值：有限实数。

## Boundaries
### Assumptions
- 圆柱轴线与机器坐标 z 轴重合。
- 圆柱半径由 `sqrt(cylinder_point_x^2 + cylinder_point_y^2)` 定义。
- `line_direction` 是参数方向，不要求单位化。

### Use Boundaries
- 适用于无限圆柱面相交计算和上层诊断几何的局部核。
- 不适用于有限长度圆柱、任意轴向圆柱、完整探测器边界命中判定或含遮挡逻辑的完整 FIDASIM 诊断流程。

### Boundary Conditions
- 当直线没有 xy 方向分量时，按源码逻辑返回 `t = 0`。
- 当判别式小于 0 时，按源码逻辑返回 `t = 0`。
- 当存在正交点参数时，选择最小正参数；否则选择最大非正参数。
- 输入必须是有限三维向量。

## Validation Checks
- 从圆柱内部出发时，检查最近正交点和圆柱半径不变量。
- 两个交点都在过去方向时，检查最大非正参数选择。
- xy 方向速度为零时，检查 `t = 0` 边界行为。
- 非三维输入覆盖失败路径。

## Implementation Notes
- FIDASIM Fortran 模块未在当前沙盒中构建，因此测试使用源码公式派生的几何 fixture 和根选择不变量，而不是直接运行 Fortran 子程序。
- Agent 补充了三维 shape 和有限性校验；核心判别式、根计算和根选择逻辑按源码行号实现。
