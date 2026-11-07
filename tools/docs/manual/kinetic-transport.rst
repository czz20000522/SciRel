分布函数与中性粒子输运：从速度网格到通量诊断
================================================

这一章回答一个具体问题：**给定一个中性分子的速度分布，怎样把它放到离散速度网格上，算出密度、流速、温度和热通量，再让同一份分布在空间中被碰撞衰减，最后读出通量？**

我们沿着一条连续的路径走：先建立轴对称圆柱速度网格和积分测度，再在网格上放一个平移 Maxwellian 并做矩归约，然后把碰撞损失频率组装进一维上风推进系数，传播一代首飞中性粒子，最后用终态归约得到通量、压强、温度和热通量。每一步都给出实际运行输出，并说明哪些结论不能从这一步推出来。

.. note::

   本章是教程，不是合同摘要。每个函数的完整签名、参数单位、失败行为和适用范围在章末链接的 API 参考页；教程里的代码只调用 SciRel 的公开函数，数字都来自当前 ``.venv`` 的实际执行。

模型与约定
----------

空间是一维的，记为 ``x``，单位 m。速度空间是轴对称的二维柱坐标：径向速度 ``vr >= 0``，轴向速度 ``vx`` 可正可负。分布函数写成 ``f(vr, vx, x)``，速度空间积分用圆柱测度

.. code-block:: text

   dV_v = 2*pi*vr*dvr*dvx

离散后，每个速度单元的体积权重是 ``2*pi*vr*dvr*dvx`` 的单元积分。所有“密度”“通量”都是对这个测度求和，而不是对 ``(vr, vx)`` 的普通矩形网格求和。

本章把 H2 分子当作一个质量为 2 个氢质量单位的粒子来处理。因此：

- Maxwellian 初值入口用 ``mass_amu=2.0``、``molecule_count=1``；
- 矩归约入口用 ``isotope_mass_amu=2.0``、``molecularity=1``；
- 终态归约入口用 ``mass_ratio=1.0`` （该入口内部按 ``2 * mass_ratio * m_H`` 取分子质量）。

这不是唯一可能的记账方式，但这一整套参数必须成套使用。后面“易错点”会展示混用另一套因子时数字怎样变化。

速度网格的节点用归一化速度表示，单位是热速度

.. code-block:: text

   Vth = sqrt(2*e*Tnorm / (m_amu*m_H))

其中 ``Tnorm`` 是网格的归一化温度（eV）。本章始终使用无量纲速度 ``u=v/Vth``：空间推进仍传入网格的 ``vr``、``vx``，碰撞系数则为 ``alpha=nu/Vth``，单位 m^-1。物理频率 ``nu`` （s^-1）必须除以同一个 ``Vth``；源项同样使用 ``Q/Vth`` （F/m），其中 F 对归一化速度体积积分后给出数密度。只有显式右端组装或物理矩诊断才乘回 ``Vth``。Maxwellian 初值的平移参数是 m/s，入口会在内部除以 ``Vth``。

速度网格：节点、测度与体积
---------------------------

网格生成和积分权重是两个不同步骤。``create_adaptive_neutral_velocity_mesh`` 根据离子温度和请求能量生成径向半网格 ``vr``，再镜像出对称的 ``vx``。温度展宽很小时使用 ``[0, 3.5]`` 上的均匀基网格；展宽较大时使用二次拉伸。请求的正能量会被插入为精确节点，而 ``Tnorm`` 是“被选中的温度/能量群体”的均值。

``make_cylindrical_velocity_quadrature`` 只接收已经给定的 ``vr``、``vx``，构造半格面、环形径向测度、单元体积和 ghost 差分系数。它不做网格自适应，也不做单位换算。单元体积是

.. code-block:: text

   radial_measure[i] = pi*(r_right[i]^2 - r_left[i]^2)
   volume[i,j] = radial_measure[i] * dvx[j]

.. code-block:: python

   import numpy as np
   from scirel.kinetic import (
       create_adaptive_neutral_velocity_mesh,
       make_cylindrical_velocity_quadrature,
   )

   vx, vr, tnorm, ix, ir = create_adaptive_neutral_velocity_mesh(
       16, (1.0, 1.05), requested_energy_ev=(1.1,)
   )
   quad = make_cylindrical_velocity_quadrature(vr=vr, vx=vx)

   print(f"nvr = {vr.size}, nvx = {vx.size}, Tnorm = {tnorm:.3f} eV")
   print(f"vr[3:6] = {np.array2string(vr[3:6], precision=6)}")
   print(f"vr[ir] = {vr[ir]:.6f}, ix = {ix}, ir = {ir}")
   print(f"sum(volume) = {quad['volume'].sum():.6f}")
   print(f"outer face = {quad['vr_right'][-1]:.6f}")
   print(f"2*pi*R^3 = {2 * np.pi * quad['vr_right'][-1] ** 3:.6f}")
   print(f"positive first index = {quad['positive_vx_first_index']}")

实际输出：

.. code-block:: text

   nvr = 17, nvx = 34, Tnorm = 1.050 eV
   vr[3:6] = [0.875    1.023533 1.09375 ]
   vr[ir] = 1.023533, ix = [12 21], ir = 4
   sum(volume) = 295.444484
   outer face = 3.609375
   2*pi*R^3 = 295.444484
   positive first index = 17

``nv=16`` 的基网格在 ``[0, 3.5]`` 上有 17 个节点；去掉 0 后径向有 16 个半节点，镜像后得到 32 个轴向节点。插入 1.1 eV 对应的节点后，径向变成 17 个，轴向 34 个。``Tnorm = 1.050`` 是 ``(1.0 + 1.05 + 1.1) / 3``，说明请求能量也进入了归一化群体，尽管温度展宽仍小到足以走均匀分支。``vr[4] = 1.023533`` 是 ``sqrt(1.1 / 1.05)``，不是基网格节点。

体积和 ``295.444484`` 等于 ``2*pi*R^3``，其中 ``R = 3.609375`` 是最外层 ghost 面的位置。这是半格外推约定下的体积闭合：所有速度单元正好铺满半径 ``R``、轴向半长 ``R`` 的圆柱。它验证的是“测度铺满域”，不是“这个网格能准确积分你的分布”。

这一节不能推出什么
~~~~~~~~~~~~~~~~~~~~

- 体积和相等只说明单元划分闭合；它不能证明 17×34 的网格对某个分布足够细。冷束、高能尾或强各向异性分布可能需要更多节点。
- 最外层 ghost 面用的是“镜像最后一个节点再取半格”的约定。换一套单元面约定，不能直接沿用这里的 ``radial_measure``、``dvx`` 和 ``volume``。
- 网格节点是无量纲速度；输运系数使用 ``nu/Vth`` （m^-1），不能直接传入 s^-1 的物理碰撞频率。
- 请求能量会改变 ``Tnorm``，也可能把均匀分支切换成拉伸分支。不能假设“加一个能量节点”只增加一个节点而不改变其它网格位置。

Maxwellian 初值：归一化与矩
----------------------------

初值入口在给定网格上构造一个平移 Maxwellian：

.. code-block:: text

   f(vr,vx) proportional to exp[-(vr^2 + (vx - s/Vth)^2) * molecule_count * Tnorm / T]
   sum(volume * f) = 1

它只负责构造归一化初值，不做后续的矩补偿。轴向平移 ``s`` 用 m/s 给出，内部除以热速度；温度 ``T`` 是每个平移层的参数。

矩归约入口接收 ``f``、速度轴和同一个 ``volume``，返回密度、轴向通量、流速、压强、温度、对角应力和随机热通量。密度是 ``sum(volume * f)``，轴向通量是 ``Vth * sum(volume * vx * f)``，流速是通量除以密度，温度是压强除以密度。

.. code-block:: python

   from scirel.kinetic import (
       build_shifted_maxwellian_seed,
       reduce_axisymmetric_neutral_moments,
   )

   seed = build_shifted_maxwellian_seed(
       vr=vr, vx=vx, tnorm_ev=tnorm,
       shifted_vx_m_s=np.array([3000.0]),
       temperature_ev=np.array([2.0]),
       mass_amu=2.0, molecule_count=1,
       cylindrical_volume=quad["volume"],
   )
   f = seed["distribution"][:, :, 0]
   mom = reduce_axisymmetric_neutral_moments(
       f[:, :, None], vx, vr, quad["volume"],
       normalization_temperature_ev=tnorm,
       isotope_mass_amu=2.0, molecularity=1,
   )

   print(f"thermal speed = {seed['thermal_speed_m_s']:.1f} m/s")
   print(f"shape = {f.shape}, integral = {np.sum(quad['volume'] * f):.12f}")
   print(f"density = {mom['density_m3'][0]:.6f} m^-3")
   print(f"flow = {mom['axial_velocity_m_s'][0]:.1f} m/s (input 3000)")
   print(f"T = {mom['temperature_ev'][0]:.4f} eV (input 2)")
   print(f"p = {mom['pressure_ev_m3'][0]:.4f} eV m^-3")
   print(f"stress_zz is stress_yy: {np.array_equal(mom['stress_zz_ev_m3'], mom['stress_yy_ev_m3'])}")

实际输出：

.. code-block:: text

   thermal speed = 10028.8 m/s
   shape = (17, 34), integral = 1.000000000000
   density = 1.000000 m^-3
   flow = 3009.1 m/s (input 3000)
   T = 1.9888 eV (input 2)
   p = 1.9888 eV m^-3
   stress_zz is stress_yy: True

``integral = 1`` 是入口自己做的体积加权归一化，密度为 1 是同一事实的另一种读法。流速 3009.1 m/s 比输入的 3000 高 0.3%，温度 1.9888 eV 比 2 eV 低 0.56%。这些差异来自有限网格：速度盒只到 ``±3.5 Vth``，径向只有 17 个节点，分布的高能尾被截断，离散求和也不是精确积分。它们不是求解器容差，也不是物理上的“流速偏移”。

``p = 1.9888 eV m^-3`` 与 ``n*T = 1 * 1.9888`` 一致，因为温度在这里就是压强除以密度。``stress_zz`` 是 ``stress_yy`` 的独立副本，这是该关系声明的圆柱对称识别；它不代表存在一个独立的 ``zz`` 应力计算。

把同一套构造在更细的网格上重复，可以直接看到差异在缩小：

.. code-block:: python

   for nv_check in (8, 16, 32):
       vx_c, vr_c, tn_c, _, _ = create_adaptive_neutral_velocity_mesh(
           nv_check, (1.0, 1.05), requested_energy_ev=(1.1,)
       )
       quad_c = make_cylindrical_velocity_quadrature(vr=vr_c, vx=vx_c)
       seed_c = build_shifted_maxwellian_seed(
           vr=vr_c, vx=vx_c, tnorm_ev=tn_c,
           shifted_vx_m_s=np.array([3000.0]),
           temperature_ev=np.array([2.0]),
           mass_amu=2.0, molecule_count=1,
           cylindrical_volume=quad_c["volume"],
       )
       mom_c = reduce_axisymmetric_neutral_moments(
           seed_c["distribution"], vx_c, vr_c, quad_c["volume"],
           normalization_temperature_ev=tn_c,
           isotope_mass_amu=2.0, molecularity=1,
       )
       print(
           f"nv={nv_check:2d}: u={mom_c['axial_velocity_m_s'][0]:.1f} m/s, "
           f"T={mom_c['temperature_ev'][0]:.4f} eV"
       )

实际输出：

.. code-block:: text

   nv= 8: u=3149.2 m/s, T=2.0193 eV
   nv=16: u=3009.1 m/s, T=1.9888 eV
   nv=32: u=2989.3 m/s, T=1.9844 eV

``nv=8`` 时流速偏高 5%，``nv=32`` 时降到约 -0.4%。这说明上一段的 0.3% 主要是离散化误差；但它仍然不是误差上界，也不能证明 ``nv=32`` 对其它分布足够。

这一节不能推出什么
~~~~~~~~~~~~~~~~~~~~

- 初值入口返回的是“未做矩补偿的归一化种子”，不是任何具体装置的物理分布。它的归一化和 ``Tnorm`` 都是人为约定。
- 流速和温度与输入值的小差异是离散化结果；换网格会变。不能把 3009.1 m/s 当成该分布的“真实流速”，也不能把 1.9888 eV 当成模型误差估计。
- 网格外的分布尾部没有进入积分。一个在 ``|vx| > 3.5 Vth`` 有显著权重的分布，不能用这组数字外推。
- 温度是中心化二阶矩；它不等于初值入口里的 ``temperature_ev`` 参数，除非质量、分子数和归一化温度都按同一套约定匹配。混用因子会系统性地改变 ``u`` 和 ``T``。
- ``stress_zz = stress_yy`` 是该关系的声明，不是从一次矩计算中独立验证的物理结论。

归一化损失系数与上风系数
------------------------

中性粒子在空间中会因为电荷交换、弹性碰撞和有限管道壁面而损失。空间推进所用的总损失系数是物理频率除以热速度，即 ``alpha=nu/Vth`` （m^-1）：

.. code-block:: text

   alpha(vr,vx,x) = [Alpha_CX] + base_loss + Omega_EL + 2*vr/D

其中 ``vr`` 是无量纲径向速度，壁面系数 ``2*vr/D`` （m^-1）对应物理逃逸频率 ``2*vr*Vth/D`` （s^-1）。壁面项只对正的管道直径 ``D`` 生效；``D = 0`` 表示关闭壁面损失。``Alpha_CX`` 是可选通道，启用时必须显式给出同形状的非负逆长度系数。这里把人为指定的基础、弹性、CX 物理频率 1500、500、2000 s^-1 全部除以种子所用的同一个 ``Vth``。

上风系数把 ``alpha``、空间节点 ``x``、无量纲轴向速度 ``vx`` 和归一化源 ``Q/Vth`` 组装成六个场。正速度分支前向递推使用无量纲 ``Ak`` 和分布单位的 ``Fk``；负速度分支后向递推使用无量纲 ``Ck`` 和分布单位的 ``Gk``。``Bk``、``Dk`` 的单位是 m，乘散射源 F/m 后才得到分布 F。这一节只走首飞路径，源设为零。

.. code-block:: python

   from scirel.kinetic import (
       assemble_neutral_total_collision_frequency,
       assemble_neutral_upwind_transport_coefficients,
   )

   x = np.linspace(0.0, 2.0, 201)  # dx = 0.01 m
   nx = x.size
   shape = (vr.size, vx.size, nx)

   vth = seed["thermal_speed_m_s"]
   base = np.full(nx, 1500.0 / vth)
   elastic = np.full(nx, 500.0 / vth)
   diameter = np.full(nx, 0.2)
   cx = np.full(shape, 2000.0 / vth)
   alpha = assemble_neutral_total_collision_frequency(
       vr, vx, base, elastic, diameter, cx
   )

   coef = assemble_neutral_upwind_transport_coefficients(
       x, vx, alpha, np.zeros(shape)
   )

   print(f"alpha shape = {alpha.shape}")
   print(f"alpha(vr={vr[0]:.3f}, vx=+3.5) = {alpha[0, -1, 0]:.6f} m^-1")
   print(f"alpha(vr={vr[-1]:.3f}, vx=+3.5) = {alpha[-1, -1, 0]:.6f} m^-1")
   print(f"Ak(vr={vr[0]:.3f}, vx=+3.5) = {coef['Ak'][0, -1, 0]:.9f}")
   print(f"Ak(vr={vr[-1]:.3f}, vx=+3.5) = {coef['Ak'][-1, -1, 0]:.9f}")
   print(f"Ck(vr={vr[0]:.3f}, vx=-3.5) = {coef['Ck'][0, 0, 1]:.9f}")
   print(f"Fk all zero = {np.all(coef['Fk'] == 0.0)}")
   print(f"min active Ak = {coef['Ak'][:, vx > 0.0, :-1].min():.6f}")

实际输出：

.. code-block:: text

   alpha shape = (17, 34, 201)
   alpha(vr=0.219, vx=+3.5) = 2.586350 m^-1
   alpha(vr=3.500, vx=+3.5) = 35.398850 m^-1
   Ak(vr=0.219, vx=+3.5) = 0.992637632
   Ak(vr=3.500, vx=+3.5) = 0.903728842
   Ck(vr=0.219, vx=-3.5) = 0.992637632
   Fk all zero = True
   min active Ak = 0.105512

最低径向速度处 ``alpha = 2.586350 m^-1``，最高径向速度处为 ``35.398850 m^-1``。三项体碰撞合计 ``4000/Vth = 0.398850 m^-1``；壁面项 ``2*vr/D`` 随 ``vr`` 从 0.21875 增到 3.5 而从 2.1875 增到 35.0 m^-1。轴向速度不影响本例的 ``alpha``，所以 ``Ck`` 与 ``Ak`` 在镜像速度节点上相等。

在最快正速度节点，``dx*alpha/(2*u_x) = 0.003695``，所以每个 0.01 m 单元的 ``Ak = 0.992637632``。这个递推是沿速度特征线的梯形离散。对非负边界和零源，要把本例解释成非负分布，还需各活动单元的递推系数非负：正支要求 ``dx*alpha_k <= 2*u_x``，负支有对应条件。原来 0.1 m 的步长在正确归一化后的慢速度格上会使系数为负；这里细化到 0.01 m，得到最小活动 ``Ak = 0.105512``，并在下一段检查生成分布非负。这是本算例的离散可接受性检查，不是网格收敛认证。``Fk`` 全零仅表示本次数值实验没有体积源。

这一节不能推出什么
~~~~~~~~~~~~~~~~~~~~

- ``alpha`` 是外部指定的逆长度损失系数；本例没有从截面、密度和温度自洽计算碰撞。所设的物理频率及管径只是演示参数。
- 活动系数非负只说明本算例允许把递推解释成非负衰减；它不证明任意步长下的正性、精度或稳定性。
- ``D = 0`` 关闭壁面项，不表示没有壁面；``alpha`` 的形状是 ``(nvr, nvx, nx)``，但本节的 ``base``、``elastic``、``diameter`` 只随 ``x`` 变化，``cx`` 是常数场。换成随速度或空间变化的场，需要重新检查每个单元的数值。
- 系数组装本身不检查物理上的“碰撞频率是否小于 ``v/dx``”之类的分辨率条件；它只检查输入域和有限性。

首飞代际：边界注入与衰减
--------------------------

``propagate_neutral_generation`` 用上风递推推进一代中性粒子。首飞路径在 ``x=0`` 只把 ``incoming_boundary`` 的正速度分支写入初值，然后沿正速度方向前向递推：

.. code-block:: text

   g[k+1] = Ak[k]*g[k] + Fk[k]

负速度分支从右边界开始后向递推，但它的右边界初值保持为零，源项 ``Gk`` 也为零，所以整条负分支保持为零。

.. warning::

   ``first_flight`` 的 ``incoming_boundary`` 只作用于正 ``vx`` 分支；负 ``vx`` 分支不会从右边界注入边界值。若物理问题需要从两端入射，不能只调用一次首飞路径就声称双向边界都处理了。

为了让“从 ``x=0`` 入射”这个图像自洽，我们把 Maxwellian 的负速度半边置零，只保留正速度半边作为边界。这样边界的体积积分不再是 1，而是大约 0.623。

.. code-block:: python

   from scirel.kinetic import propagate_neutral_generation

   boundary = f.copy()
   boundary[:, vx < 0.0] = 0.0
   gen = propagate_neutral_generation(
       vx, coef["Ak"], coef["Bk"], coef["Fk"],
       coef["Ck"], coef["Dk"], coef["Gk"],
       generation_kind="first_flight", incoming_boundary=boundary,
   )

   assert np.all(gen >= 0.0)
   print(f"shape = {gen.shape}, finite = {np.all(np.isfinite(gen))}")
   print(f"negative-vx max = {np.abs(gen[:, vx < 0.0, :]).max():.1e}")
   for k in (0, 100, 200):
       print(f"n(x={x[k]:.1f}) = {np.sum(quad['volume'] * gen[:, :, k]):.6f} m^-3")

   j = np.argmax(vx)
   ratio = gen[0, j, :] / boundary[0, j]
   exact = np.exp(-alpha[0, j, 0] * x / vx[j])
   print(f"fastest bin ratio(2 m) = {ratio[-1]:.9f}")
   print(f"exp(-alpha*L/u_x) = {exact[-1]:.9f}")
   print(f"max relative difference = {np.max(np.abs(ratio / exact - 1.0)):.2e}")

实际输出：

.. code-block:: text

   shape = (17, 34, 201), finite = True
   negative-vx max = 0.0e+00
   n(x=0.0) = 0.622978 m^-3
   n(x=1.0) = 0.004721 m^-3
   n(x=2.0) = 0.000697 m^-3
   fastest bin ratio(2 m) = 0.228111491
   exp(-alpha*L/u_x) = 0.228113026
   max relative difference = 6.73e-06

对最快的速度格点（``vr`` 最小、``vx = +3.5``，对应物理速度 ``3.5*Vth``），递推与连续指数衰减 ``exp(-alpha*x/u_x)=exp(-nu*x/v_x)`` 的最大相对差是 ``6.73e-6``。它核对了零源、沿空间恒定系数下的一条特征线上的梯形递推；它不替代整条分布或网格收敛检查。

积分密度从 ``0.622978`` 降到 ``0.000697``，比值约 ``0.00112``；它小于最快格点的 ``0.228``，因为低轴向速度和较高径向壁面损失的粒子被优先损失。经过 2 m 后，分布已不再是原来的 Maxwellian。这个积分密度比值不能用来反推唯一的 ``alpha``。

这一节不能推出什么
~~~~~~~~~~~~~~~~~~~~

- 这不是一个自洽的中性输运解。没有体积源、没有复合、没有壁面反射、没有第二个边界，也没有和等离子体背景的耦合；``alpha`` 还是外部给定的。
- 负速度分支为零是首飞边界注入方式的直接结果，不是“物理上没有反向中性粒子”。要填充负分支，需要体积源或另一端的边界处理。
- 单格点与 ``exp(-alpha*x/u_x)`` 的吻合只验证了这一条特征线上的离散；它不验证积分密度、其它速度格点或空间变化的 ``alpha``。
- ``dx = 0.01 m`` 的选择通过了本例的非负性检查；这里没有针对完整分布做空间或速度网格收敛研究。
- 输出是分布值，不是密度或通量。``gen`` 必须和同一个 ``volume`` 一起使用；换一套测度就不能直接比较。

终态诊断：通量与热通量
----------------------

终态归约函数把一份选定的终态分布变成空间剖面。它们接收归一化速度轴、显式热速度、分布、径向权重和轴向宽度：

- ``reduce_terminal_molecular_flux_velocity`` 返回轴向通量和平均速度；
- ``reduce_terminal_molecular_pressure_temperature`` 返回压强和温度；
- ``reduce_terminal_molecular_heat_flux`` 返回随机热通量和总热通量。

这三个入口都允许零宽度单元，只要每个空间切片的积分密度为正。在正权重下，它们与矩归约共享同一组离散定义：

.. code-block:: text

   density = sum(volume*f)
   flux = Vth*sum(volume*vx*f)
   u = flux/density
   T = p/density

这里用的是正权重的 ``radial_measure`` 和 ``dvx``，所以它们与矩归约在重叠字段上应当逐项一致。

前面的 ``gen`` 用单位积分种子构造，实际密度从边界的 0.622978 m^-3 衰减到末端的 0.000697 m^-3。为了得到可读的物理量级，令 ``n0 = 1e20`` 为目标参考密度 1e20 m^-3 相对于 1 m^-3 的无量纲倍数；``f_phys = n0 * gen`` 因而仍具有 m^-3 单位。因为 ``alpha`` 是外部给定的，不随密度变化，这个缩放只改变诊断的绝对值，不改变传播结果。

.. code-block:: python

   from scirel.kinetic import (
       reduce_terminal_molecular_flux_velocity,
       reduce_terminal_molecular_pressure_temperature,
       reduce_terminal_molecular_heat_flux,
   )

   n0 = 1.0e20
   f_phys = n0 * gen
   mom_phys = reduce_axisymmetric_neutral_moments(
       f_phys, vx, vr, quad["volume"],
       normalization_temperature_ev=tnorm,
       isotope_mass_amu=2.0, molecularity=1,
   )
   flux = reduce_terminal_molecular_flux_velocity(
       vx, seed["thermal_speed_m_s"], f_phys,
       quad["radial_measure"], quad["dvx"],
   )
   pt = reduce_terminal_molecular_pressure_temperature(
       vr, vx, 1.0, seed["thermal_speed_m_s"], f_phys,
       quad["radial_measure"], quad["dvx"],
   )
   hf = reduce_terminal_molecular_heat_flux(
       vr, vx, 1.0, seed["thermal_speed_m_s"], f_phys,
       quad["radial_measure"], quad["dvx"],
   )

   for k in (0, 200):
       print(f"x={x[k]:.1f} m:")
       print(f"  n = {mom_phys['density_m3'][k]:.6e} m^-3")
       print(f"  flux = {flux['flux_profile_m2_s'][k]:.6e} m^-2 s^-1")
       print(f"  u = {flux['mean_velocity_profile_m_s'][k]:.6e} m/s")
       print(f"  p = {pt['pressure_profile_ev_m3'][k]:.6e} eV m^-3")
       print(f"  T = {pt['temperature_profile_ev'][k]:.6f} eV")
       print(f"  q_rand = {hf['random_heat_flux_profile_w_m2'][k]:.6e} W m^-2")
       print(f"  q_total = {hf['total_heat_flux_profile_w_m2'][k]:.6e} W m^-2")

   rel_flux = np.max(
       np.abs(flux["flux_profile_m2_s"] - mom_phys["axial_flux_m2_s"])
       / np.abs(mom_phys["axial_flux_m2_s"])
   )
   rel_p = np.max(
       np.abs(pt["pressure_profile_ev_m3"] - mom_phys["pressure_ev_m3"])
       / np.abs(mom_phys["pressure_ev_m3"])
   )
   rel_q = np.max(
       np.abs(hf["random_heat_flux_profile_w_m2"] - mom_phys["random_heat_flux_w_m2"])
       / np.abs(mom_phys["random_heat_flux_w_m2"])
   )
   print(f"relative mismatch: flux {rel_flux:.2e}, p {rel_p:.2e}, q_rand {rel_q:.2e}")

实际输出：

.. code-block:: text

   x=0.0 m:
     n = 6.229784e+19 m^-3
     flux = 5.671956e+23 m^-2 s^-1
     u = 9.104579e+03 m/s
     p = 9.934682e+19 eV m^-3
     T = 1.594707 eV
     q_rand = 2.409290e+04 W m^-2
     q_total = 3.945699e+05 W m^-2
   x=2.0 m:
     n = 6.974323e+16 m^-3
     flux = 1.424204e+21 m^-2 s^-1
     u = 2.042068e+04 m/s
     p = 2.080844e+16 eV m^-3
     T = 0.298358 eV
     q_rand = 8.061539e+00 W m^-2
     q_total = 1.266536e+03 W m^-2
   relative mismatch: flux 1.94e-15, p 2.11e-15, q_rand 8.54e-14

密度下降为原来的约 ``0.00112``，通量下降为约 ``0.00251``；平均速度从 9.10 km/s 升到 20.42 km/s，说明慢粒子被优先损失。通量是 ``n*u`` 的剖面，必须和密度、速度一起读，不能把速度当常数。

压强下降为约 ``0.000209``，温度从 ``1.5947`` 降到 ``0.2984`` eV，约为边界值的 ``0.187``。本例的壁面损失还选择径向速度，因此速度过滤同时改变了中心化二阶矩。边界温度本来就不同于种子参数 2 eV：只保留正速度半边后，中心化二阶矩也随之改变。

随机热通量从 ``2.41e4`` 降到 ``8.06`` W/m²，总热通量从 ``3.95e5`` 降到 ``1.27e3`` W/m²。总热通量在 ``x=0`` 约为随机热通量的 16.4 倍，因为它还包含整体动能通量和焓通量；随机热通量只描述相对平均流速的涨落。两者回答不同的问题，不能互相替代。

最后一行的相对差 ``1.94e-15``、``2.11e-15``、``8.54e-14`` 说明终态归约和矩归约在同一套正权重上消费了同一个离散分布。这是代数一致性检查，不是独立物理验证或误差上界。

这一节不能推出什么
~~~~~~~~~~~~~~~~~~~~

- 这些剖面只对应一个边界分布、一个 ``alpha`` 模型和一个网格。它们不是守恒证明，也不覆盖壁面反射、体积源、复合或与等离子体的反馈。
- ``n0 = 1e20`` 是演示用的缩放。热通量、通量和压强都随 ``n0`` 线性缩放；如果 ``alpha`` 实际上依赖密度，这个缩放就不再与传播自洽。
- 温度和热通量的变化只描述这组带损失分布的矩；它们不单独构成能量守恒检查。换定义或参考系时，热通量读数也会改变。
- 终态入口允许零权重单元；这里没有触发那个分支。零权重单元的行为不能用这组正权重结果外推。
- 一致性达 ``1e-15`` 不代表物理精度；它只说明两个后处理路径的离散求和一致。真正的误差来源是网格、``alpha``、边界分布和速度截断。

易错点
------

**归一化速度与物理速度。** 输运中的 ``vx`` 是无量纲 ``u_x``，``alpha=nu/Vth`` 是 m^-1，``x`` 是 m，因而 ``dx*alpha/u_x`` 无量纲。物理频率要除以同一个 ``Vth``，不要把物理速度和逆长度系数混搭。源项是 ``Q/Vth`` （F/m）；显式 Boltzmann 右端入口将整个空间平衡乘一次 ``Vth``，恢复 F/s。

**质量因子要成套使用。** 本章的 H2 记账是 ``mass_amu=2``、``isotope_mass_amu=2``、``molecularity=1``、终态 ``mass_ratio=1``。如果保持同一个分布，却把矩归约改成 ``isotope_mass_amu=1``、``molecularity=2``，热速度和分子质量会同时换一套因子，同一分布会给出约 ``4453.6 m/s`` 的流速和 ``4.0385 eV`` 的温度，而不是上面的 3009.1 m/s 和 1.9888 eV。这不是物理变化，是记账不一致。

**请求能量会改变 ``Tnorm``。** 本章把 ``requested_energy_ev`` 设为 ``(1.1,)``，``Tnorm`` 才是 1.050 eV，且温度展宽仍走均匀分支。若改成 ``(5.0,)``，``Tnorm`` 会变成 2.35 eV，网格切换成拉伸分支；同一个 ``nv`` 不再产生上面的节点。加能量节点不是“只多一个节点”。

**首飞边界只填正速度分支。** ``first_flight`` 的 ``incoming_boundary`` 只在 ``x=0`` 写入正 ``vx``；负分支从右边界零初值后向递推，没有边界注入。需要双向入射时，不能把一次首飞调用当成两端边界问题。

**密度衰减不是单指数。** 最快格点符合 ``exp(-alpha*x/u_x)``，但积分密度比值约 0.00112 是速度过滤的结果。不同速度的衰减不同，不能用积分密度拟合一个速率再反推唯一的 ``alpha``。

**随机热通量不是总热通量。** 前者是中心化涨落携带的热流，后者还包括整体动能和焓的输运。本章 ``x=0`` 处两者相差约 16 倍。引用“热通量”时必须说明是哪一个。

**一致性检查不是误差估计。** 终态与矩归约的 ``1e-15`` 级一致只说明同一离散测度下的求和一致；它不告诉你网格够不够细、``alpha`` 对不对、边界分布是否物理。

什么时候用哪个函数
------------------

- 要建立速度网格：用 :doc:`../reference/generated/scirel.kinetic.adaptive-neutral-velocity-mesh`。要注意温度展宽阈值、请求能量插入和 ``Tnorm`` 的定义。
- 要由已有 ``vr``、``vx`` 构造积分测度：用 :doc:`../reference/generated/scirel.kinetic.cylindrical-velocity-quadrature`。它不生成网格，也不做单位换算。
- 要构造平移 Maxwellian 初值：用 :doc:`../reference/generated/scirel.kinetic.shifted-maxwellian-seed`。它不做矩补偿，归一化依赖你传入的 ``cylindrical_volume``。
- 要从分布得到密度、流速、温度、应力和随机热通量：用 :doc:`../reference/generated/scirel.kinetic.axisymmetric-neutral-moments`。注意空切片策略和 ``stress_zz`` 的别名约定。
- 要组装归一化总损失系数 ``nu/Vth``：用 :doc:`../reference/generated/scirel.kinetic.neutral-total-collision-frequency`。电荷交换启用时必须显式给出逆长度系数场；精确零直径 ``D = 0`` 是显式关闭壁面的哨兵值，不是 ``D -> 0+`` 的极限；封闭或退化几何解释由调用方在输运边界层决定。
- 要组装一维上风系数：用 :doc:`../reference/generated/scirel.kinetic.neutral-upwind-transport-coefficients`。首飞和散射两条路径消费不同的系数，先确定 ``generation_kind``。
- 要传播一代中性粒子：用 :doc:`../reference/generated/scirel.kinetic.neutral-generation-propagation`。首飞只用正速度边界；散射需要 ``scattered_source_distribution``。
- 要由终态分布读通量和流速：用 :doc:`../reference/generated/scirel.kinetic.terminal-flux-velocity-reduction`；读压强和温度：用 :doc:`../reference/generated/scirel.kinetic.terminal-pressure-temperature-reduction`；读随机/总热通量：用 :doc:`../reference/generated/scirel.kinetic.terminal-heat-flux-reduction`。
- 如果源在空间中有形状，而不是从边界入射，先看 :doc:`../reference/generated/scirel.kinetic.spatial-source-shape-normalization`，再决定是否走散射代际。本章没有展开这条路径。

适用范围与验证边界
------------------

本章的数值只对应这套一维空间、二维轴对称速度、H2 质量记账、外部给定 ``alpha`` 和首飞边界注入的模型。它不覆盖：

- 磁化或二维/三维空间输运；
- 与等离子体密度、温度、电势自洽耦合的求解；
- 壁面反射、分子内自由度、振动/转动能级和化学反应网络；
- 非线性 Boltzmann 右端、多个代际的累计与收敛判据；
- 跨物种网格插值。

这些功能有各自的入口和合同；不要用本章的脚本外推。参数校验、异常类型、完整的输入/输出字段和每个函数的适用范围在章末链接的 API 参考页；它们由合同生成，和本章的实际运行数字是两层不同的证据。

本章的验证边界是：脚本在当前 ``.venv`` 中按顺序真实跑通；每段输出都来自该次执行；单格点指数衰减和终态/矩一致性是两个独立的数值检查。它们不构成全参数域验证，也不构成对 ``alpha``、边界分布或网格物理适用性的批准。

.. seealso::

   如果你更关心动理学方程的频域根和初值演化，可以继续读 :doc:`/tutorials/kinetic-initial-value`；如果你要在其它领域选择入口，回到 :doc:`/user-guide/index`。
