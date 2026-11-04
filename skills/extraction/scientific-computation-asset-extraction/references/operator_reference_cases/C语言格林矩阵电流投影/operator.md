# C语言格林矩阵电流投影

## Summary
该算子把离散电流源的 Green 响应矩阵按电流向量线性叠加，得到评价点上的磁通 `psi`、径向磁场 `BR` 和轴向磁场 `BZ`。输入是长度为 `n_currents` 的电流向量，以及三个形状为 `(n_currents, n_points)` 的响应矩阵；输出是每个评价点上的三个场量数组。

核心运算是矩阵-向量投影：对每个评价点，把所有源电流 `currents[i]` 与对应 Green 响应 `gpsi[i, j]`、`gbr[i, j]`、`gbz[i, j]` 相乘后求和。该算子不计算 Green 函数本身，只复用已经生成的响应矩阵做高吞吐场量投影。

## Scientific Role
这是轴对称 R-Z 磁场计算链条中的场/电流响应投影核。它把离散线圈或电流丝源的电流幅值映射为磁通和磁场分量，可作为线圈场叠加、等离子体电流响应、平衡迭代或反演流程中的稳定低层数值核。

## Evidence References
- `pleiades/fields.py:129-153` (`psi`): `rank == 2` 时使用 `current @ gpsi(mesh=mesh)` 形成磁通投影。
- `pleiades/fields.py:154-194` (`BR`, `BZ`): `rank == 2` 时分别使用 `current @ gBR(mesh=mesh)` 和 `current @ gBZ(mesh=mesh)` 形成磁场分量投影。
- `pleiades/fields.py:196-219` (`_compute_greens`): `rank == 2` 时把每个电流源的 `gpsi/gBR/gBZ` 响应组织为 `(m, n)` 矩阵。

## Normalized Signature
`green_matrix_current_projection(currents, n_currents, gpsi, gbr, gbz, n_points, psi, br, bz) -> status`

## Inputs
- currents: 含义：离散源电流向量；形状：`(n_currents,)`；单位：A；取值：有限实数，顺序必须与 Green 响应矩阵第一维一致。
- n_currents: 含义：离散电流源数量；形状：标量；单位：1；取值：正整数。
- gpsi: 含义：单位电流对评价点磁通的 Green 响应矩阵；形状：row-major `(n_currents, n_points)`；单位：证据未声明，应与上游 Green 函数实现的磁通归一化一致；取值：有限实数。
- gbr: 含义：单位电流对评价点径向磁场 `BR` 的 Green 响应矩阵；形状：row-major `(n_currents, n_points)`；单位：证据未声明，应与上游 Green 函数实现的磁场归一化一致；取值：有限实数。
- gbz: 含义：单位电流对评价点轴向磁场 `BZ` 的 Green 响应矩阵；形状：row-major `(n_currents, n_points)`；单位：证据未声明，应与上游 Green 函数实现的磁场归一化一致；取值：有限实数。
- n_points: 含义：R-Z 评价点数量；形状：标量；单位：1；取值：正整数。

## Outputs
- status: 含义：执行状态码；形状：标量；单位：1；取值：`GREEN_PROJECTION_OK` 或输入合同错误状态。
- psi: 含义：投影后的磁通数组；形状：`(n_points,)`；单位：`currents` 与 `gpsi` 单位乘积；取值：有限实数。
- br: 含义：投影后的径向磁场数组；形状：`(n_points,)`；单位：`currents` 与 `gbr` 单位乘积；取值：有限实数。
- bz: 含义：投影后的轴向磁场数组；形状：`(n_points,)`；单位：`currents` 与 `gbz` 单位乘积；取值：有限实数。

## Boundaries
### Assumptions
- Green 响应矩阵已经由上游物理核计算完成，本算子只做线性投影。
- `currents` 的源顺序与 `gpsi/gbr/gbz` 的第一维顺序一致。
- C 实现使用 `double` 精度和 row-major 数组布局。
- 输入坐标和 Green 响应的几何语义由上游生成矩阵负责；本算子不重新判断源点或评价点几何。

### Use Boundaries
- 适用于已经拥有 Green 响应矩阵、需要重复投影不同电流向量的高性能场量计算。
- 适用于轴对称 R-Z 响应矩阵或其他同形线性响应矩阵，只要矩阵第一维是源、第二维是评价点。
- 不适用于计算 Green 函数、处理非线性电流依赖、求解平衡收敛、反演电流分布或修复上游矩阵奇异值。

### Boundary Conditions
- 任一输入或输出指针为空时返回 `GREEN_PROJECTION_NULL_POINTER`。
- `n_currents == 0`、`n_points == 0` 或矩阵元素数量溢出时返回 `GREEN_PROJECTION_INVALID_SIZE`。
- `currents/gpsi/gbr/gbz` 中存在非有限值时返回 `GREEN_PROJECTION_NONFINITE_INPUT`。
- 成功计算前会把 `psi/br/bz` 输出数组清零，再逐源累加。

## Validation Checks
- 使用源码公式派生的三源两点评价 fixture，手工计算 `currents @ gpsi/gbr/gbz` 并逐项断言。
- 使用单电流源 fixture 覆盖 `rank == 1` 标量乘法在 C profile 中的等价表示。
- 使用非法尺寸输入覆盖失败路径。
- 使用非有限输入覆盖失败路径，证明 C 改写不是只编译通过。

## Implementation Notes
- 源码直接支持的核心行为是 `current @ gpsi/gBR/gBZ` 线性投影以及 `(m, n)` Green 响应矩阵组织方式。
- Agent 补充内容属于语言 profile 改写和合同补全：显式长度参数、row-major 布局、状态码、空指针检查、非有限值检查和 C 测试夹具。
- 本案例没有补充新的磁场物理公式、Green 函数表达式、单位归一化或几何边界条件。
