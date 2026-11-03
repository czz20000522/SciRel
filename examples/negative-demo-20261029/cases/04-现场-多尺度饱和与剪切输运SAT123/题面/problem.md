# 磁化环形等离子体的多尺度湍流饱和与准线性输运

本题研究磁化环形等离子体中微观漂移波湍流的一个降阶计算流程。背景可以理解为托卡马克局部磁通管：密度和温度梯度驱动线性微不稳定性，扰动包含静电势以及平行矢势、平行磁压缩等电磁响应；低频的 $E\times B$ 流、带状流和磁几何改变湍流的混合与饱和，饱和后的涨落再产生粒子、能量和动量输运。

程序不直接推进非线性分布函数，而是读取给定的首遍/第二遍线性增长谱和准线性响应权重，依次计算参考混合峰、剪切引起的谱位移、SAT1/2/3 经验饱和强度，再计算各物种和各场通道的输运谱及其波数积分。输出的主要物理量包括：增长率和混合峰参数、剪切后的有效增长率、饱和场强、粒子通量、能量通量、环向与平行动量通量，以及能量交换通量。

输入不包含最终位移、场强或输运结果。线性响应表是本题规定的科学输入，不由物理参数、矩算子或移位后的本征问题重新生成。因此，本题不声称完成上游线性本征谱、非线性 gyrokinetic 时域演化、物理矩算子或实验预测。每个情景在独立原生进程中运行，避免初始化状态跨情景泄漏。

## 物理背景与计算目标

### 1. 线性微不稳定性

在磁化等离子体中，平衡密度和温度梯度能够驱动漂移波类微不稳定性。线性阶段，一个给定波数和模态的扰动幅度可写成

$$
\delta f_k(t)\propto \exp(\gamma_k t-i\omega_{r,k}t),
$$

其中 $\gamma_k$ 是增长率，$\omega_{r,k}$ 是实频率。增长率谱决定哪些 $k_y$ 和模态容易增长，但它本身不是饱和后的湍流幅度。输入文件中的 `first_growth_cs_over_a` 和 `second_growth_cs_over_a` 是两组已经给定的线性响应，程序不在本题内重新求解它们。

首遍响应用于寻找低波数的参考混合峰和计算剪切位移；第二遍响应用于在经验饱和规则中计算有效增长率和输运。这里的“首遍/第二遍”是模型流程的两个响应阶段，不是同一个本征问题的两次时间推进。

### 2. 带状流与 $E\times B$ 剪切

湍流扰动可以驱动近似轴对称的低频带状流。带状流对应的 $E\times B$ 剪切会使漂移波结构在径向波数上发生位移，并降低相干增长。降阶模型通常用线性增长率与波数构造混合速度尺度；本题首遍峰采用

$$
v_{zf}=\frac{\gamma}{k_y}.
$$

在给定剪切下，程序计算谱位移 $k_{x,e}$，再把它转换为几何网格上的 $k_{x0}$ 和 $k_{xx}$。随后，剪切通过 SAT 分支中的抑制因子进入有效增长率。这里的剪切抑制是模型规定的闭合项，不是程序从完整非线性带状流方程自洽演化出来的结果。

### 3. 饱和与经验闭合

线性不稳定性会指数增长，但真实湍流不会无限增长。非线性模态耦合、带状流混合、稳定模态能量吸收、有限相关时间和几何效应共同限制涨落幅度。经验饱和闭合的任务，是用可计算的线性信息和少量几何/控制参数，把增长率转换为饱和强度 $P$。

本题的 SAT1、SAT2、SAT3 就是三种固定的饱和闭合分支。它们不是三次迭代，也不是三个独立本征问题：

- SAT1 使用单尺度的 $w=k$ 和 $h=k_{x,e}$，在 s-alpha 几何下用剪切抑制后的增长率计算饱和强度；
- SAT2 在 $k_{\rm cut}$ 两侧使用不同的波数映射和增长率表达式，并对高波数区做解析加权平均；
- SAT3 在 SAT2 的基础上增加 $k_T$ 处的低/高尺度连接，并使用模态静电能量权重确定 QLA 因子。

这些分支属于本题规定的经验模型。它们的参数和公式不是由本题中的第一性原理方程推导出来的，三者的比较用于评估闭合规则对饱和和输运结果的敏感性。

### 4. 准线性输运

准线性计算把线性模态结构、增长率、场响应和饱和强度组合成平均输运通量。抽象地说，对某个波数 $k$ 和模态 $m$，输运量可写成

$$
\mathcal{F}_{q,s}(k,m)
\sim
P_{km}\,W_{q,s}(k,m),
$$

其中 $P_{km}$ 是 SAT 分支给出的饱和强度，$W_{q,s}$ 是输入的准线性响应权重，$q$ 表示粒子、能量、动量或能量交换通道，$s$ 表示电子或氘。程序保留响应的符号，因此得到的通量可以为正，也可以为负；不能把所有通量取绝对值后再积分。

本题输出的通量包括粒子通量、能量通量、环向动量通量、平行动量通量和能量交换通量，并区分静电、平行矢势和平行磁压缩三个场通道。它们属于准线性响应的加权结果，不是由未提供的分布函数矩算子重新计算的通量。

### 5. 多尺度与环形几何

输入波数覆盖离子尺度和电子尺度。模型以 $k_y\rho_s$ 表示波数，并在 $k_T=1/\rho_{\rm ion}$ 附近连接低尺度和高尺度分支。SAT3 的高尺度分支仍然是给定闭合模型的一部分，不等同于独立求解电子尺度 gyrokinetic 本征问题。

圆截面几何、磁场强度、磁力线投影、俘获率和 Hermite 网格用于构造局部波数和场权重。它们决定几何平均、$k_\perp$ 相关量以及输运投影，但本题不重建 Grad-Shafranov 平衡，也不从输入参数求新的全局磁平衡。

## 本题需要的物理知识

理解和实现本题需要以下几类知识：

1. 线性模态理论：复频率、增长率、模态峰值和波数谱；
2. 磁化等离子体基础：回旋半径、$E\times B$ 漂移、平行电磁扰动和环形磁几何；
3. 湍流饱和机制：带状流混合、剪切抑制、稳定模态耦合和经验饱和参数化；
4. 准线性理论：用线性场响应和权重估算粒子、能量及动量通量；
5. 多尺度输运：离子尺度与电子尺度的分支连接、波数区间加权和对数积分；
6. 数值实现：有限网格、Hermite 求积、分段函数、解析区间积分以及有符号量的保留。

这些知识用于理解题目给定的闭合和检查输出，不意味着程序已经包含完整的非线性 gyrokinetic 求解器。



## SAT1、SAT2、SAT3 的含义

这里的 SAT 是 saturation rule 的缩写，表示三种预先规定的经验饱和闭合。SAT1、SAT2、SAT3 是分支名称，不表示三次迭代、三阶近似或三个独立的本征问题。三种规则都使用同一组给定的首遍/第二遍增长谱、准线性响应表和几何输入；它们的区别在于如何把增长率、剪切位移和响应权重转换为饱和场强及输运量。

- **SAT1：单尺度饱和闭合。** 以首遍峰和 s-alpha 几何为基础，使用 $w=k$、$h=k_{x,e}$ 的谱位移，并按 SAT1 的抑制参数计算第二遍饱和强度。SAT1 会对时间抑制后的增长率重新搜索峰值，因此最终的 $k_{\max}$、$v_{zf}$ 和 `jmax` 可能与首遍不同。
- **SAT2：带低/高波数延拓的饱和闭合。** 它使用几何给出的 $k_{\rm cut}$、$G_q$ 和 $w(k)$，在低波数区和高波数区采用不同的增长率表达式，再对指定的高波数节点执行解析加权平均。SAT2 保留首遍的离散 `jmax` 和 $k_{\max}$，但会按第二遍抑制率更新 $v_{zf}$。
- **SAT3：带尺度连接和模态权重的饱和闭合。** 它在 SAT2 的低/高波数结构上增加 $k_T$ 处的连接，使用第二遍静电能量权重插值得到模态参数 $x_m$，再计算低尺度、过渡区和高尺度的场强。SAT3 还对粒子、能量和其它响应使用不同的 QLA 权重。

因此，SAT1/2/3 的比较是对三种经验闭合规则的敏感性比较。它不能说明哪一种规则由本题之外的动力学方程唯一推出；本题只要求在给定响应和固定参数下忠实执行这三个分支。

## 归一化、物种与情景

所有量使用固定的 $a$、$c_s=\sqrt{T_e/m_D}$、$B_{\rm unit}$、$n_e$、$T_e$ 和 $m_D$ 归一化。波数、增长率和剪切分别表示为

$$
k_y\equiv k_y\rho_s,
\qquad
\gamma\equiv\gamma a/c_s,
\qquad
\gamma_E\equiv\gamma_E a/c_s.
$$

峰参数 $v_{zf}$ 定义为

$$
v_{zf}=\frac{\gamma}{k_y}.
$$

它是饱和模型中的无量纲混合尺度，不能直接解释为 SI 单位的带状流速。

物种顺序固定为电子、氘。两种温度、氘质量和密度均取 1，电子质量为 $1/3670$，电荷为 $-1/+1$，并有

$$
\rho_{\rm ion}=\frac{\sqrt{m_iT_i}}{Z_i}=1,
\qquad
v_i=\sqrt{T_i/m_i}.
$$

主输入给出 12 个 $k_y$、两个模态、首遍和第二遍增长率、各 $k_y$ 的高斯角宽、全部响应权重以及 10 个独立情景。情景包括 SAT1、SAT2、SAT3 在剪切 $-0.3$、$0$、$+0.3$ 下的结果，以及 SAT3 零剪切的中间权重比情景。

默认情况下，第 1 模的电子/离子静电能量权重比小于 0.8，第 2 模的该比值大于 1。附加情景把两个比值分别设置为 0.90 和 0.95，只替换公开表中的电子静电能量权重，离子权重和其它权重保持不变。`inputs.json` 中的表和情景定义就是全部科学输入，不读取旧数值结果。

## 原生执行顺序

每个情景按以下顺序运行：

1. 初始化原生 Hermite 网格和普通圆截面几何。
2. 调用 `get_zonal_mixing`，求首遍低波数峰。
3. 对每个 $k_y$，用首遍参考增长率和给定剪切调用 `get_xgrid_functions`、`xgrid_functions_sa` 和 `get_ft_sa`。
4. 填入公开的第二遍响应表。
5. 令 `jmax` 为正值，调用 `get_multiscale_spectrum` 的第二遍分支。

零剪切情景仍按同一流程处理。第二遍响应不会被解释为传输驱动器自行生成的本征谱。

## 首遍低波数峰

固定

$$
\alpha_{zf}=+1,
\qquad
n_{ky}=n_{\rm mix}=12,
\qquad
k_{\rm cut}=0.8/\rho_{\rm ion}.
$$

SAT2/3 再乘几何因子 `grad_r0=1`。在满足 $j=1,\ldots,n_{ky}-1$ 且 $k_{y,j}\le k_{\rm cut}$ 的节点中，严格比较首遍第 1 模的

$$
\frac{\gamma_j}{k_{y,j}}.
$$

保留最大值对应的 1 起始离散索引 `jmax`。若值相同，保留先出现的节点。输入增长率为正，因此不会出现全稳定选择。

若 `jmax` 不是第一个或最后一个合格节点，令

$$
k_-=k_{y,j_{\max}-1},
\qquad
k_+=k_{y,j_{\max}+1},
\qquad
D=k_+-k_-,
$$

$$
u=\frac{k_{y,j_{\max}}-k_-}{D},
\qquad
f_0,f_1,f_2=\left.\frac{\gamma}{k_y}\right|_{k_-,k_{y,j_{\max}},k_+}.
$$

二次式 $F(t)=A+Bt+Ct^2$ 的系数为

$$
A=f_0,
\qquad
B=\frac{f_1-f_0(1-u^2)-f_2u^2}{u-u^2},
\qquad
C=f_2-f_0-B.
$$

若 $f_0\ge f_1$，取左节点；否则求 $t_*=-B/(2C)$。当 $t_*$ 不在 $[0,1]$ 内时取对应端点，位于区间内时取顶点。峰值为

$$
k_{\max}=k_-+Dt_*,
\qquad
v_{zf}=F(t_*).
$$

边界最大值直接取节点值。离散 `jmax` 始终保留原搜索索引，不能用细化后的浮点 `kmax` 重新选择索引。首遍峰三元组是正式输出。

## 圆截面几何与剪切位移

固定几何和控制参数为

$$
r=0.5,
\quad R=3,
\quad q=2,
\quad s=1,
\quad \alpha=\theta_0=x_{\rm well}=0,
$$

$$
f=R B_t/B_{\rm unit}=3,
\quad \operatorname{sign}B_t=\operatorname{sign}I_t=+1,
\quad \beta_e=0.004,
$$

$$
\operatorname{Debye}=0,
\quad b_{\rm model}=2,
\quad ft_{\rm model}=0,
\quad \theta_{\rm trapped}=0.7,
\quad ft_{\min}=0.01.
$$

先在 `gamma_reference=0` 下调用同一个几何入口，初始化饱和因子，再求首遍峰。不能使用未初始化的几何输出。

`nxgrid=16` 生成 31 个物理学 Hermite 多项式 $H_{31}$ 的对称根，并将中心点强制设为 0。Newton 网格使用容差 $3\times10^{-14}$，最多迭代 100 次；`gauher/gauss_hermite` 必须完整执行，`nbasis=4`。对每个 $k_y$，使用输入角宽 `width`：

$$
\theta=\operatorname{width}\,x,
\qquad
\epsilon=r/R,
\qquad
R_x=1+\epsilon\cos\theta,
\qquad
B_x=1/R_x.
$$

令

$$
G=\alpha_e\gamma_E,
\qquad
\alpha_e=1,
\qquad
\alpha_{\rm quench}=0.
$$

只有参考首模增长率 `gref` 非零时才启用位移；本题输入均为正。定义

$$
k_{y,i}=k_y\frac{v_i m_i}{|Z_i|},
\qquad
w_E=\min(k_{y,i}/0.3,1)\frac{G}{g_{\rm ref}}.
$$

在 GYRO 单位下，SAT1 的位移为

$$
k_{x,e}=-\left[0.53\frac{G}{g_{\rm ref}}+0.25w_E\tanh\left((0.69w_E)^6\right)\right],
\qquad |k_{x,e}|\le1.45.
$$

SAT2/3 的位移为

$$
k_{x,e}=-0.32\left(\frac{k_y}{k_{\max}}\right)^{0.3}
\frac{G}{k_yv_{zf}},
\qquad |k_{\max}v_{zf}G|>10^{-8},
$$

否则 $k_{x,e}=0$，并将 $|k_{x,e}|$ 限制为 1.6。限幅保留原符号。原生谱位移为 `kxe`，几何中的位移为

$$
k_{x0}=\operatorname{sign}B_t\,k_{x,e}.
$$

位移参考增长率来自首遍；后续幅度抑制使用第二遍增长率，二者不能混用。

网格上的几何量为

$$
k_{xx}=\operatorname{sign}B_t[-s(\theta-\theta_0)+\alpha\sin\theta-k_{x0}],
$$

$$
w_{dx}=\frac{-x_{\rm well}\min(1,\alpha)+\cos\theta-\sin\theta\,k_{xx}}{R_x},
\quad b_{0x}=1+k_{xx}^2,
\quad b_{2x}=B_x^2,
\quad w_{dpx}=0.
$$

投影量为

$$
c_{x,\mathrm{tor},\parallel}=R R_x\operatorname{sign}B_t,
\qquad
c_{x,\mathrm{tor},\perp}=-r/q,
\qquad
c_{x,\parallel,\parallel}=B_x.
$$

这 8 个几何数组都必须输出，不能用外部给定的最终位移替代几何入口。

## 有效俘获率与几何平均

使用 `ft_model=0` 的原生俘获率。定义

$$
\theta_{\max}=\min\left(\theta_{\rm trapped}\,\operatorname{width}\,\frac{\pi}{\sqrt2},\pi\right),
$$

$$
B_{\max}=\frac{1}{1+\epsilon\cos\theta_{\max}},
\qquad
B_{\min}=\frac{1}{1+\epsilon}.
$$

对 $i=1,\ldots,n_x$，令

$$
u_i=\cos\frac{\pi(2i-1)}{2n_x},
\qquad
\theta_i=u_i\theta_{\max},
\qquad
b_i=\frac{1}{1+\epsilon\cos\theta_i},
$$

$$
w_i=\sqrt{1-u_i^2}\exp[-(\theta_i/\operatorname{width})^2],
\qquad
f_t=\frac{\sum_iw_i\sqrt{1-b_i/B_{\max}}}{\sum_iw_i}.
$$

每个物种的俘获率为 $\max(f_t,0.01)$。不能用单一的 $\sqrt{1-B_{\min}/B_{\max}}$ 替代上式。

原生几何还在 $2n_x$ 个等角区间上用端点梯形法计算圆截面平均，步长为 $2\pi/(2n_x)$，保留周期末端。输出标量满足

$$
R_2=R^2\langle R_x^2\rangle,
\quad
B_2=\langle1/R_x^2\rangle,
\quad
B_{\rm ave}=\langle1/R_x\rangle,
\quad
B_{t,\rm ave}=\langle R_x\rangle,
\quad
RB_t=R.
$$

另外，`grad_r=kx_geo0=SAT_geo0/1/2=grad_r0=1`，并有

$$
B_{p0}=\frac{r}{q(R+r)},
\qquad
B_{t0}=B_{\rm geo0}=f/R=1.
$$

输出的 17 个几何标量中，`Btave` 表示 $\langle R_x\rangle$，不能当作 `Bave`。本题只使用这些几何量进行经验闭合，不重建 Grad-Shafranov 平衡。

## 第二遍多尺度饱和

下面的 $g_j$ 是第二遍第 1 模增长率，$g_{jm}$ 是第二遍第 $m$ 模增长率，$k_j$ 表示 $k_y$。所有增长率除数采用 $10^{-10}$ 阈值。初始场和通量清零，但调用前必须填入全部 QL 响应表。正 `jmax` 选择第二遍分支；不提供 `gamma_kymix`、饱和幅度或最终输运的捷径表。

固定

$$
\mathrm{rlnp\_cutoff}=0,
\quad d\ln p/dr=12,
\quad \mathrm{etg\_factor}=+1,
\quad \mathrm{etg\_stiff}=1,
$$

$$
\mathrm{USE\_MIX}=\mathrm{true},
\quad \mathrm{USE\_SUB1}=\mathrm{false},
\quad \mathrm{expsub}=2,
\quad c_{ky}=3.
$$

SAT1 在 s-alpha 几何下使用

$$
c_{\rm norm}=14.63,
\quad c_{z1}=0.90|\alpha_{zf}|,
\quad c_{z2}=|\alpha_{zf}|,
\quad \mathrm{measure}=\sqrt{T_em_i}=1,
\quad k_{ETG}=1.05/\rho_{\rm ion}.
$$

不能把 Miller 的 $c_{z1}=0.48$ 或其它拟合值带入本题。

SAT2/3 使用

$$
b_0=0.76,
\quad b_1=1.22,
\quad b_2=3.55,
\quad b_3=1,
$$

$$
d_1=\frac{(B_{t0}/B_{\rm geo0})^4}{\mathrm{grad\_r0}}=1,
\quad G_q=B_{\rm geo0}/\mathrm{grad\_r0}=1,
\quad d_2=b_3/G_q^2=1,
$$

$$
c_{\rm norm}=b_2\frac{12}{d\ln p/dr}=3.55,
\quad k_{\rm cut}=0.76k_{\max},
\quad c_{z1}=0,
\quad c_{z2}=1.05|\alpha_{zf}|,
\quad \mathrm{measure}=1/k_{\max},
\quad k_{ETG}=1000.
$$

这些量使用原生几何输出，不引入 SAT0 或 Waltz 替代模型。

对每个 $k_y$，SAT1 取 $w=k$、$h=k_{x,e}$。SAT2/3 取

$$
w=\begin{cases}
k_{\rm cut}/\mathrm{grad\_r0},&k<k_{\rm cut},\
k_{\rm cut}/\mathrm{grad\_r0}+b_1(k-k_{\rm cut})G_q,&k\ge k_{\rm cut},
\end{cases}
\qquad
h=k_{x,e}k/w.
$$

时间抑制为

$$
g_{\rm net,j}=\frac{g_j}{1+|a_xh|^p}.
$$

SAT1 使用 $(a_x,p,a_y)=(1.15,4,0.56)$，SAT2/3 使用 $(1.21,2,1)$。

SAT1 对 $g_{\rm net}$ 重新执行同一个峰搜索，因此最终 $v_{zf}$、$k_{\max}$ 和 `jmax` 可以与首遍不同。SAT2/3 保留首遍 $k_{\max}$ 和离散 `jmax`，保存 $v_{zf,fp}$，再令

$$
v_{zf}=v_{zf,fp}\frac{g_{\rm net}(j_{\max})}{\max(g(j_{\max}),10^{-10})}.
$$

最终峰三元组也必须输出。不能因剪切较大而修改输入或控制参数。

令

$$
g_m=v_{zf}k_{\max}.
$$

SAT1 的初始带状流增长模型为

$$
g_{\rm mix}(k)=
\begin{cases}
\max[g_{\rm net}-c_{z1}(k_{\max}-k)v_{zf},0],&k<k_{\max},\
c_{z2}g_m+\max[g_{\rm net}-c_{z2}v_{zf}k,0],&k\ge k_{\max}.
\end{cases}
$$

SAT2/3 在 $k<k_{\max}$ 时使用 $g_{\rm net}$，否则使用

$$
g_m+\max[g_{\rm net}-c_{z2}v_{zf}k,0].
$$

对离散 $j=j_{\max}+2,\ldots,n_{ky}$，用同一完整区间做解析加权平均。积分下限为 $k_{y,j_{\max}+1}$，上限为最后一个 $k_y$ 节点。对分段线性增长率使用

$$
W(k;k_0)=\frac{\sqrt3\,k_0^2}{k_0^2+3(k-k_0)^2},
\qquad
g_{\rm mix}(k_0)=\frac{\int g(k)W(k;k_0)\,dk}{\int W(k;k_0)\,dk}.
$$

不能只取相邻两个节点，也不能把积分延拓到 0 或无穷。原生解析积分使用

$$
M_1=k_0\,\Delta\,\arctan\left[\sqrt3\left(k/k_0-1\right)\right],
$$

$$
M_2=k_0M_1+\frac{k_0^2}{2\sqrt3}\,\Delta\ln\left[3(k-k_0)^2+k_0^2\right].
$$

若区间斜率为 $D$，分子为

$$
(g_{\rm left}-k_{\rm left}D)M_1+DM_2.
$$

对每个模态，若 $g_j\le10^{-10}$，取 $g_{\rm eff}=0$；否则

$$
g_{\rm eff}=g_{\rm mix}(g_{jm}/g_j)^2.
$$

当 $k>k_{ETG}$ 时，再乘以 $\sqrt{k/k_{ETG}}$。势强度为

$$
P_{jm}=\mathrm{measure}\,c_{\rm norm}
\left[\frac{g_{\rm eff}}{wk(1+a_yh^2)}\right]^2.
$$

本题固定 GYRO 单位，不能再乘非 GYRO 的 `sat_geo_factor`，也不能按瞬时最大幅度或物种密度重新归一。

## SAT3 的低/高尺度连接与模态权重

SAT3 先使用时间抑制前的首遍峰，定义

$$
K=k_{\max},
\quad G_m=v_{zf,fp}K,
\quad K_{\min}=0.685K,
\quad A=-1/(2K_{\min}),
\quad C=-0.751K,
$$

$$
k_T=1/\rho_{\rm ion},
\quad k_0=0.6K_{\min},
\quad k_P=2K_{\min},
\quad c=-2.42,
\quad \mathrm{scal}=0.82.
$$

对每个模态，使用公开第二遍静电能量权重比

$$
r(k)=\left|\frac{W_{e,E,ES}}{\sum_iW_{i,E,ES}}\right|.
$$

在连续 $K$ 处对实际 $k_y$ 节点线性插值，得到 $x_m$。若 $K$ 不大于第一个 $k_y$ 节点，或包围节点的离子分母为零，原生取 $x_m=0.5$。本题分母均为正，不能用 ITG/TEM 标签替代该计算。

定义 $T(x;y_I,y_T)$：当 $x<0.8$ 时取 $y_I$，当 $x>1$ 时取 $y_T$，中间区间线性过渡。令

$$
Y_I=3.3G_m^2/K^5,
\qquad
Y_{TEM}=12.7G_m^2/K^4,
\qquad
Y_m=T(x_m;Y_I,Y_{TEM}).
$$

$x_m$ 由给定 QL 表决定，不能由增长率排序或微小权重推断。

原生代码同时重建未抑制的第一遍模型 $g_{fp}$：当 $k<K$ 时取第二遍原始 $g_j$，当 $k\ge K$ 时取

$$
g_{fp}=v_{zf,fp}K+\max[g_j-c_{z2}v_{zf,fp}k,0].
$$

该模型使用同一高 $k_y$ 解析混合。$v_{zf}=0$ 时按原生分支使用当前 $g_m=0$ 和同一最大值项。不能用这条诊断模型重建线性本征问题。定义

$$
F(k)=\frac{(g_{\rm mix}/g_{fp})^2}{(1+a_yh^2)^2},
\qquad
g_{fp}=0\Rightarrow F=0.
$$

由于网格跨过 $k_T$，原生在包围 $k_T$ 的两个节点 $l$ 上计算不含模态和 ExB 因子的 SAT2 连接势

$$
D_l=\mathrm{scal}\,\mathrm{measure}\,c_{\rm norm}
\left[\frac{g_{fp}(l)}{w_lk_l}\right]^2.
$$

对 $g_l\le10^{-10}$ 取 $D_l=0$，再线性插值得到各模态共用的 $Y_{conn}$。这不是外部给定的电子尺度边界强度。

若 $g_j\le10^{-10}$，取 $P=0$。其余分支为

$$
k\le k_T\ \text{且}\ k_P\ge k_T:\qquad P=0.
$$

$$
k\le k_P\ \text{且}\ k_P<k_T:\qquad
S(k)=\frac{Ak^2+k+C}{Ak_0^2+k_0+C},
$$

$$
P=Y_mS(k)^cF(k)(g_{jm}/g_j)^4.
$$

当 $k_P<k\le k_T$ 时，若 $Y_{conn}=0$，原生取 $10^{-5}$，并令

$$
d=\frac{(Y_m/Y_{conn})^{1/|c|}-[Ak_P^2+k_P+C-(k_P-k_T)(2Ak_P+1)]/(Ak_0^2+k_0+C)}{(k_P-k_T)^2},
$$

$$
e=-2dk_P+\frac{2Ak_P+1}{Ak_0^2+k_0+C},
\qquad
f=(Y_m/Y_{conn})^{1/|c|}-ek_T-dk_T^2,
$$

$$
S(k)=dk^2+ek+f,
\qquad
P=Y_mS(k)^cF(k)(g_{jm}/g_j)^4.
$$

当 $k>k_T$ 时，

$$
P=\mathrm{scal}\,\mathrm{measure}\,c_{\rm norm}
\left[\frac{g_{\rm mix}(g_{jm}/g_j)^2}{wk(1+a_yh^2)}\right]^2.
$$

若 $k>1000$，再令 $g_{\rm mix}\leftarrow g_{\rm mix}\sqrt{k/1000}$。本题所有 $k_y<1000$，但高于 $k_T$ 的电子尺度分支仍然存在。若原生幂、分母或表访问产生非有限值或失败，必须保留失败，不能用绝对值、钳制、零参考或替代算法强行通过。

SAT3 的模态权重为

$$
QLA_{particle}=2T(x;1.1,0.6),
\qquad
QLA_{energy}=2T(x;0.75,0.6),
\qquad
QLA_{other}=1.6.
$$

这里的因子 2 是原生实场对称因子，积分层不能再次乘 2。SAT1/2 的三个乘子均为 1。场谱四个分量按原生顺序为

$$
[P,P,QL_{A\parallel}^2P,QL_{B\parallel}^2P].
$$

前两个分量在本规则中相等，不能把第一个标为输入 `QL_field[1]*P`。四个给定的无量纲二次矩响应 $N,T,U,Q$ 逐一乘以 $P$；这些响应不用于反推未提供的矩算子。所有 $5$ 个量、$2$ 个物种和 $3$ 个场通道的有符号 QL 通量都必须乘以 $P$ 并输出，不能删除负号，也不能把场通道重新解释为某一种单独应力机制。

## 谱积分、单位与输出

先在每个 $k_y$ 上相加两个模态，保留物种、场通道和五个量的轴。第一个区间的贡献为 $k_1F_1$。对于相邻节点 $k_0<k_1$，令

$$
D=\frac{\log(k_1/k_0)}{k_1-k_0},
\qquad
a=k_0(k_1D-1),
\qquad
b=k_1(1-k_0D),
$$

区间贡献为

$$
aF_0+bF_1.
$$

逐区间相加得到总量。保留每个有符号区间贡献和总量，不能只输出正热通量。该积分规则来自同一原始传输驱动器；本题只在 wrapper 中逐项实现和检查，不把它描述为自洽本征谱求解。

通量统一使用 GB 单位：

$$
\Gamma_N=n_ec_s(\rho_s/a)^2,
\quad
\Gamma_E=n_eT_ec_s(\rho_s/a)^2,
$$

$$
\Pi_{\rm tor}=n_eT_ea(\rho_s/a)^2,
\quad
\Pi_{\parallel}=n_eT_e(\rho_s/a)^2,
\quad
Q_{\rm exch}=n_eT_ec_s/a(\rho_s/a)^2.
$$

环向投影含 $R/a$ 或 $r/a$ 力臂，平行投影的 $B_x$ 不含长度因子。题目没有给出物理 $a$、$n_e$ 和 $T_e$，因此不输出 SI 输运。三个场通道的权重来自输入表；结果只表示对这组给定响应的经验闭合，不表示某个动力学模型已经生成了电磁响应。

正式输出包括首遍和最终峰、原生 `kxe` 与几何 `kx0`、31 点 Hermite 网格、每个 $k_y$ 的 17 个几何标量和 $31\times8$ 几何数组，以及以下谱数组：

$$
12\times2\times4\ \text{场谱},
\quad
12\times2\times2\times4\ \text{矩强度},
$$

$$
12\times2\times2\times3\times5\ \text{有符号输运谱},
\quad
12\times2\times3\times5\ \text{区间贡献},
\quad
2\times3\times5\ \text{总量}.
$$

各列顺序见 `output-spec.json`。输入轴和全部情景不可省略，布尔值不能冒充数值。

重放容差在运行前固定为 `rtol=1e-10`、`atol=1e-12`，参考零值保持精确为零。比较范围仅限同一组给定响应、有限网格和原生闭合流程，不能据此接受连续极限、经验模型适用性、实验预测、物理参数到响应的矩/FLR/应力算子，或真实移位本征谱的自洽性。
