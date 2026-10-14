# GPDF 广义分布与根扫描 D2

本批从冻结 D1 的 `gpdf_zetaph`、`gpdf_calFp`、`gpdf_hilb`、`gpdf_residual`、`gpdf_small_k` 与 `root_scans` 提取科学能力。公开运行只依赖 NumPy/SciPy，不依赖 MATLAB、Symbolic Toolbox、上游源码或动态执行字符串。

统一定义为 $Z(z)=\int f(v)/(v-z)\,dv$，$Z_p=dZ/dz$。光滑衰减密度可将 $Z_p$ 写为 $\int f'(v)/(v-z)\,dv$；在位置 $a$ 的跳跃 $J=f(a+)-f(a-)$ 贡献 $J/(a-z)$。这是不完整 Maxwellian 与有限截断 slowing-down 修正的依据。实轴采用上边界 PV+iπf；解析分布的下半平面使用 Landau 延拓。非解析分段密度下半平面明确使用原实轴积分，避免把复数大小比较或猜测的延拓当作数学定义。

| 冻结能力 | SciRel 入口/分支 | 科学范围 |
|---|---|---|
| `gpdf_calFp` | `DensityExpression` | 安全 AST 表达式及链式法则一阶导数；接受 MATLAB 点运算符 |
| `gpdf_hilb`, `gpdf_calZ` | `evaluate_generalized_hilbert` | 解析密度的 Cauchy/Hilbert 变换、实轴 PV、下半平面延拓；显式特征网格与完整无限尾 |
| `gpdf_zetaph` Fn=0 | `evaluate_generalized_dispersion(selector=0)` | 默认归一化 Maxwellian；自定义解析表达式要求提供解析特征网格 |
| Fn=1 | selector=1 | 原点 delta，Z=-1/z、Zp=1/z² |
| Fn=2 | selector=2 | 正单位 top-hat，区间 [-.5,.5]，精确复对数 |
| Fn=3 | selector=3 | 单位三角密度，支撑 [-1,1] |
| Fn=4 | selector=4 | 原固定 gamma/kappa n=2、vt=1，归一化密度 sqrt(2)/π/(1+v²/2)² |
| Fn=5 | selector=5 | H(v-.1)exp(-v²)/sqrt(π)，保留原未重新归一化密度与准确跳跃 |
| Fn=6 | selector=6 | |v|≤4 的 slowing-down，3sqrt(3)/(4π)/(1+|v|³)，保留原有限截断质量 |
| `gpdf_residual` | `evaluate_gpdf_residual` | Langmuir、IAW、beam、generalized 四类，x=ω/(sqrt(2)k) |
| `gpdf_small_k` | `evaluate_gpdf_small_k` | 小 k 频率与指数阻尼渐近；对数域阻尼避免 0/0 |
| `scan_init`, `root_guess`, `root_frequency`, `legacy_fsolve`, `root_scan` | `scan_gpdf_roots` | 四原扫描网格、参数闭包、复根拆成两个实残差、频率归一化与顺序接续 |

D2 明确修正并保留的失败历史：

- Fn=2 原 `H(v-.5)-H(v+.5)` 是负密度，但同一函数的 Zp 是正密度导数；本批统一成正单位 top-hat。解析变换及独立定义积分同时验证 Z/Zp。
- Fn=5 原表达式的截断为 +.1，而额外跳跃项使用 -.1；本批使用实际截断 +.1 对应的分布导数。测试显式显示旧修正与新结果不同。
- Fn=3/6 原复数大小比较没有唯一解析延拓；本批规定上下半平面原实轴积分互为共轭，不假冒全纯分段密度。
- 原 `fsolve(f,x0,options,kk)` 在冻结环境 Octave 7.3 被拒绝。SciRel 用闭包绑定 k、把复未知数映射为两维实向量；不重新调用这个无效接口。
- `calZ` 原实现遇 NaN 就移动输入 1e-10；本批保留真实输入，delta/端点奇点显式拒绝，光滑分布上半平面可去奇点由原积分直接给值。

表达式仅支持数值常量、pi、v、算术与 exp/log/sqrt/sin/cos/sinh/cosh/tanh。拒绝属性、下标、未知名称和任意函数调用。与原 `eval`/Symbolic Toolbox 的任意表达式域不同，此受限域是公开合同。自定义密度必须为实值可积且导数衰减；网格由调用者明确解析所有有效特征，有限采样不能证明此条件。当前积分结果不附全局误差证书；没有为所有任意表达式提供精度保证。

独立验证包括：七个 selector 的直接定义积分及平方核导数积分；Lorentzian 上/下半平面与实轴残数闭式；上半平面可去奇点；分段分布共轭关系；截断跳跃回归；小 k 冷等离子体极限与指数阻尼；四类根扫描的实际残差。最终结果与安装轮次见本次冻结交付报告，本文不把源码测试提升为安装包验收。
