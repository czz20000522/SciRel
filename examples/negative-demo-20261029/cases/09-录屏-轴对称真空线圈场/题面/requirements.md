# 轴对称真空线圈场计算需求

状态：**FROZEN_FOR_INDEPENDENT_EXECUTION**。题目、完整输入与本次新增数值预算已冻结，由主控确认维护基线后安排独立出库执行。

需要计算给定环形线圈系统的真空磁场和极向磁通，供空间场分布、中心截面与磁镜约束分析使用。物理问题采用稳恒 Biot–Savart 定律；输入电流位于以 Z 轴为中心的理想闭合圆形细丝上。介质为真空，无等离子体电流、外加背景场或磁性材料。采用固定常数 μ0/(4π)=1e-7 T·m/A。

## 输入与物理约定

读取同目录 `inputs.json`。`filaments` 含全部 84 个圆环的半径 R、位置 Z 和每个圆环的电流 I，单位依次为 m、m、A。每条记录是一个等效单匝闭合圆环，圈数为 1，I_A 是以 A 为单位的电流；源工况的匝数/权重均已物化在这 84 条记录中，不可再按组数、匝数或 A-turn 系数重复倍乘。正电流沿柱坐标正方位方向，按右手定则在对称轴上产生正 BZ。

柱坐标中 BR 沿增大 R 的方向，BZ 沿增大 Z 的方向；本问题 Bphi=0。磁场分量和模长采用 T。定义 psi=R*Aphi=Φ/(2π)，其中 Φ 为固定 Z 平面内由半径 R 圆周围成的圆盘所穿过的磁通；psi 单位为 Wb/rad，轴上规范 psi(0,Z)=0。不要将 psi 输出为完整磁通 Φ。轴上 BR=0，BZ 采用物理极限，不能因为中间表达式出现 0/0 就将轴向磁场置零。

`grid.R_m` 为包含两端点的 0 至 0.75 m 共 76 点，`grid.Z_m` 为包含两端点的 -1 至 1 m 共 201 点。结果的轴序固定为 `[Z,R]`，二维 shape 为 `[201,76]`，展平时 R 变化最快。共 15276 个网格点，全部保留；网格没有与电流丝同位置的导体奇点，靠近电流丝的点也不能掩膜、删去或裁切。

## 程序入口与产物

提供程序入口 `python solve.py --inputs inputs.json --output-dir results`，并交付可重复运行所需代码与依赖说明。入口须读取实际输入文件，不能硬编码隐藏参照值。

生成以下产物：

- summary.json：必须包含 status、axis_max_Bmag_T、axis_center_Bmag_T、mirror_ratio_denominator_error_budget_T 和 axis_mirror_ratio。镜比严格定义为整个给定轴线 201 点上的 Bmag 最大值，除以 R=0、Z=0 处 Bmag；包括两端点，不使用延伸轴线、插值极值或指定单侧局部峰值。令 eC = 1e-10 T + 1e-7*abs(axis_center_Bmag_T)；当中心值 <= eC 时，必须令 status=MIRROR_RATIO_UNDEFINED_LOW_DENOMINATOR、axis_mirror_ratio=null、保留场和 profile 产物并记录 mirror_ratio_denominator_error_budget_T=eC，不得直接相除。有效镜比时使用 status=COMPLETED_BOUNDED_PARTIAL。输入错误和非有限场分别使用 HOLD_INVALID_INPUT 与 HOLD_NONFINITE_FIELD。

- `run_receipt.json`：实际运行命令、输入文件 SHA-256、Python/依赖/SciRel 版本、SciRel 包身份，以及实际执行过的公开 SciRel 能力调用记录（完整接口名、相关输入身份/维度、输出维度、用于哪些最终产物）。单纯导入包或列出可用接口不构成实际能力调用。原始运行日志一并交付。

## 依赖与信息边界

允许 Python 标准库、NumPy、SciPy 和公开交付的 SciRel。必须实际调用公开 SciRel 能力参与计算，并在回执中保留调用事实。不要读取来源项目、源归档、参考实现、历史输出或隐藏验收材料；需求与必要输入仅以本公开包为准。遇到公开能力不足、接口不适用、无解或数值失败时，明确报告证据，不推断成功。

## 公开完成条件与误差预算

全部必需文件存在、坐标及单位正确、所有 15276 点上的 BR/BZ/psi/Bmag 有限、完整网格与两条 profile 一致、镜比采用上述定义、实际 SciRel 调用可核实。计算还须保持轴上约定与线圈上下对称工况的物理对称性，不以局部样点代替全网格。

以下为本次冻结的数值误差预算。逐元素比较采用 `abs(actual-reference) <= atol + rtol*abs(reference)`，rtol=1e-7；BR/BZ/Bmag 的 atol=1e-10 T；psi 的 atol=1e-11 Wb/rad。profile 使用其对应量相同的预算。坐标的绝对预算为 1e-14 m、相对预算为 0；派生结果还须在对应量预算内与本次完整网格保持一致。镜比单独采用传播后的绝对误差预算：令 M 为参考整轴 Bmag 最大值、C 为参考中心 Bmag，分子和分母各自沿用场量预算 eM=1e-10 T+1e-7*abs(M)、eC=1e-10 T+1e-7*abs(C)。只有 C>eC 时，镜比允许绝对误差为 `eM/C + (M+eM)*eC/[C*(C-eC)]`，按 `abs(actual_ratio-reference_ratio)` 不超过该值判断，不再叠加固定镜比 rtol 或 atol。若 C<=eC，应明确报告低分母及镜比在此误差预算下未定义，不能直接相除或判定比较成功。全部元素逐一检查，不跳过零值、近丝点或失败项。不允许通过重新缩放、增加磁通偏置或扩大容差使结果通过。

## 核验数量

BR/BZ/psi 分别为 15276 个标量，三项共 45828；Bmag 另有 15276 个派生标量，四项场量合计 61104。坐标 R/Z 共 30552 个标量。两条 profile 的四项场量共 1108 个标量、坐标共 277 个标量；summary 的三项共 3 个标量。文件逐项数值比较总计 93044 个标量，其中包含派生量与切片的重复交付。实际 SciRel 调用证据另行核对，不计入这个数值分母。
