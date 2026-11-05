# 成对圆线圈的腔内磁场与轴向安装偏差

两个等半径、同向通流的细圆线圈在中心腔内产生近似均匀的轴向磁场。本题比较名义配置和上侧线圈轴向偏移后的磁场、约化极向磁通以及中心区域均匀性，并量化安装偏差的影响。

模型不包含等离子体响应、导体有限截面、自场、电阻和时间变化。完整输入见 `inputs.json`，输出字段见 `output-spec.json`。

## 坐标、单位与线圈配置

使用右手圆柱坐标

$$
(R,\phi,Z).
$$

长度单位为 m，电流单位为 A，磁场单位为 T。正电流沿 $+\phi$ 方向，场方向按右手规则确定。磁导率取

$$
\mu_0=4\pi\times10^{-7}\ \mathrm{H\,m^{-1}}.
$$

两个圆环均绕 $Z$ 轴，半径和电流分别为

$$
a=0.50\ \mathrm{m},
\qquad
I=+1000\ \mathrm{A}.
$$

这里的 $1000\ \mathrm{A}$ 是每个圆环的电流，不能再除以或乘以线圈数量。

名义配置的线圈平面位于

$$
Z=-0.25\ \mathrm{m},
\qquad
Z=+0.25\ \mathrm{m}.
$$

偏移配置保持下侧线圈不变，把上侧线圈移到

$$
Z=+0.27\ \mathrm{m}.
$$

## 观测网格与磁场量

观测半径和高度为

$$
R\in\{0.02,0.05,0.10,0.15,0.20\}\ \mathrm{m},
$$

$$
Z\in\{-0.20,-0.10,0,0.10,0.20\}\ \mathrm{m}.
$$

取两组坐标的全组合，共 25 个点。输出矩阵的行对应 $Z$，列对应 $R$，均保持输入顺序；展平时使用 C 顺序。观测点不在轴线上，也不在导体上，因此不要求处理这些奇点。

对名义和偏移两种配置，分别计算径向场、轴向场、场强和约化极向磁通：

$$
B_R,
\qquad
B_Z,
\qquad
|B|=\sqrt{B_R^2+B_Z^2},
\qquad
\psi=R A_\phi.
$$

环向场为零。$\psi$ 的单位为 Wb，并采用轴线上 $\psi=0$ 的规范。由轴线到半径 $R$ 的完整圆盘磁通为

$$
\Phi(R,Z)=2\pi\psi(R,Z).
$$

因此，$\psi$ 不是整个圆盘的总磁通。

## 均匀性和倾角诊断

每个配置使用自己的参考场

$$
B_{\rm ref}=B_Z(0.02\ \mathrm{m},0).
$$

中心子域取给定离散网格中满足

$$
R\le0.10\ \mathrm{m},
\qquad
|Z|\le0.10\ \mathrm{m}.
$$

该子域包含 9 个点。在这 9 个点上计算轴向场均匀性和最大倾角：

$$
U=\max\left|\frac{B_Z}{B_{\rm ref}}-1\right|,
$$

$$
T_{\max}=\max\left|\operatorname{atan2}(B_R,B_Z)\right|.
$$

$U$ 无量纲，$T_{\max}$ 的单位为 rad。计算倾角时使用有符号的 $B_Z$，不能先替换为 $|B_Z|$。此外，计算

$$
\Phi(0.10\ \mathrm{m},0)=2\pi\psi(0.10\ \mathrm{m},0).
$$

最终输出偏移配置减名义配置的差值：

$$
\Delta B_R=B_R^{\rm disp}-B_R^{\rm nom},
\qquad
\Delta B_Z=B_Z^{\rm disp}-B_Z^{\rm nom},
$$

$$
\Delta\psi=\psi^{\rm disp}-\psi^{\rm nom},
\qquad
\Delta U=U^{\rm disp}-U^{\rm nom},
\qquad
\Delta T_{\max}=T_{\max}^{\rm disp}-T_{\max}^{\rm nom}.
$$

## 数值预算与输出状态

数值预算已冻结为 output-spec.json 中的 numeric_budget。正常有限结果使用 COMPLETED_BOUNDED_PARTIAL；输入错误或非有限输出分别使用 HOLD_INVALID_INPUT 或 HOLD_NONFINITE_OUTPUT。

## 输出与边界

输出文件为 `result.json`。不得用绘图替代数值结果，不得对偏移配置强行施加中平面对称，也不得删除非有限值后继续汇总。
