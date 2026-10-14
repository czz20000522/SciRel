# GPDF 线性 Vlasov–Poisson 核心

本候选提供单一空间 Fourier 模式、固定离子背景的线性电子初值求解。
Python 实现由方程独立创作，不携带 MATLAB 实现，也不在运行时读取来源文件。
它是有明确 D2 修正的候选，不能称为逐位复现 D1 或人工批准发行。

## 科学模型和对角线判断

采用无量纲等离子体频率、Debye 长度归一化，方程为

\[
\dot f_j=-ikv_j f_j+E g_j,\qquad
ikE=-\Delta v\sum_j f_j,\qquad g_j=f_0'(v_j).
\]

因此离散生成矩阵是

\[
A=-ik\operatorname{diag}(v)+\frac{i\Delta v}{k}g\mathbf1^T.
\]

只有自由输运项为对角阵。电场是所有速度节点共同产生的标量，其反馈为稠密秩一项。
把后一项保留为对角线会失去不同速度节点之间的反馈。测试以单节点扰动确认其他节点
的 RHS 随之改变，并用独立 `scipy.linalg.expm(t*A)` 检验 RK4 的收敛阶数。
生产实现以向量和总和计算，内存为 O(nv+nt)，不创建大型稠密矩阵。

方程与 half-spectral 方法的公开依据是
[Xie 2012](https://arxiv.org/abs/1211.5984)；GPDF 与线性初值验证的关系见
[Xie 2013](https://arxiv.org/abs/1305.6476)。矩阵公式由上式直接消元推导，
独立 oracle 使用矩阵指数而非来源实现或存储答案。

## 来源绑定

注册 D1 `gpdf-d1-candidate/L1/operators/` 八个算子和
`L1/task_graphs/vp_landau/vp_graph.m` 为只读来源入口。

| 来源文件 | SHA-256 |
|---|---|
| vp_init.m | 388a6c8c466bf9d09a8a957a2e587709095adc6792a6872a683a7df8c634d0f5 |
| vp_distribution.m | e080e76a166f5668a58da6c8991cc065099637d31803bf5be33c4130dd7af3a1 |
| vp_field.m | dae7ea2815e9f73025152f8e0b65ce5646bd59d9c17ab5a4e7bc9358052a6a4a |
| vp_rhs.m | 7361c7e600e8ad10f87933e165e84cab126eed12cdfac117be33d2f5df315d66 |
| vp_rk4_step.m | 6a0c2e617c173f9cce2423c8383193b8c41a1aa876dc6d56b30b67733ecff4d0 |
| vp_evolve.m | 80bcf926f66d5bafdbf2f6f780b85c19f761390a7192e06ba5171033d223c72c |
| vp_envelope.m | 149bedbe8dcd914820f33d1ca484e1d14feeece726d9059e0569659fe45651eb |
| vp_diagnostic.m | 7b08c92bddfa8c3681d81c10ca5eeb90d3e356fbe38a29fdba49b0b6910847ed |
| vp_graph.m | e8882c2d80da115cc9f70ed473b7fc04e3cec4197c25c61fb1353bd84ed4f739 |

## 保留和修正

保留默认 Fn=2、kappa=1、k=.15、±20 速度窗、2048 个区间（2049 节点）、
dt=.01、2000 步，以及初始扰动 .1 exp(-v²)。保留端点全权重的矩形积分，
因此速度截断和积分误差仍需研究者独立评估，不能把时间积分收敛当作连续方程精确解。

| D1 行为 | D2 候选行为与依据 |
|---|---|
| 初始 E=.01 与 Poisson 不一致，首个 RHS 使用该值 | 初始 E 由初始 f 求和，首步及各阶段都满足同一约束；外部输入不一致时报错 |
| Maxwellian 理论数据表来自 k=.2，但实际模拟 k=.15 | 不给非匹配分布/波数套用表中理论值；仅 kappa=1 提供解析根 1-i k sqrt(2) |
| log(real(E))，MATLAB 对负值给复数，零点发散 | 返回 log(abs(E))，零点明确为 -inf，不丢弃虚部电场 |
| 最后一次场样本被排除 | 历史保留全部 nt+1 个样本 |
| 理论曲线任意偏移 -15 | 理论包络以初始幅值和 exp(wi*t) 表示，不附加偏移 |
| 极值时间索引存在额外偏移，少于两个峰值继续除零或索引失败 | 直接映射采样时刻；不足两个孤立峰明确 ValueError；组合函数保留演化并给出诊断不可用原因 |
| 用首末峰估计阻尼 | 全部选中峰的 log 幅值作最小二乘；频率仍为 pi/平均峰距 |
| 其余 Fn 值隐式进入 slowing-down | 仅 1–4 合法，未知选择器报错 |
| slowing-down 只使用平滑内部导数、在 +4/-4 使用不对称边界比较 | 默认完整弱导数含 -4 处 +f(4)、+4 处 -f(4) 的跳跃质量；线性沉积到相邻节点并除以 dv；边界普通导数取左右平均，显式 smooth 选项保留仅平滑 forcing |

Fn=1 为单位方差 Maxwellian；Fn=2 为 kappa>1/2 的规范化 kappa 分布导数；
Fn=3 为三角分布的分段导数。Fn=4 的默认弱导数对应
`f0=A/(|v|³+vt³) 1_{|v|<4}`，`vt=sqrt(2)`、`A=3sqrt(3)vt²/(4pi)`。
平滑内部导数之外还包含 `f0(4) delta(v+4)-f0(4) delta(v-4)`。
跳跃质量在包围截止点的两个节点按线性权重沉积，准确保留离散质量及一阶矩。
角点普通导数取两侧平均。分部积分 oracle 独立计算 `∫g sin(.7v)dv=-∫f0 .7cos(.7v)dv`；
省略跳跃项时该恒等式失败。源 A 保留，因此截断损失的密度质量不自动重新归一化。
`cutoff_mode="smooth"` 仅显式复用来源平滑 forcing，不代表截断分布完整弱导数。

`vp_diagnostic` 的 pi/峰距只适用于站立实振荡（或整体相位乘以实振荡）的幅值。
纯旋转复指数的模没有这类峰；该诊断不能替代色散根计算。有限速度节点的复现时间
TR=2pi/(k*dv) 随状态提供，不自动声称 TR 之后的长期行为可靠。

## 使用

```python
from scirel.kinetic.vlasov_poisson import solve_vlasov_poisson
result = solve_vlasov_poisson()
state = result['state']
assert state['df'].shape == (2049,)
assert state['dEt'].shape == (2001,)
print(result['diagnostic_status'])
```

低层入口分别提供 `vp_init`、`vp_distribution`、`vp_field`、`vp_rhs`、
`vp_rk4_step`、`vp_evolve`、`vp_envelope` 和 `vp_diagnostic`。
演化不修改传入状态；重复调用以输入 df 续接，并返回新的局部时间历史。
科学运行仅需要 NumPy；SciPy 矩阵指数、pytest 属于开发/独立参考环境。

## 验证边界

`tests/operator_contracts/test_gpdf_vlasov_poisson.py` 包含约束、非对角反馈、
所有来源分支、kappa 独立差分导数、矩阵指数四阶收敛、无反馈自由输运解析解、
合成阻尼余弦诊断、slowing-down 分部积分和截止点质量/一阶矩，以及
所有四分布的原默认 2049 节点/2000 步完整运行。
测试实际执行与安装 wheel 验证回执由主控串行科学容器运行记录；本文件不将
已编写测试当作已通过，也不将源码测试当作无源码安装接受。

首轮由主控科学容器执行的 12 项检查通过；弱导数新增检查后 14 项通过。
对应回执 `vp-first.log` 与 `vp-weak-derivative.log` 由主控冻结。
此时所有四分布的默认规模参数化检查已经编写，其最终运行回执另行记录。

Poisson 修正后默认扰动为偶实函数，电场主要为虚数。来源绘图的
`real(log(real(E)))` 相当于对实部取绝对值再取 log，可能直接变为 -inf，
不能代表该复 Fourier 模式的实际幅值；使用 `log(abs(E))` 同时对任意整体相位不变。
初始一致性失败也不依赖来源 runtime：来源给出的高斯扰动具有严格正积分，
Poisson 电场为纯虚非零量，必然不等于实数 .01。

最终边界检查对分布导数、Poisson 场、Vlasov RHS 和 RK4 的非有限派生值显式
抛出 FloatingPointError。先执行失败回归的回执为 `vp-nonrepresentable-RED.log`
（DID NOT RAISE）；随后添加窄范围有限性检查，最终针对性实跑另行绑定。
此前全仓回落检查为 2707 passed / 83 skipped / 47 warnings，发生在这次窄修正之前，
不能单独作为修正后源码接受证据。

最终科学轮次发现新加的极端 forcing 失败断言本身有误：Fn4 在 ±4 外的平滑导数
严格为零，`[-1e308,0,1e308]` 不应被要求报非可表示错误。保留该轮真实失败日志
`science-final.log` 和此前 RED，不重写历史；删除错误的新增 oracle，改以
`smooth` 截断尾部精确零且不发生溢出为正断言。实现只在支撑内部计算该平滑导数，
避免对必为零的支撑外点计算无用 inf/inf。Poisson 求和与 Vlasov RHS 真正非可表示
的两项失败断言和全部原科学容差均保持。
