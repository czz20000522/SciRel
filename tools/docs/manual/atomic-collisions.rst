原子碰撞：从一条截面到局部碰撞频率
====================================

这一章跟着一个问题走：**给定氢等离子体的温度、密度和速度网格，怎样从一条电荷交换截面，走到一个可解释的局部碰撞频率？**

路径是连续的：

.. code-block:: text

   截面 sigma(E)
     -> Maxwellian 靶上的能量分辨 <sigma v>
     -> 四族碰撞矩阵 SIG
     -> Alpha 场
     -> Omega 与 nu

这条路径只覆盖原子氢的一部分碰撞过程。它不是完整的碰撞辐射模型，也不包含速率系数拟合、Saha 人口、弹性截面的全部分支或分子氢的平行实现；这些入口在章末单独说明。

约定：能量用 eV，截面用 m²，速率系数用 m³/s，密度用 m^-3；速度网格用热速度 ``Vth`` 归一化；``Omega`` 用 m^-1，``nu`` 用 s^-1。下面的代码只调用 SciRel 公开函数，数值输出都是在仓库 ``.venv`` 中实际运行得到的，不是手写的示意值。

从能量到截面：先确认分支和端点
------------------------------

H 与 H⁺ 的电荷交换截面有两条独立拟合。默认分支是九系数 Janev 对数多项式，``freeman=True`` 选择另一条 Freeman-Jones 解析式：

.. code-block:: text

   Janev:    exp(polyval(log(E), a)) * 1e-4
   Freeman:  1e-4 * 0.6937e-14 * (1 - 0.155 log10(E))^2
             / (1 + 0.1112e-14 E^3.3)

两条式子的能域不同：Janev 分支把能量裁到 ``[0.1, 2.01e4]`` eV，Freeman 分支裁到 ``[0.1, 1e5]`` eV。所谓“裁剪”不是外推，也不是报错；超出能域的正能量会静默返回端点值。负能量则会被拒绝。

.. code-block:: python

   import numpy as np
   from scirel.collisions import (
       evaluate_atomic_hydrogen_charge_exchange_cross_section as cx_h,
       evaluate_molecular_hydrogen_charge_exchange_cross_section as cx_h2,
   )

   energy = np.array([1.0, 10.0, 100.0, 1.0e3, 1.0e4])
   janev = cx_h(energy)
   freeman = cx_h(energy, freeman=True)
   molecular = cx_h2(energy)
   print("E/eV   H+H+ Janev   H+H+ Freeman   H2+H2+")
   for e, a, f, m in zip(energy, janev, freeman, molecular):
       print(f"{e:8.0f}  {a*1e20:11.3f}  {f*1e20:13.3f}  {m*1e20:7.3f}")

   lo = cx_h(np.array([0.01, 0.1]))
   hi = cx_h(np.array([3.0e4, 2.01e4]))
   print("clip low ", lo[0] == lo[1], f"{lo[0]:.6e}")
   print("clip high", hi[0] == hi[1], f"{hi[0]:.6e}")

   try:
       cx_h(np.array([1.0, -0.5]))
   except ValueError as error:
       print(type(error).__name__, error)
   try:
       cx_h(energy, freeman=np.ones((2, 2)))
   except ValueError as error:
       print(type(error).__name__, error)

实际输出（截面数值的单位是 1e-20 m²）：

.. code-block:: text

   E/eV   H+H+ Janev   H+H+ Freeman   H2+H2+
          1       60.348         69.370   12.959
         10       46.315         49.532   12.099
        100       31.434         33.027    7.581
       1000       17.441         19.855    4.771
      10000        8.979          9.844    6.048
   clip low  True 7.296111e-19
   clip high True 4.993038e-20
   ValueError energy_ev must be nonnegative
   ValueError freeman must be a scalar branch selector, not an array

在这五个能量点上，Janev 分支从 ``60.348e-20`` 降到 ``8.979e-20`` m²；Freeman 分支在低能端高约 15%，到 10 keV 附近只高约 10%。分子氢的拟合在低能端明显更小，但在 10 keV 附近又接近原子分支；这两条曲线没有简单的常数比例关系。两个原子分支是**独立拟合**，不是同一个量的两种参数化；选哪一条是调用者的模型选择，不能把两条的差当成误差棒。

端点检查显示：``E=0.01`` 与 ``E=0.1`` 返回完全相同的 ``7.296111e-19``，``E=3.0e4`` 与 ``E=2.01e4`` 返回完全相同的 ``4.993038e-20``。这是合同声明的端点复制。负能量在裁剪之前就被拒绝，错误信息里点名 ``energy_ev``；数组形式的 ``freeman`` 也被拒绝，而不是被 ``np.any`` 归约。

这一节不能推出：这些数是截面，不是速率系数，也不是碰撞频率；没有做热平均；没有外部原子物理实验基准；不能从两条拟合的差得到不确定度；也不能把端点值当作能域外的有效外推。

把截面放进 Maxwellian 靶：能量分辨的 <sigma v>
-----------------------------------------------

下一步把截面放进一个离散的圆柱速度网格。一个沿轴向 ``vx`` 运动的单能粒子，穿过温度为 ``T_target`` 的 Maxwellian 靶；靶分布在 ``(vr, vx)`` 网格上离散，网格单元体积由调用者给出。合同中的速率为

.. code-block:: text

   vth = sqrt(2 e Tnorm / (m_target m_H))
   f_target(vr,vx) ∝ exp(-(vr^2 + vx^2) Tnorm / T_target)
   rate(E) = vth * sum(volume * sigma(E_rel) * v_rel * f_target)

碰撞能量用**入射粒子质量** ``particle_mass_amu`` 构造，而不是约化质量；这是这个算符的约定。靶分布用调用者给的单元体积归一化，因此把所有体积同乘一个常数不会改变结果。

.. code-block:: python

   import numpy as np
   from scirel.collisions import (
       average_cross_section_over_maxwellian,
       evaluate_atomic_hydrogen_charge_exchange_cross_section as cx_h,
   )

   dvr = 3.5 / 24
   dvx = 7.0 / 36
   vr = (np.arange(24) + 0.5) * dvr
   vx = (np.arange(36) + 0.5) * dvx - 3.5
   M_H = 1.6726231e-27
   e = 1.602177e-19
   vth = np.sqrt(2.0 * e * 20.0 / (1.0 * M_H))
   volume = np.outer(vr * dvr, np.full(36, dvx)) * vth**3
   beam = np.array([0.0, 1.0, 10.0, 100.0])
   rate = average_cross_section_over_maxwellian(
       particle_energy_ev=beam,
       particle_mass_amu=1.0,
       target_temperature_ev=10.0,
       target_mass_amu=1.0,
       vx=vx, vr=vr, tnorm_ev=20.0,
       cylindrical_volume=volume,
       cross_section_m2=cx_h,
   )
   print(f"vth = {vth:.6e} m/s")
   print("E_beam/eV   <sigma v>/(m^3/s)")
   for E, R in zip(beam, rate):
       print(f"{E:9.0f}   {R:.9e}")

   sigma0 = 3.0e-20
   const = average_cross_section_over_maxwellian(
       particle_energy_ev=beam,
       particle_mass_amu=1.0,
       target_temperature_ev=20.0,
       target_mass_amu=1.0,
       vx=vx, vr=vr, tnorm_ev=20.0,
       cylindrical_volume=volume,
       cross_section_m2=lambda E: np.full_like(E, sigma0),
   )
   analytic = sigma0 * vth * 2.0 / np.sqrt(np.pi)
   print(f"const rest limit: {const[0]:.9e} vs {analytic:.9e}  ratio={const[0]/analytic:.6f}")

   scaled = average_cross_section_over_maxwellian(
       particle_energy_ev=beam,
       particle_mass_amu=1.0,
       target_temperature_ev=10.0,
       target_mass_amu=1.0,
       vx=vx, vr=vr, tnorm_ev=20.0,
       cylindrical_volume=volume * 7.5,
       cross_section_m2=cx_h,
   )
   print("volume scaling exact:", np.array_equal(scaled, rate))

实际输出：

.. code-block:: text

   vth = 6.189937e+04 m/s
   E_beam/eV   <sigma v>/(m^3/s)
           0   2.161479352e-14
           1   2.213181636e-14
          10   2.620005271e-14
         100   4.415984397e-14
   const rest limit: 2.093487534e-15 vs 2.095378633e-15  ratio=0.999097
   volume scaling exact: True

``vth`` 是 20 eV 归一化能量、氢靶质量对应的热速度，约 ``6.19e4`` m/s。用真实电荷交换截面得到的 ``<sigma v>`` 从 ``2.16e-14`` 升到 ``4.42e-14`` m³/s：入射能量增加时相对速度增大，而截面下降得没有那么快，所以在这四个点上速率上升。这个趋势只属于这条束靶设置，不能外推成“所有温度下都上升”。

恒截面检查用的是 ``T_target = Tnorm = 20`` eV、零束能。此时解析极限是 ``sigma * vth * 2/sqrt(pi)``；运行值 ``2.093487534e-15`` 与解析值 ``2.095378633e-15`` 的比是 ``0.999097``。这点差异来自 24×36 中点网格的离散误差，说明归一化和静止束极限是对的，不说明网格已经收敛。体积整体乘 7.5 后结果逐位相同，说明体积只是测度，靶分布按它归一化后整体尺度会抵消；这**不**意味着任意非均匀的体积改动都不影响积分。

这一节不能推出：这不是两个 Maxwellian 之间的热速率系数，而是单能粒子对离散 Maxwellian 靶的束靶平均；不能把它和给定的双变量速率拟合直接对比；没有检查网格尾部是否解析；没有包含物种混合、屏蔽或碰撞频率。

把核函数装成矩阵：四族 SIG
---------------------------

要把截面变成输运算符，需要在一个归一化圆柱速度网格上组装四族核矩阵：电荷交换 ``SIG_CX``、H–H⁺ 动量传递 ``SIG_H_P``、H–H₂ 动量传递 ``SIG_H_H2`` 和 H–H 自碰撞应力 ``SIG_H_H``。角向用中点离散：

.. code-block:: text

   g^2 = vr_i^2 + vr_k^2 - 2 vr_i vr_k cos(theta) + (vx_j - vx_l)^2
   theta_m = pi (m + 1/2) / n_theta

矩阵列权重是 ``Vr2pidVr_k * dVx_l``，速度载体按 Fortran 顺序展平：``row = i + nvr*j``，``col = k + nvr*l``。默认 ``n_theta=5``；合同明确把它当作可显式加节点的离散参数，而不是普适精度保证。

.. code-block:: python

   import numpy as np
   from scirel.collisions import assemble_atomic_hydrogen_collision_matrices as assemble

   vr = np.array([0.5, 1.0])
   vx = np.array([-1.0, 0.0, 1.0])
   wr = np.array([1.0, 2.0])
   dx = np.ones(3)
   s5 = assemble(vr, vx, wr, dx, 10.0, mu=1.0, n_theta=5)
   s32 = assemble(vr, vx, wr, dx, 10.0, mu=1.0, n_theta=32)
   for name in ("SIG_CX", "SIG_H_P", "SIG_H_H2", "SIG_H_H"):
       a = s5[name]
       print(f"{name:8s} shape={a.shape} min={a.min(): .3e} max={a.max(): .3e} neg={np.count_nonzero(a < 0)}")
   print(f"Vth = {np.sqrt(s5['Vth2'][0]):.6e} m/s")
   for name in ("SIG_CX", "SIG_H_P", "SIG_H_H2", "SIG_H_H"):
       d = np.max(np.abs(s5[name] - s32[name]))
       rel = d / np.max(np.abs(s32[name]))
       print(f"{name:8s} max|5-32|={d:.3e} rel={rel:.3e}")

实际输出：

.. code-block:: text

   SIG_CX   shape=(6, 6) min= 3.186e-19 max= 1.710e-18 neg=0
   SIG_H_P  shape=(6, 6) min=-5.118e-18 max= 5.118e-18 neg=12
   SIG_H_H2 shape=(6, 6) min=-4.099e-20 max= 4.099e-20 neg=12
   SIG_H_H  shape=(6, 6) min=-3.904e-20 max= 1.950e-20 neg=24
   Vth = 4.376946e+04 m/s
   SIG_CX   max|5-32|=7.806e-21 rel=4.564e-03
   SIG_H_P  max|5-32|=2.754e-24 rel=5.380e-07
   SIG_H_H2 max|5-32|=6.563e-26 rel=1.601e-06
   SIG_H_H  max|5-32|=1.667e-23 rel=4.270e-04

2×3 的速度网格给出 N=6，所以四个矩阵都是 6×6。``SIG_CX`` 在这个网格上严格非负；另外三个核保留负元素，因为动量传递和应力投影本身带符号。负元素不是组装失败，也不能用 ``abs`` 或截正“修好”。

``Vth`` 约 ``4.38e4`` m/s。把默认五点换成 32 点后，``SIG_CX`` 的最大相对变化是 ``4.56e-3``（约 0.46%），``SIG_H_H`` 是 ``4.27e-4``，而两个混合通道只有 ``1e-7`` 到 ``1e-6``。这说明默认五点的误差不是所有族都一样大；它也**不**证明 32 点已经收敛。合同把角节点数留作显式收敛检查参数，使用者应自己加密并报告变化。

这一节不能推出：矩阵元素不是物理速率，只有与分布收缩后才有碰撞频率的含义；没有外部截面实验基准；没有证明默认角节点适用于任意网格；``Tnorm`` 和 ``mu`` 是模型输入，不是从数据推断出来的。

从矩阵到 Alpha：Fortran 顺序不是细节
-------------------------------------

下一层是逐空间单元的矩阵—向量收缩。合同写作

.. code-block:: text

   Alpha_CX[:,:,k]   = F^-1(SIG_CX   @ F(fi_hat[:,:,k] * ni[k]))
   Alpha_H_H2[:,:,k] = F^-1(SIG_H_H2 @ F(fH2[:,:,k]))
   Alpha_H_P[:,:,k]  = F^-1(SIG_H_P  @ F(fi_hat[:,:,k] * ni[k]))
   Alpha_H_H[:,:,k]  = F^-1(SIG_H_H  @ F(fH[:,:,k]))

其中 ``F`` / ``F^-1`` 是速度载体的 Fortran 顺序（``order='F'``）展平与恢复。``fi_hat`` 是归一化的原子种子分布，``ni`` 携带离子密度；``fH2`` 和 ``fH`` 直接是分子/原子中性粒子的密度分布。两个混合通道用 ``fi_hat * ni``，两个中性通道用各自的裸分布。

.. code-block:: python

   import numpy as np
   from scirel.collisions import assemble_atomic_hydrogen_collision_matrices as assemble
   from scirel.kinetic import contract_atomic_hydrogen_alpha_frequencies as contract

   vr = np.array([0.5, 1.0])
   vx = np.array([-1.0, 0.0, 1.0])
   wr = np.array([1.0, 2.0])
   dx = np.ones(3)
   w = wr[:, None] * dx[None, :]
   s = assemble(vr, vx, wr, dx, 10.0, mu=1.0, n_theta=32)

   def maxwell(density, drift):
       f = np.exp(-vr[:, None]**2 - (vx[None, :] - drift)**2)
       return f * density / np.sum(w * f)

   fi = maxwell(1.0, 0.2)[:, :, None]
   fH2 = maxwell(2.0e17, -0.1)[:, :, None]
   fH = maxwell(1.0e17, 0.15)[:, :, None]
   alphas = contract(
       s["SIG_CX"], s["SIG_H_H"], s["SIG_H_H2"], s["SIG_H_P"],
       fi, np.array([1.5e17]), fH2, fH,
   )
   for name, value in alphas.items():
       print(f"{name:9s} shape={value.shape} min={value.min(): .3e} max={value.max(): .3e}")

   carrier = (fi * 1.5e17).reshape(6, order="F")
   f_order = s["SIG_CX"] @ carrier
   c_order = s["SIG_CX"] @ (fi * 1.5e17).reshape(6)
   manual = f_order.reshape(fi.shape, order="F")
   print("Fortran match:", np.array_equal(alphas["Alpha_CX"], manual))
   print(f"C-order vs Fortran max diff = {np.max(np.abs(c_order - f_order)):.3e}, rel={np.max(np.abs(c_order - f_order))/np.max(np.abs(f_order)):.3e}")

实际输出：

.. code-block:: text

   Alpha_CX  shape=(2, 3, 1) min= 7.125e-02 max= 1.024e-01
   Alpha_H_H2 shape=(2, 3, 1) min=-2.597e-03 max= 2.959e-03
   Alpha_H_P shape=(2, 3, 1) min=-1.926e-01 max= 1.294e-01
   Alpha_H_H shape=(2, 3, 1) min=-9.795e-04 max= 3.499e-04
   Fortran match: True
   C-order vs Fortran max diff = 3.244e-02, rel=3.167e-01

``fi`` 的积分被归一化为 1，``ni=1.5e17`` 才携带密度；``fH2`` 和 ``fH`` 的积分分别是 ``2.0e17`` 和 ``1.0e17`` m^-3。四个 Alpha 场都保持 ``(2, 3, 1)`` 形状。``Alpha_CX`` 在这个算例中约 ``0.071`` 到 ``0.102``；``Alpha_H_P`` 跨越负值和正值，``Alpha_H_H2`` 和 ``Alpha_H_H`` 也在零两侧。这些是带符号的中间场，不是概率密度，也不能直接当最终频率。

手工用 ``order='F'`` 展平后重算，``Alpha_CX`` 逐位一致（``Fortran match: True``）。若改用默认 C 顺序展平，最大相对差达到 ``31.7%``；这不是舍入误差，而是把速度单元按不同顺序喂给了矩阵。矩阵的 ``row=i+nvr*j`` 约定和这里的 ``order='F'`` 必须成对使用。

这一节不能推出：Alpha 场不是最终碰撞频率，不能只看它的正负号判断物理方向；负值来自带符号核，合同要求原样保留、不截正；这里只演示了一个空间单元，没有输运迭代或时间推进。

从 Alpha 到局部频率：比值、单位和未定义
---------------------------------------

最后一层在每个空间单元内把 Alpha 归约为局部矩匹配系数。设

.. code-block:: text

   n = sum(w f)
   u = sum(w f vx) / n
   U = Vth u
   K = vr^2 - 2 (vx - u)^2
   W = sum(w f K) / n

混合通道的分母是 ``(U - U_background)/Vth``，自碰撞通道的分母是 ``W``；``Omega = N/d``，``nu = Vth * Omega``。分母为零时，合同返回 ``NaN``、``defined=False``，但保留有限的碰撞矩；负比值保留并标记为 ``negative_no_bgk_closure``，不设下限、不截正。总频率是启用通道之和，任何一个启用通道未定义都会传播到总和。

.. code-block:: python

   import numpy as np
   from scirel.collisions import (
       assemble_atomic_hydrogen_collision_matrices as assemble,
       assemble_atomic_hydrogen_omega_frequencies as omega_reduce,
   )
   from scirel.kinetic import contract_atomic_hydrogen_alpha_frequencies as contract

   vr = np.array([0.5, 1.0])
   vx = np.array([-1.0, 0.0, 1.0])
   wr = np.array([1.0, 2.0])
   dx = np.ones(3)
   w = wr[:, None] * dx[None, :]
   s = assemble(vr, vx, wr, dx, 10.0, mu=1.0, n_theta=32)

   def maxwell(density, drift):
       f = np.exp(-vr[:, None]**2 - (vx[None, :] - drift)**2)
       return f * density / np.sum(w * f)

   fi = maxwell(1.0, 0.2)[:, :, None]
   fH2 = maxwell(2.0e17, -0.1)[:, :, None]
   fH = maxwell(1.0e17, 0.15)[:, :, None]
   a = contract(
       s["SIG_CX"], s["SIG_H_H"], s["SIG_H_H2"], s["SIG_H_P"],
       fi, np.array([1.5e17]), fH2, fH,
   )
   Vth = float(np.sqrt(s["Vth2"][0]))
   nH = np.sum(w * fH[:, :, 0])
   flow_fi = Vth * np.sum(w * fi[:, :, 0] * vx[None, :]) / np.sum(w * fi[:, :, 0])
   flow_H2 = Vth * np.sum(w * fH2[:, :, 0] * vx[None, :]) / np.sum(w * fH2[:, :, 0])
   r = omega_reduce(
       fH, np.array([nH]), a["Alpha_H_P"], a["Alpha_H_H2"],
       s["SIG_H_H"], wr, dx, vr, vx, Vth,
       np.array([flow_fi]), np.array([flow_H2]),
   )
   print(f"VxH = {r['VxH'][0]:.6f} m/s")
   print(f"Wperp_paraH = {r['Wperp_paraH'][0]:.9f}")
   for name in ("H_P", "H_H2", "H_H"):
       print(f"{name:4s} Omega={r['Omega_'+name][0]: .9f} 1/m  nu={r['nu_'+name][0]: .6f} 1/s  status={r['status_'+name][0]}")
   print(f"Omega_EL={r['Omega_EL'][0]:.9f} 1/m  nu_EL={r['nu_EL'][0]:.6f} 1/s")

   origin = vx[0]
   u_rel = np.sum(w * fH[:, :, 0] * (vx - origin)[None, :]) / nH
   u = origin + u_rel
   r0 = omega_reduce(
       fH, np.array([nH]), a["Alpha_H_P"], a["Alpha_H_H2"],
       s["SIG_H_H"], wr, dx, vr, vx, Vth,
       np.array([Vth * u]), np.array([Vth * u]),
   )
   print(f"matched flow: Omega_H_P={float(r0['Omega_H_P'][0])} defined={r0['defined_H_P'][0]} status={r0['status_H_P'][0]} moment={r0['moment_H_P'][0]:.6e}")

实际输出：

.. code-block:: text

   VxH = 5543.274344 m/s
   Wperp_paraH = -0.223070651
   H_P  Omega= 0.152986508 1/m  nu= 6696.137005 1/s  status=finite_nonnegative
   H_H2 Omega= 0.002655305 1/m  nu= 116.221279 1/s  status=finite_nonnegative
   H_H  Omega= 0.000631014 1/m  nu= 27.619145 1/s  status=finite_nonnegative
   Omega_EL=0.156272827 1/m  nu_EL=6839.977429 1/s
   matched flow: Omega_H_P=nan defined=False status=undefined_zero_denominator moment=-6.376374e-03

``VxH`` 是该单元原子氢的平均轴向速度，约 ``5.54e3`` m/s。``Wperp_paraH`` 是选定的中央应力（垂直减两倍轴向二阶矩），它是带符号量，约 ``-0.223``；负值不代表计算失败，也不能当方差解释。

在这个算例中，H–H⁺ 混合通道的 ``Omega`` 约 ``0.153`` m^-1，``nu`` 约 ``6.70e3`` s^-1；H–H₂ 和 H–H 通道小得多；三通道总 ``nu`` 约 ``6.84e3`` s^-1。三个通道的 ``status`` 都是 ``finite_nonnegative``，说明分母非零且比值非负。

最后一个调用故意把背景流速度设成与实际平均流一致，使混合通道的分母为零。结果 ``Omega_H_P`` 是 ``nan``、``defined=False``、状态为 ``undefined_zero_denominator``，但 ``moment_H_P`` 仍返回有限的 ``-6.376374e-03``。这正说明“频率未定义”和“碰撞矩不存在”不是一回事；也不能把 ``NaN`` 当成零碰撞。

这一节不能推出：这是矩匹配的局部归约，不是完整 Boltzmann 碰撞算子；有限速度/角网格不保证精确 Maxwell 平衡；负比值虽然被保留，但不构成可接受的非负 BGK 松弛；单单元结果不能替代空间耦合、时间推进或收敛研究。

选择入口、易错点与本章没有覆盖的部分
------------------------------------

按这条路径选函数：

- 只想要一条 H+H⁺ 电荷交换截面：:doc:`../reference/generated/scirel.collisions.atomic-hydrogen-charge-exchange-cross-section`；分子氢用 :doc:`../reference/generated/scirel.collisions.molecular-hydrogen-charge-exchange-cross-section`。
- 想把一条截面投到离散 Maxwellian 靶上：:doc:`../reference/generated/scirel.collisions.maxwellian-relative-speed-rate-average`。
- 想得到四族核矩阵：:doc:`../reference/generated/scirel.collisions.atomic-hydrogen-collision-matrices`。
- 想从矩阵和分布得到 Alpha：:doc:`../reference/generated/scirel.kinetic.atomic-alpha-contraction`。
- 想归约出局部 ``Omega`` 与 ``nu``：:doc:`../reference/generated/scirel.collisions.atomic-hydrogen-omega-frequencies`。

几个容易踩的坑：

- 分支和端点：Janev 与 Freeman-Jones 是两条独立拟合，能域和端点不同；超出能域的正能量是静默裁剪，不是外推。
- 束靶还是热平均：``average_cross_section_over_maxwellian`` 是单能粒子对 Maxwellian 靶的平均，不是两个 Maxwellian 之间的热速率。
- 质量约定：碰撞能量按 ``particle_mass_amu`` 构造，不是约化质量；不要通过改质量来“补偿”模型差异。
- 展平顺序：SIG 按 Fortran 顺序组装，Alpha 必须按 ``order='F'`` 收缩；C 顺序会产生可观察的数值错误。
- 带符号中间量：弹性核和部分 Alpha 有负值，合同要求保留；截正会改变模型。
- 未定义不是零：零分母给出 ``NaN`` 和 ``defined=False``；负比值有单独状态，不应被静默丢弃。

本章没有展开的入口，以及原因：

- 五个弹性截面资产（:doc:`../reference/generated/scirel.collisions.atomic-hydrogen-elastic-cross-section`、:doc:`../reference/generated/scirel.collisions.atomic-molecular-hydrogen-elastic-cross-section`、:doc:`../reference/generated/scirel.collisions.molecular-hydrogen-elastic-cross-section`、:doc:`../reference/generated/scirel.collisions.proton-atomic-hydrogen-elastic-cross-section`、:doc:`../reference/generated/scirel.collisions.proton-molecular-hydrogen-elastic-cross-section`）：动量传递/黏性分支、输出形状和 10 eV 分段断点由各资产合同规定；H–H₂ 与 H⁺–H 返回与输入相同的形状，H⁺–H 在 E<10 eV 时使用低能分支，在 E≥10 eV（含恰好 10 eV）时使用高能分支。它们服务于弹性矩阵，但会把本章从一条连续路径变成截面清单。
- 五个速率与人口资产（:doc:`../reference/generated/scirel.collisions.atomic-hydrogen-charge-exchange-rate-coefficient`、:doc:`../reference/generated/scirel.collisions.molecular-hydrogen-charge-exchange-rate-coefficient`、:doc:`../reference/generated/scirel.collisions.janev-electron-impact-ionization-rate`、:doc:`../reference/generated/scirel.collisions.atomic-hydrogen-1s-radiative-recombination-rate-coefficient`、:doc:`../reference/generated/scirel.kinetic.hydrogen-saha-equilibrium-population`）：它们是从温度/能量或密度/温度直接给出的独立拟合与 Saha 关系，不能由本章的束靶平均或矩阵收缩推出。
- 分子氢的矩阵、Alpha 和 Omega（:doc:`../reference/generated/scirel.collisions.molecular-hydrogen-collision-matrices`、:doc:`../reference/generated/scirel.kinetic.molecular-alpha-contraction`、:doc:`../reference/generated/scirel.collisions.molecular-hydrogen-omega-frequencies`）：结构与原子路径平行，但系数表、物种配对和截面拟合不同；重复一遍代码不会增加新的方法信息。
- 三通道求和入口（:doc:`../reference/generated/scirel.kinetic.elastic-frequency-channels`）：它是已归一化通道的逐点求和；本章的 ``omega_reduce`` 已经返回 ``Omega_EL``，单独再讲会重复。

边界：本章的数值只对应声明的归一化圆柱网格、给定的截面拟合和这套矩匹配归约。换分布、换物种、换 ``Tnorm``/``mu``、换角节点或换空间耦合，都不能直接套用这里的 ``Omega`` 和 ``nu``。完整签名、参数校验、失败行为和更大参数域的验证边界在章末链接的 API 参考页；本章只负责把一条计算路径讲清楚。
