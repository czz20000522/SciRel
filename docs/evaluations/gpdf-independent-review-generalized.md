# GPDF Faddeeva / J-pole / Vlasov–Poisson 独立复核

复核者：GPDF `generalized_core` worker。复核对象由另一 worker/root 编写；本复核者未编写这些实现。本文是技术复核记录，不是人工认可或再分发授权。复核者自己的广义分布实现不在本独立结论内。

## 固定对象与证据边界

读取源码、冻结 D1 的 J-pole 来源、现有科学回归和 root 提供的实际容器日志。科学容器由 root 串行调度；本复核者没有重复启动容器，也没有把日志读取得到的结果冒称独立重跑。

| 对象 | 本次读取 SHA256 |
|---|---|
| `src/scirel/kinetic/faddeeva_variants.py` | `2dcf463248d7e587b03110459d5e3aa43eab719b3a734c518a6e731cc65268a5` |
| `src/scirel/kinetic/_gpdf_pole_data.py` | `6ce6cadb4942bf6ecb5c152fc5ac8b1d6e4b27f78ff38cf9cf68ec0efcdf2156` |
| `src/scirel/kinetic/vlasov_poisson.py` | `2a94f232447463e56de9472cd0bc1988f1c12e01552fda5e34452508a740d17f` |
| `tests/operator_contracts/test_gpdf_faddeeva_variants.py` | `2e79c97c933ef9d457d00672c1c3e520f52829c74d28dfbeecaf3d677c669dcf` |
| `tests/operator_contracts/test_gpdf_vlasov_poisson.py` | `a6e6d5cb678296d3050405c4ca9befcbace1be43710e5b813d1a9bb1514135cb` |

源码继续变化时，本次 SHA 绑定复核不能自动覆盖后续修改；后续测试及冻结身份由最终报告保存。

## 独立发现与修正

发现一项实际数值域缺陷：初版 Faddeeva 的 `denom**2` 与下半平面 `exp(-upper**2)` 在 float64 中可能先溢出，而最终数学函数仍可表示。例如 z=1e200-.1i 的 w(z) 具有 i/(sqrt(π)z) 主项，指数反射项已下溢为零；直接 float64 平方却产生非有限复数并误报失败。J-pole 的反射项存在同样问题。

复核者将具体触发输入交 root；root 将平方分母改为顺序除法，并在指数中先提升到 `np.clongdouble` 再平方，最后转换回目标复数类型。复核者重新读取实际修正代码，确认两处指数均先提升类型；分母没有先乘 sqrt(π) 或先平方。`outputs/faddeeva-review-regression.log` 实际记录 27 passed，并新增巨大有限实部上下半平面回归，保留 -40i 的真实不可表示溢出失败。

平台边界：此宽精度指数修正依赖已测 Linux 科学容器中 `np.longdouble` 能容纳全部 float64 坐标平方。不能从该结果推断 longdouble 与 double 同宽的平台也拥有同样数值域。极大实部的相位约化精度也不能仅由有限回归证明普遍可靠。

## 数学核对

- Weideman 系数的采样长度 4N、FFT 平移、正频系数截取与 Möbius 变量一致；w 的下半平面反射满足 w(z)=2exp(-z²)-w(-z)。正虚轴使用 erfcx 排除 exp(y²)erfc(y) 的 inf*0。
- Z=i√πw；J-pole 的下半平面公式为共轭原实轴变换加 2i√πexp(-z²)，符号正确。数据镜像 b→conj(b)、c→-conj(c) 与冻结 D1 相符；源文件摘要实测为 `7d06418f453b6a2ac0d6ba805df9c62a3d33af91b21dd00968695ad4cd5c08dc`，与私有数据声明一致。逐行抽查 8/12/16/24 阶数据和源镜像规则，未见错配；未把十进制文字差异解释为许可证明。
- J-pole 是固定有误差的有理近似；6 个测试点及约定容差不证明全复平面精度。对矩阵所有元素逐一计算修复了源 `length(z)` 漏元素行为。
- Vlasov–Poisson 满足 ikE=-∫δf dv 以及 δf_t=-ikvδf+E f0′。离散闭合 E=i*dv*sum(δf)/k，代入得到完整矩阵 A=-ik diag(v)+(i dv/k)f0′·1ᵀ；反馈是秩一全耦合，不能变成逐节点对角项。
- 每个 RK4 stage 使用该 stage 的闭合 E，因而对固定离散矩阵是四阶多项式；既有独立 dense expm 误差比测试确实检验四阶而非仅重复实现。初始场从 Poisson 约束计算，显式拒绝源初值 .01 的不闭合行为。
- 固定 kappa=1 时密度是宽度 sqrt(2) 的 Cauchy，其精确 ε=1-1/(ω+i sqrt(2)k)²，故正频根 ω=1-i sqrt(2)k，与代码理论值一致。其他 kappa 或家族不附冒用该理论值。
- slowing-down 在 ±4 的导数跳跃符号为左正右负；线性节点沉积保持跳跃总质量与一次矩。既有积分分部和离网格节点回归独立于 RK4。端点含全权重的矩形积分保留源离散，空间截断与速度误差仍需单独看待。

结论：上述固定源码在所述数学与源级测试范围内技术复核通过；未发现剩余阻断问题。数值近似精度、有限速度域/步长、longdouble 平台域、安装包执行和许可/人工认可各有独立边界，不由本记录替代。

## 最终候选 VP 窄增量复核（2026-10-14）

本次只追加复核此前 VP 摘要 `2a94f232447463e56de9472cd0bc1988f1c12e01552fda5e34452508a740d17f` 之后的有限值防护、Fn4 支撑内部算术及新增错误 oracle 更正。实际读取当前 `vlasov_poisson.py` 并重新计算 SHA256，确认最终对象为 `a94a5247c72b5fcf206b6dcfee294e4a68abc57866264fc776834174f3a221b8`。不将此窄复核扩展为对其他后续文件修改的重新批准。

- `vp_field` 保留 E=(i/k)dv∑δf，在求和和缩放后检查派生场有限性，非有限结果抛出 FloatingPointError。`vp_rhs` 保留 -ikvδf+E f0′，对完整派生向量作相同检查；未改变耦合符号、矩形权重或线性动力学。现有输入有限性不保证派生乘法/求和仍有限，因此这些检查补全失败闭合；它们不证明极端相消输入的精确算术可表示性。
- Fn4 先创建零向量，仅在 |v|≤4 的节点计算平滑导数；端点继续乘以 .5，weak 模式继续施加原有左右跳跃沉积。支撑内分母严格正且速度有界，避开支撑外无意义的巨大速度立方和 inf/inf；数学密度与跳跃没有改变。
- 重读 VP 评价文档及测试：此前新增 oracle 要求 `[-1e308,0,1e308]` 的 smooth 截断导数报错，但三个位置的正确值都为零（外部无支撑，原点的导数为零），该新增失败要求本身错误。更正为在 `np.errstate(over='raise', invalid='raise')` 下返回精确全零，atol=rtol=0，具有真实的失败判别力。Poisson 派生求和溢出和 RHS 派生溢出的两项报错回归仍保留。评价文档明确保留 `vp-nonrepresentable-RED.log` 及 `science-final.log` 历史，不把首次失败改写成成功；这不是放宽既有科学断言或容差。

本次实际读取 `outputs/science-final2.log`，最终科学轮次记录 **184 passed**。另读取无源码安装回执 `outputs/d3/{SCIENCE,CONTAINER,EXAMPLES}.json`：SCIENCE 的 all_passed=true，覆盖七个 selector、四个完整扫描共 130 根以及四个 VP 默认 2049 节点/2000 步案例；EXAMPLES 的 all_passed=true，列出 23 个实际执行的 exact-document 示例。CONTAINER 记录退出码 0、NetworkMode=none、1 CPU/2 GiB、科学线程数 1，挂载只有离线 wheel 输入、验证 driver 与结果目录；SCIENCE 记录 source_mount=ABSENT、answers=NOT_USED、forbidden_development_imports=ABSENT，导入源位于 `/target/lib/python3.14/site-packages/scirel`。独立计算已安装输入 wheel 摘要为 `259dba11c4bca6a9b4fcd7b17135c26b0bf10f853a57e1dcbf25c1575427d2bd`，与主控指明的候选一致。

本复核者检查了上述真实日志、容器配置和摘要，没有重跑科学测试或 D3。D3 结论限于这份 wheel 在记录的 Linux arm64 / Python 3.14.7、NumPy 2.5.4、SciPy 1.18.1 环境中的实际检查范围；不是跨平台、任意输入、全局精度或任意分支的证明。最终 VP 窄增量技术复核通过，未发现本范围内剩余阻断问题；人工认可和再分发许可仍独立于技术与安装证据。
