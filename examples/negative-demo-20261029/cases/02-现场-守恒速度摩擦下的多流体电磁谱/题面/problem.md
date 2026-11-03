# 多组分碰撞等离子体的电磁本征谱

求均匀、静止、冷、非相对论磁化多流体的完整复频谱，并比较无摩擦和给定两两速度摩擦两种工况。摩擦算子由输入直接给定，是线性平均速度算子；不根据温度、电荷或库仑对数重新计算碰撞率。本题也不包含动理学碰撞、热交换或一般自碰撞闭合。

## 归一化与线性模型

所有输入均为无量纲量。取

$$
c=\epsilon_0=\mu_0=B_0=1。
$$

时间使用同一个 $t_0$ 归一化，因此 $\omega$、$\lambda$ 和 $\nu$ 均乘以 $t_0$，而 $k$ 以 $1/(ct_0)$ 为单位。背景磁场沿 $z$ 方向，波矢为

$$
\boldsymbol{k}=(k_x,0,k_z)。
$$

所有种群满足 $\boldsymbol{v}_0=0$、$c_{s,\parallel}=c_{s,\perp}=0$、$\gamma_{\rm pressure}=1$、$\nabla\log n=(0,0)$，并设置 `relativistic=false`。要求 $m_s>0$、$n_s>0$，背景满足电中性且无电流：

$$
\sum_s q_s n_s=0。
$$

不做隐式 SI 换算，也不加入额外的背景响应。

扰动采用

$$
\exp\left(i\boldsymbol{k}\cdot\boldsymbol{x}-i\omega t\right),
\qquad \lambda=-i\omega。
$$

未知量按每个种群的

$$
(\delta n_s,u_{x,s},u_{y,s},u_{z,s})
$$

排列，再接电磁场

$$
(E_x,E_y,E_z,B_x,B_y,B_z)，
$$

总维数为 $4S+6$。必须保留全部代数本征根，包括零根、重复根以及正负频率根；不能先按 Gauss 约束删根，也不能只选择某个命名分支。

令

$$
\rho_s=m_s n_s,
\qquad \Omega_s=\frac{q_sB_0}{m_s}。
$$

对第 $j$ 个种群，线性方程为

$$
\begin{aligned}
\lambda\,\delta n_j
  &=-i n_j(k_xu_{x,j}+k_zu_{z,j}),\\
\lambda\,\boldsymbol{u}_j
  &=\Omega_j(u_{y,j},-u_{x,j},0)
    +\frac{q_j}{m_j}\boldsymbol{E}
    +\sum_i\nu_{ij}\boldsymbol{u}_i,\\
\lambda\,\boldsymbol{E}
  &=ic^2\boldsymbol{k}\times\boldsymbol{B}
    -\frac{1}{\epsilon_0}\sum_jq_jn_j\boldsymbol{u}_j,\\
\lambda\,\boldsymbol{B}
  &=-i\boldsymbol{k}\times\boldsymbol{E}。
\end{aligned}
$$

由此得到

$$
M X=\lambda X,
\qquad \omega=i\lambda。
$$

$\operatorname{Im}(\omega)>0$ 表示增长，$\operatorname{Im}(\omega)<0$ 表示阻尼。增长率必须保留符号，不能用 $|\operatorname{Im}(\omega)|$ 代替。零根必须保留，因此最大增长率可以为零；题目不要求所有模态都严格阻尼。

## 碰撞矩阵的索引与物理含义

`inputs.json` 中的 `collision_states` 是彼此独立的摩擦工况，其余物理输入保持不变。每个 `nu` 都是完整的、带符号的 $S\times S$ 频率矩阵。约定如下：

- 行索引 $i$ 表示贡献速度 $\boldsymbol{u}_i$；
- 列索引 $j$ 表示第 $j$ 个种群的速度方程；
- 输入矩阵元素为 $\nu_{ij}$，实际速度算子为

  $$
  C_{ji}=\nu_{ij},
  \qquad C=\nu^{\mathsf T}。
  $$

因此方程中的摩擦项就是 $\sum_i\nu_{ij}\boldsymbol{u}_i$。输入的对角线已经包含损失项，不能再次减去行和、补负号、转置两次，或乘以质量和密度。

每个非零工况表示守恒的两两平均速度摩擦。对 $i\ne j$，要求

$$
\nu_{ij}\ge 0,
\qquad
\nu_{jj}=-\sum_{i\ne j}\nu_{ij}。
$$

这意味着每一列的和为零，因此所有种群具有相同速度时，摩擦项为零：

$$
C\,(u,u,\ldots,u)^{\mathsf T}=0。
$$

还要求质量密度配平：

$$
\rho_j\nu_{ij}=\rho_i\nu_{ji}=\alpha_{ij}\ge 0。
$$

于是总动量满足

$$
\sum_j\rho_j(C\boldsymbol{u})_j=0。
$$

对真实速度，摩擦项对动能的贡献为

$$
\frac{d}{dt}\left(\sum_j\frac{\rho_j|\boldsymbol{u}_j|^2}{2}\right)
 =-\sum_{i<j}\alpha_{ij}|\boldsymbol{u}_i-\boldsymbol{u}_j|^2
 \le 0。
$$

因此，负对角线表示两两摩擦造成的速度损失，不表示某个孤立种群存在自摩擦耗散。不能把 `nu` 的所有元素都解释成非负碰撞频率。若输入正对角线，应直接拒绝；不能在求解时自动翻转符号修复。

本题三种群的质量密度为

$$
\rho=(6,16,32)。
$$

非零工况对应

$$
\alpha_{12}=0.48,
\qquad
\alpha_{13}=0.12,
\qquad
\alpha_{23}=0.32。
$$

这些数值用于核对输入矩阵，`nu` 仍是唯一的摩擦输入。每个波矢的完整谱还应满足

$$
\sum_{\ell}\operatorname{Im}(\omega_\ell)=3\,\operatorname{tr}(\nu)。
$$

无摩擦工况的右端为 $0$，给定非零工况的右端为 $-0.49125$。这个恒等式用于检查完整谱的结构，不能替代逐根精度或物理正确性验收。

## 参考入口与适用范围

参考入口先读取公开种群参数并完成原初始化，再把每个公开 `nu` 原样传给碰撞参数，调用原有本征求解函数。原初始化的默认碰撞参数为零；其辅助分类按 $m\le1$ 和 $m>1$ 处理，并对类间参数作对称赋值。该默认规则不会自动构造负损失项，也不会执行质量密度配平，因此不能用于本题的摩擦矩阵。它同样不能区分以 kg 给出的通常电子质量和离子质量，因为这两者都小于 1。

本题使用明确的无量纲有符号矩阵覆盖默认值，不支持 SI 入口。

## 输入、输出与失败条件

所有输入位于 `inputs.json`。以下情况必须明确失败：未定义字段、非有限数、布尔值冒充数值、重复的种群/工况/波矢标签、数组维度错误、$k_y\ne0$、不支持的热压/漂移/梯度/相对论设置、非正质量密度，以及非中性背景。

每个 `nu` 必须是 $S\times S$ 矩阵，并满足上文的符号、列和与质量密度配平条件。允许全零工况，但整个请求至少包含一个非零工况。恒等式的输入检查允许

$$
32\,\epsilon_{\rm mach}\sum |\text{相关项}|
$$

范围内的舍入误差；该范围不是科学答案的数值容差。

输出必须包含每个工况、每个波矢的全部 $4S+6$ 个有限复频率，以及

$$
\texttt{maximum\_growth\_rate}=\max_\ell\operatorname{Im}(\omega_\ell),
\qquad
\texttt{summed\_growth\_rate}=\sum_\ell\operatorname{Im}(\omega_\ell)。
$$

复数编码为 `[real, imag]`，具体字段、数组形状和标签规则见 `output-spec.json`。若谱长度错误、出现非有限输出或本征求解失败，必须明确失败，不能换算法分支，也不能用空数组或零数组替代结果。模态次序可以不同；工况和波矢可以通过显式标签安全重排，但重复根的重数必须保留。
