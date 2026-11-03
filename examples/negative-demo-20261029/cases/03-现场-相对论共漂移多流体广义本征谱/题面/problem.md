# 多组分相对论流体的广义本征谱

所有种群沿背景磁场以 $0.6c$ 共漂移，背景净电荷和净电流均为零。本题按给定的相对论惯性矩阵求完整复频谱。不能在非相对论结果上直接添加 $\boldsymbol{k}\cdot\boldsymbol{v}_0$，也不能把惯性矩阵 $A_s$ 简化为单位矩阵。所有背景速度必须严格小于光速。

## 归一化、变量与输入

所有量均已归一化：

$$
c=\epsilon_0=\mu_0=B_0=1.
$$

背景磁场沿 $z$ 方向，波矢为

$$
\boldsymbol{k}=(k_x,0,k_z).
$$

每个种群输入 $q_s$、$m_s$、$n_s$、背景速度

$$
\boldsymbol{v}_{0,s}=(v_{x0,s},v_{y0,s},v_{z0,s}),
$$

以及 $c_{s,\parallel}$、$c_{s,\perp}$、$\gamma_{\rm pressure}$ 和密度梯度

$$
\nabla\log n_s=(\epsilon_{x,s},\epsilon_{y,s}).
$$

碰撞项固定为零。物种顺序只定义未知量的坐标顺序，不定义模态或本征根的输出顺序。

扰动采用

$$
\exp\left(i\boldsymbol{k}\cdot\boldsymbol{x}-i\omega t\right),
\qquad
\lambda=-i\omega.
$$

未知量先按种群排列为

$$
(\delta n_s,u_{x,s},u_{y,s},u_{z,s}),
$$

再接电磁场

$$
(E_x,E_y,E_z,B_x,B_y,B_z).
$$

总维数为 $4S+6$。这里 $\boldsymbol{u}_s$ 是速度扰动，$\boldsymbol{E}$ 和 $\boldsymbol{B}$ 是场扰动。

## 背景系数

对每个种群定义质量密度、平行和垂直压力系数、压力各向异性以及回旋频率：

$$
\rho_s=m_sn_s,
$$

$$
P_{\parallel,s}=\frac{\rho_sc_{s,\parallel}^2}{\gamma_{{\rm pressure},s}},
\qquad
P_{\perp,s}=\frac{\rho_sc_{s,\perp}^2}{\gamma_{{\rm pressure},s}},
$$

$$
\Delta_s=\frac{P_{\parallel,s}-P_{\perp,s}}{B_0},
\qquad
\Omega_{c,s}=\frac{q_sB_0}{m_s}.
$$

## 线性方程

连续方程为

$$
\lambda\,\delta n_s
=-i(\boldsymbol{k}\cdot\boldsymbol{v}_{0,s})\delta n_s
-n_s\left[(ik_x+\epsilon_{x,s})u_{x,s}
+\epsilon_{y,s}u_{y,s}
+ik_zu_{z,s}\right].
$$

速度方程为

$$
\begin{aligned}
\lambda A_s\boldsymbol{u}_s
={}&-i(\boldsymbol{k}\cdot\boldsymbol{v}_{0,s})A_s\boldsymbol{u}_s
+\Omega_{c,s}(u_{y,s},-u_{x,s},0)\\
&-i\frac{\delta n_s}{n_s}
  (k_xc_{s,\perp}^2,0,k_zc_{s,\parallel}^2)
+\frac{q_s}{m_s}(\boldsymbol{E}+\boldsymbol{v}_{0,s}\times\boldsymbol{B})\\
&-i\frac{\Delta_s}{\rho_s}
  (k_zB_x,k_zB_y,2k_xB_x).
\end{aligned}
$$

各向异性项的 $z$ 分量中系数 2 是本题闭合模型的一部分，不能改成 1。

当 relativistic=false 时，

$$
A_s=I_3.
$$

当 relativistic=true 时，定义

$$
\Gamma_s=\frac{1}{\sqrt{1-|\boldsymbol{v}_{0,s}|^2/c^2}},
$$

$$
A_s=\Gamma_sI_3
+\frac{\Gamma_s^3}{c^2}\boldsymbol{v}_{0,s}\boldsymbol{v}_{0,s}^{\mathsf T}.
$$

此时必须满足

$$
|\boldsymbol{v}_{0,s}|<c.
$$

Maxwell 方程为

$$
\lambda\boldsymbol{E}
=ic^2\boldsymbol{k}\times\boldsymbol{B}
-\frac{1}{\epsilon_0}\sum_s q_s
  (n_s\boldsymbol{u}_s+\boldsymbol{v}_{0,s}\delta n_s),
$$

$$
\lambda\boldsymbol{B}=-i\boldsymbol{k}\times\boldsymbol{E}.
$$

这些方程组成广义本征问题

$$
M X=\lambda A X,
\qquad
\omega=i\lambda.
$$

## 模型范围与输出

这是给定背景系数下的局部线性模型，只包含上述项，不要求从非线性方程重建全局平衡。必要的静态补偿只用于维持输入背景，扰动方程不加入未知的补偿响应。

所有输入工况位于 inputs.json。本题不规定求解算法，但每个波矢必须输出全部 $4S+6$ 个复频率，保留零根、重复根、负频率根及其重数。稳定性按 $\operatorname{Im}(\omega)$ 的符号判断，不能用绝对值替代。
