从冷等离子体到动理学色散关系
============================

这一章回答一个具体问题：**给定了等离子体参数、背景磁场和一个波矢，怎样一步步判断波能不能传播、频率是多少、阻尼有多强？** 我们不会逐个函数罗列入口，而是沿一条连续的计算路径走：

1. 把密度、温度、质量和磁场换算成 SI 尺度，并说明波矢的几何约定；
2. 用冷等离子体模型算一个局部介电张量，看它给出了什么、又缺了什么；
3. 换成动理学 Maxwellian 静电响应，在一个复频率处计算介电函数；
4. 用这个响应作为残差，从一个种子求出一条复根；
5. 扫一段波数，检查分支连续性，并解释一个常见的分支陷阱；
6. 用固定极点有理近似替换等离子体色散函数，比较不同阶数的误差；
7. 组装磁化动理学介电张量，在同一波点比较有限谐波求和与 Ronnmark 极点两条路径。

读完本章，你应该能独立完成一条“冷模型估计 → 动理学响应 → 种子求根 → 分支扫描 → 方法交叉检查”的计算，并且知道每一步的结论边界。

.. note::

    本章是教程，不是合同摘要。每个函数的完整签名、参数单位、失败行为和适用范围在章末链接的 API 参考页；教程里的代码只调用 SciRel 的公开函数。

本章的代码块按顺序执行：后面的块会复用前面定义的 ``E``、``M_E``、``M_D``、``scales``、``wp`` 和 ``species``。如果要单独运行某一块，请先执行“准备：平衡尺度与波矢”中的代码。

约定与路线
----------

本章统一采用时间约定 ``exp(-i omega t)``。冷等离子体部分用 SI 单位；动理学静电部分采用归一化单位：等离子体频率为 1、Maxwellian 热速度标准差为 1、波数按逆 Debye 长度归一化。两种单位不能直接混用，后文会在切换处明确说明。

文中的“根”只表示某个复方程在数值上被满足，不表示它一定是物理上最重要的模式，也不表示它是唯一根。分支选择始终由调用者给出的种子和扫描顺序决定。

准备：平衡尺度与波矢
--------------------

先取一个具体的氘电子等离子体：背景磁场 ``B0 = 1 T``，电子和离子密度都是 ``1e19 m^-3``，参考温度 ``T00 = 1000 eV``；电子温度等于参考温度，离子温度取 ``0.5 T00``。组分尺度由下面的关系给出：

.. code-block:: text

   v_ts      = sqrt(2 k_B T_s / m_s)
   omega_cs  = q_s B0 / m_s
   omega_ps^2 = n_s q_s^2 / (m_s epsilon_0)
   rho_cs    = sqrt(k_B T_s / m_s) / omega_cs
   k_n       = 1 / max_s |rho_cs|
   omega_n   = min_s |omega_cs|

``omega_cs`` 和 ``rho_cs`` 都带电荷符号；``omega_n`` 取的是**最小**绝对回旋频率，在这个双组分例子里是离子回旋频率，而不是电子回旋频率。``k_n`` 取的是**最大**绝对回旋半径，也就是离子回旋半径的倒数。这个选择是后续磁化张量入口的归一化约定，不是物理上的“最重要尺度”。

.. code-block:: python

   import numpy as np
   from scirel.kinetic import derive_species_equilibrium_scales
   from scirel.geometry import project_planar_wavevector

   E = 1.602176634e-19
   M_E = 9.1093837015e-31
   M_D = 2.013553212745 * 1.67262192369e-27

   scales = derive_species_equilibrium_scales(
       ms=[M_E, M_D],
       qs=[-E, E],
       ns_unit=[1.0, 1.0],
       Ts_unit=[1.0, 0.5],
       B0=1.0, n00=1e19, T00=1000.0,
   )
   wp = np.sqrt(scales["wp2"])
   print(f"f_pe  = {wp/(2*np.pi)/1e9:.3f} GHz")
   print(f"f_ce  = {abs(scales['wcs'][0])/(2*np.pi)/1e9:.3f} GHz")
   print(f"f_ci  = {scales['wcs'][1]/(2*np.pi)/1e6:.3f} MHz")
   print(f"v_te  = {scales['vts'][0]/1e6:.3f} Mm/s")
   print(f"v_ti  = {scales['vts'][1]/1e3:.3f} km/s")
   print(f"rho_i = {scales['rhocs'][1]*1e3:.3f} mm")
   print(f"kn    = {scales['kn']:.3f} 1/m")
   print(f"wn    = {scales['wn']:.3e} rad/s")

   waves = project_planar_wavevector(k_grid=[0.5, 1.0], theta_rad=0.3)
   print("kx =", waves["kx"])
   print("kz =", waves["kz"])
   print("k  =", waves["k"])

实际输出：

.. code-block:: text

   f_pe  = 28.397 GHz
   f_ce  = 27.992 GHz
   f_ci  = 7.571 MHz
   v_te  = 18.756 Mm/s
   v_ti  = 218.111 km/s
   rho_i = 3.242 mm
   kn    = 308.451 1/m
   wn    = 4.757e+07 rad/s
   kx = [0.1477601  0.29552021]
   kz = [0.47766824 0.95533649]
   k  = [0.5 1. ]

``f_pe`` 是总等离子体频率，由电子和离子的 ``omega_ps^2`` 相加得到；离子的贡献很小，但代码仍然把它算进去。``f_ce`` 约 27.99 GHz，``f_ci`` 约 7.57 MHz，两者相差约 3700 倍，正好是电子与离子的质量比量级。``v_te`` 约 18.8 Mm/s，是 1 keV 电子的热速度；``v_ti`` 约 218 km/s。``rho_i`` 约 3.24 mm，所以 ``kn`` 约 308 1/m；``wn`` 等于离子回旋频率，约 ``4.76e7 rad/s``。

波矢投影采用 ``kx = k sin(theta)``、``kz = k cos(theta)``，角度从 ``+z`` 向 ``+x`` 量。``theta = 0.3 rad`` 时，``k = 0.5 1/m`` 对应 ``kx = 0.148 1/m``、``kz = 0.478 1/m``。这里的 ``z`` 轴就是背景磁场方向；后面的磁化张量入口要求把垂直分量和平行分量分开传入。

**这一节不能推出什么。** 尺度只说明“这个平衡态有哪些特征频率和长度”，不说明任何波一定存在，也不说明哪个模式最重要。``wn`` 和 ``kn`` 是入口的归一化选择，不是模式频率或模式波数；换一套归一化，数值会变，但物理结论不应跟着变。

冷等离子体：介电张量
--------------------

冷模型把每个组分看成没有热运动的流体。对频率 ``omega``、背景磁场 ``B`` 和物种列表，Stix 标量为

.. code-block:: text

   S   = 1 - sum_s omega_ps^2 (omega + i nu_s)
             / (omega [(omega + i nu_s)^2 - Omega_cs^2])
   D_H = sum_s Omega_cs omega_ps^2
             / (omega [(omega + i nu_s)^2 - Omega_cs^2])
   P   = 1 - sum_s omega_ps^2 / (omega (omega + i nu_s))

其中 ``Omega_cs = q_s |B| / m_s`` 是带符号的回旋频率，``nu_s`` 是碰撞率。张量在调用者给出的笛卡尔基底中写成

.. code-block:: text

   epsilon_r = S I + (P - S) b b + i D_H [b]_x

``b`` 是磁场单位方向，``[b]_x`` 是叉乘矩阵。这个表达式说明：平行方向由 ``P`` 控制，垂直对角由 ``S`` 控制，垂直非对角由 ``D_H`` 控制。

取 ``f = 50 GHz``，背景磁场沿 ``z`` 轴：

.. code-block:: python

   from scirel.dielectric import cold_plasma_dielectric_tensor

   species = [
       {"density_m3": 1e19, "charge_c": -E, "mass_kg": M_E},
       {"density_m3": 1e19, "charge_c": E, "mass_kg": M_D},
   ]
   eps = cold_plasma_dielectric_tensor(50e9, [0.0, 0.0, 1.0], species)
   with np.printoptions(precision=4, suppress=True):
       print(eps)
   print("max |eps - eps^H| =", np.max(np.abs(eps - eps.conj().T)))
   print("eigvals =", np.linalg.eigvalsh(eps))
   b = np.array([0.0, 0.0, 1.0])
   print("b^H eps b =", b @ eps @ b)

实际输出：

.. code-block:: text

   [[0.5302+0.j     0.    +0.2629j 0.    +0.j    ]
    [0.    -0.2629j 0.5302+0.j     0.    +0.j    ]
    [0.    +0.j     0.    +0.j     0.6774+0.j    ]]
   max |eps - eps^H| = 0.0
   eigvals = [0.26728665 0.67744724 0.79318418]
   b^H eps b = (0.6774472367611433+0j)

这里 ``S = 0.5302``、``D_H = 0.2629``、``P = 0.6774``。张量是 Hermitian 的，因为两个组分的碰撞率都取默认的 0；``epsilon == epsilon^H`` 的偏差精确为 0。三个本征值是 ``S - D_H``、``P``、``S + D_H``；``b^H eps b`` 恰好回到 ``P``，这就是平行方向的响应。注意本征值都是正的并不自动说明波能传播：传播条件还要结合波矢和 Maxwell 旋度项。

冷模型也能给出一个“静电根”。令 ``B = 0``，张量退化为 ``P I``，而 ``P = 0`` 要求

.. code-block:: text

   omega^2 = sum_s omega_ps^2 = omega_p^2

也就是 ``omega = omega_p``，与波数无关。取 ``f_pe = wp/(2 pi)`` 计算：

.. code-block:: python

   f_pe = wp / (2*np.pi)
   eps_zero = cold_plasma_dielectric_tensor(f_pe, [0.0, 0.0, 0.0], species)
   print("Re diag(eps) at f_pe, B=0 =", np.diag(eps_zero).real)
   print("max off-diagonal =", np.max(np.abs(eps_zero - np.diag(np.diag(eps_zero)))))

实际输出：

.. code-block:: text

   Re diag(eps) at f_pe, B=0 = [-4.74351987e-10 -4.74351987e-10 -4.74351987e-10]
   max off-diagonal = 0.0

对角元不是精确的 0，而是约 ``-4.74e-10``。这不是新的物理修正，而是 ``f_pe`` 由 ``sqrt(wp2)`` 算出来、再乘 ``2 pi`` 回到角频率时的舍入残差。它提醒我们：**残差小只说明数值上接近根，不说明模型给出了严格零**。

**这一节不能推出什么。** 冷模型没有热运动，因此没有朗道阻尼，也没有有限拉莫尔半径修正；介电张量是局部的，不能描述空间色散或非局部响应。``P = 0`` 给出的是冷极限的静电根，不能拿它预测有限温度下根的虚部。冷模型在精确回旋共振处是奇异的；本库对贡献物种的精确零分母会整次拒绝，而不是返回一个被截断的有限值。张量的矩阵元依赖你给的基底，只有 ``b^H eps b`` 和本征结构在基底旋转下不变。

动理学静电响应：一个复频率点
----------------------------

现在换成动理学模型。考虑一维、无磁场、无碰撞的静电等离子体，电子平衡分布为

.. code-block:: text

   f0(v) = exp(-v^2/2) / sqrt(2*pi)

采用等离子体频率为 1、热速度标准差为 1 的归一化，波数 ``k`` 按逆 Debye 长度归一化。纵向介电函数为

.. code-block:: text

   epsilon(omega,k) = 1 + chi
   chi = (1 + z Z(z)) / k^2
   z = omega / (sqrt(2) k)
   D = k^2 epsilon

``Z`` 是等离子体色散函数。``D`` 只是 ``epsilon`` 乘以与频率无关的 ``k^2``，所以 ``epsilon = 0`` 和 ``D = 0`` 是同一个方程；不要把 ``D`` 当成独立方程，也不要拿 ``|D|`` 和 ``|epsilon|`` 直接比较。

先算一个复频率点 ``omega = 1.2 + 0.3i``、``k = 0.4``：

.. code-block:: python

   from scirel.kinetic import evaluate_maxwellian_electrostatic

   omega = 1.2 + 0.3j
   k = 0.4
   response = evaluate_maxwellian_electrostatic(omega, k)
   print(f"epsilon = {response['epsilon']:.9f}")
   print(f"D       = {response['D']:.9f}")
   print(f"z       = {response['z']:.9f}")
   print(f"error   = {response['epsilon_error']:.3e}")

实际输出：

.. code-block:: text

   epsilon = 0.412798173+0.597635601j
   D       = 0.066047708+0.095621696j
   z       = 2.121320344+0.530330086j
   error   = 9.358e-14

``omega/k = 3 + 0.75i``，除以 ``sqrt(2)`` 后得到 ``z = 2.121 + 0.530i``。``epsilon`` 的虚部不为零，说明这个试探频率不在根上。``D = 0.16 * epsilon``，实部和虚部都正好是 ``epsilon`` 的 0.16 倍；这就是 ``D = k^2 epsilon`` 的直接结果。

``epsilon_error`` 是数值误差估计，不是严格的误差上界。它在这里约 ``9.36e-14``，相对于 ``|epsilon|`` 很小，只说明这次求值的算术误差不大，不说明 ``epsilon`` 离零很近。

**这一节不能推出什么。** 一个复频率处的响应不是根；``epsilon`` 小也不等于“波存在”。这个模型是一维、无磁场、无碰撞、固定离子的 Maxwellian 静电模型；换分布、加磁场、加碰撞或换物种，都要换入口或换模型。``epsilon_error`` 不是区间证书，不能用来证明某个根不存在。

从响应到一条根：种子与残差
--------------------------

求根时，SciRel 不声称自动找到“物理上最重要的根”，而是从你给的种子出发，找到**这一条分支**上的根，并在返回前检查归一化残差。归一化残差大致是

.. code-block:: text

   r_norm = (|epsilon| + epsilon_error) / (1 + |chi|)

它把真空项和极化项的相对大小考虑进去，避免直接用 ``|D|`` 时被 ``k^2`` 缩放。接受一个根需要同时满足求解器成功、函数求值预算未超、``r_norm`` 小于容差，并且误差项本身小于容差的四分之一。

.. code-block:: python

   from scirel.kinetic import solve_maxwellian_electrostatic_mode

   solved = solve_maxwellian_electrostatic_mode(
       k=0.4,
       initial_omega=1.45 - 0.1j,
   )
   print(f"omega = {solved['omega']:.12f}")
   print(f"|epsilon| = {abs(solved['epsilon']):.3e}")
   print(f"normalized residual = {solved['normalized_residual']:.3e}")
   print(f"residual error gate = {solved['normalized_residual_error']:.3e}")
   print(f"evaluations = {solved['evaluations']}")

   other = solve_maxwellian_electrostatic_mode(
       k=0.4,
       initial_omega=-1.3 - 0.1j,
   )
   print(f"other = {other['omega']:.12f}")
   print(f"other normalized residual = {other['normalized_residual']:.3e}")

实际输出：

.. code-block:: text

   omega = 1.285056969654-0.066127958691j
   |epsilon| = 2.221e-15
   normalized residual = 1.110e-15
   residual error gate = 2.963e-13
   evaluations = 15
   other = -1.285056969654-0.066127958691j
   other normalized residual = 1.122e-15

``omega`` 的实部是振荡频率，虚部为负表示在 ``exp(-i omega t)`` 约定下随时间衰减。第一个根从 ``1.45 - 0.1i`` 出发，第二个根从 ``-1.3 - 0.1i`` 出发；两者实部符号相反、虚部相同，归一化残差都约 ``1e-15``。这说明在这个实波数下，正负实频两支都可以是方程的有效根。**残差小只能说明“这个数确实是该方程的一个根”，不能区分哪一支是你想要的模式。**

``evaluations = 15`` 是 MINPACK 的函数求值次数。``residual error gate = 2.96e-13`` 小于默认容差的四分之一，所以这次接受不是因为“残差碰巧小”，而是误差门也通过了。

**这一节不能推出什么。** 求根器不证明唯一性，不保证最低阻尼，也不保证全局最不稳定。换种子可能落到另一支，甚至收敛失败；这是分支选择问题，不是求解器“算错了”。残差是后向误差，不是物理阻尼率，也不是频率误差。

扫一条分支：连续性与分支陷阱
----------------------------

固定默认种子策略，扫描 ``k = 0.2, 0.4, 0.6, 0.8, 1.0``：

.. code-block:: python

   from scirel.kinetic import scan_gpdf_roots, evaluate_gpdf_small_k

   scan = scan_gpdf_roots(
       "langmuir",
       k_values=[0.2, 0.4, 0.6, 0.8, 1.0],
   )
   for kk, om, res in zip(scan["k"], scan["omega"], scan["dielectric_residual"]):
       print(f"k={kk:4.2f}  omega={om:.9f}  |res|={abs(res):.2e}")

   asym = evaluate_gpdf_small_k(0.2)
   print(f"asymptotic real = {asym['omega_real']:.6f}")
   print(f"asymptotic imag = {asym['omega_imag']:.6e}")

实际输出：

.. code-block:: text

   k=0.20  omega=1.063984341-0.000055107j  |res|=2.88e-14
   k=0.40  omega=1.285056970-0.066127959j  |res|=2.22e-15
   k=0.60  omega=1.545706755-0.264110338j  |res|=6.41e-16
   k=0.80  omega=1.799899318-0.534552362j  |res|=6.21e-16
   k=1.00  omega=2.045904866-0.851330459j  |res|=6.75e-16
   asymptotic real = 1.060000
   asymptotic imag = -6.513542e-05

这五个点在同一条连续分支上：波数增大，实频率升高，阻尼率增大。小波数时阻尼很弱，接近无碰撞的朗缪尔波；波数接近 1 时，阻尼已经不可忽略。这也是冷模型和动理学模型的差别：冷极限在归一化单位下给 ``omega = 1``，与 ``k`` 无关；而 ``k = 0.2`` 的动理学根是 ``1.063984 - 5.5107e-05 i``，实部已经有约 6.4% 的 Bohm-Gross 偏移，虚部是冷模型完全没有的朗道阻尼。作为独立检查，小波数渐近式给出

.. code-block:: text

   omega_r = 1 + 1.5 k^2
   omega_i = -sqrt(pi/8) exp(-1/(2k^2) - 1.5) / k^3

在 ``k = 0.2`` 处给出 ``1.060000 - 6.513542e-05 i``，而数值根是 ``1.063984 - 5.5107e-05 i``。实部只差约 0.4%，虚部差约 18%；这是领头渐近式与完整残差的差别，不是求解器误差。两者同量级可以作为检查，但不能互相替代。

现在看一个必须注意的分支陷阱。直接用默认种子扫 ``k = 0.1``：

.. code-block:: python

   bad = scan_gpdf_roots("langmuir", k_values=[0.1])
   print(bad["omega"])
   print(f"scan residual = {bad['dielectric_residual'][0]:.3e}")

实际输出：

.. code-block:: text

   [-1.01519753+8.57692635e-15j]
   scan residual = 2.015e-13

这个结果仍是方程的有效根，但它落在负实频分支上。更值得注意的是：如果改用 ``solve_maxwellian_electrostatic_mode``，把初值当成**频率** ``omega`` 传入，同样的 ``k = 0.1`` 可以找到正根：

.. code-block:: python

   positive = solve_maxwellian_electrostatic_mode(
       k=0.1,
       initial_omega=1.0 - 0.01j,
   )
   print(f"omega = {positive['omega'].real:.6f} + {positive['omega'].imag:.1e}j")
   print(f"normalized residual = {positive['normalized_residual']:.3e}")

实际输出：

.. code-block:: text

   omega = 1.015198 + 1.6e-17j
   normalized residual = 4.547e-13

正根和负根都存在，残差都在 ``1e-12`` 以下。差别来自种子：``scan_gpdf_roots`` 的 ``initial_guess`` 是**相位** ``x = omega/(sqrt(2) k)``，不是频率 ``omega``；默认相位种子 ``1 - 0.1j`` 在 ``k = 0.1`` 时对应的频率种子只有约 ``0.141 - 0.014i``，于是落到了负实频支。默认扫描网格又恰好包含 ``k = 0.1``，所以直接把默认结果画成曲线，会在第一个点看到一个“跳变”。这不是“物理波突然反向传播”，而是种子单位、求解盆地和扫描顺序共同造成的分支选择。

**这一节不能推出什么。** 一次扫描不枚举全部根，也不自动选择物理上最重要的分支；残差小不能排除另一支同样小的残差。小波数渐近式不是根求解器，不能外推到 ``k`` 接近 1。扫描失败会拒绝整个扫描，不返回部分结果；这不是“有些点没算出来”，而是调用者必须处理的失败。

固定极点近似：把 Z 换成有理式
-----------------------------

动理学张量的 Ronnmark 路径会把等离子体色散函数替换成固定阶数的有理近似：

.. code-block:: text

   Z_J(z) = sum_{j=1}^{J} b_j / (z - c_j)

极点 ``c_j`` 和留数 ``b_j`` 来自预置表。``evaluate_maxwellian_jpole`` 支持 ``J = 8, 12, 16, 24``；上半平面直接求和，下半平面用反射关系

.. code-block:: text

   Z(z) = conj(Z(conj(z))) + 2 i sqrt(pi) exp(-z^2),   Im(z) < 0

保持解析延拓。把近似值与精确的 ``Z`` 比较：

.. code-block:: python

   from scirel.kinetic import evaluate_maxwellian_jpole, evaluate_plasma_dispersion

   z = np.array([0.2 + 0.7j, 1.0 + 0.5j, 2.0 + 0.5j, -0.5 - 0.3j])
   exact = evaluate_plasma_dispersion(z)["Z"]
   print("z       =", z)
   for order in (8, 16, 24):
       approx = evaluate_maxwellian_jpole(z, order=order)["Z"]
       err = np.abs(approx - exact) / np.abs(exact)
       print(f"J={order:2d}  " + "  ".join(f"{e:.2e}" for e in err))

实际输出：

.. code-block:: text

   z       = [ 0.2+0.7j  1. +0.5j  2. +0.5j -0.5-0.3j]
   J= 8  3.18e-11  3.76e-09  4.41e-07  1.03e-11
   J=16  2.65e-14  1.66e-14  7.90e-15  9.09e-15
   J=24  7.41e-14  5.51e-14  1.89e-13  6.71e-14

``J = 8`` 在 ``z = 2 + 0.5i`` 处的相对误差约 ``4.4e-7``，已经比前两个点大两个数量级；``J = 16`` 把四个点都压到 ``1e-14`` 量级；``J = 24`` 反而略差于 ``J = 16``。第四个点 ``z = -0.5 - 0.3i`` 位于下半平面，走的是反射关系，误差与前三个点同量级。这不是“极点越多越不准”的普遍规律，而是有限精度下系数条件数、舍入和截断误差共同作用的结果。极点表的选择是近似元数据，不是全局精度证书。

**这一节不能推出什么。** 这四个点的误差小，不证明近似在整个复平面都好；靠近极点、强阻尼区或下半平面更深处需要单独检查。``J = 24`` 比 ``J = 16`` 差也不说明 ``J = 16`` 在所有点都更好。固定阶数近似不能替代收敛性研究，更不能因为某个根用 ``J = 8`` 算出来就认定它是物理模式。

磁化张量：两条路径在同一个波点
------------------------------

最后组装磁化动理学介电张量。对每个物种求和后得到

.. code-block:: text

   K_ij = delta_ij - sigma_ij / (i omega epsilon_0)

再加入 Maxwell 旋度项：

.. code-block:: text

   n_x = c k_x / omega,   n_z = c k_z / omega
   D_xx = K_xx - n_z^2
   D_yy = K_yy - (n_x^2 + n_z^2)
   D_zz = K_zz - n_x^2
   D_xz = D_zx = K_xz + n_x n_z
   det(D) = 0 给出本征模

``evaluate_kinetic_dispersion_relation`` 在同一个平衡快照上同时计算两条路径：有限谐波求和（``lmx = 5``）和 Ronnmark 固定 ``J = 8`` 极点。它接受 SI 物种参数、以 eV 为单位的 ``T00``、无量纲频率比 ``omega_frac``、无量纲垂直波数比 ``kx_frac``，以及**绝对**平行波数 ``kz``。``omega`` 和 ``kx`` 由入口自己用 ``wn``、``kn`` 导出，调用者不要同时传绝对值和比例。

取 ``omega_frac = 1000``、``kx_frac = 0.5``、``kz = 159 1/m``：

.. code-block:: python

   from scirel.kinetic import evaluate_kinetic_dispersion_relation

   result = evaluate_kinetic_dispersion_relation(
       ms=[M_E, M_D], qs=[-E, E], ns_unit=[1.0, 1.0], Ts_unit=[1.0, 0.5],
       B0=1.0, n00=1e19, T00=1000.0,
       omega_frac=1000.0, kz=159.0, kx_frac=0.5,
   )
   ds = result["determinant_sum_n"]
   dr = result["determinant_ronnmark"]
   C = scales["c"]
   print(f"omega = {result['omega']:.6e} rad/s")
   print(f"kx    = {result['kx']:.6f} 1/m")
   print(f"n_x   = {C*result['kx']/result['omega']:.3f}")
   print(f"n_z   = {C*159.0/result['omega']:.3f}")
   print(f"det_sum      = {ds:.6e}")
   print(f"det_ronnmark = {dr:.6e}")
   print(f"relative difference = {abs(ds - dr)/abs(dr):.3e}")
   print(f"max |K_yx + K_xy| = {abs(result['K_ronnmark'][1,0] + result['K_ronnmark'][0,1]):.1e}")
   print(f"max |det(D) - det| = {abs(np.linalg.det(result['D_ronnmark']) - dr):.3e}")

实际输出：

.. code-block:: text

   omega = 4.757179e+10 rad/s
   kx    = 154.225641 1/m
   n_x   = 0.972
   n_z   = 1.002
   det_sum      = 2.348809e+02-1.121402e-11j
   det_ronnmark = 2.348827e+02-3.879698e-04j
   relative difference = 8.160e-06
   max |K_yx + K_xy| = 0.0e+00
   max |det(D) - det| = 1.421e-13

``omega = 4.757e10 rad/s`` 对应约 7.57 GHz；``kx_frac = 0.5`` 乘上 ``kn = 308.45 1/m`` 得到 ``154.23 1/m``；``kz = 159 1/m`` 是绝对波数，不是比例。折射率 ``n_x = 0.972``、``n_z = 1.002``，接近真空光速尺度，但行列式并不接近零：``det_sum`` 约 ``234.88``，``det_ronnmark`` 约 ``234.88 - 3.88e-4 i``。所以这个波点**不是根**，这个调用只是评估行列式，不做求根。``n_x``、``n_z`` 接近 1 只说明相速度在光速尺度上，不是行列式为零的证据；``det`` 由全部张量分量共同决定。

两条路径在这个点的相对差别约 ``8.2e-6``；``det(D)`` 与返回的 Ronnmark 行列式差约 ``1.4e-13``，张量的反对称关系 ``K_yx = -K_xy`` 精确到 0。差别不大，但这只是一个点的一致性检查。

把 ``kx_frac`` 从 0.25 扫到 4，固定 ``omega_frac`` 和 ``kz``：

.. code-block:: python

   for kx_frac in (0.25, 0.5, 1.0, 2.0, 4.0):
       r = evaluate_kinetic_dispersion_relation(
           ms=[M_E, M_D], qs=[-E, E], ns_unit=[1.0, 1.0], Ts_unit=[1.0, 0.5],
           B0=1.0, n00=1e19, T00=1000.0,
           omega_frac=1000.0, kz=159.0, kx_frac=kx_frac,
       )
       a = r["determinant_sum_n"]
       b = r["determinant_ronnmark"]
       print(f"kx_frac={kx_frac:4.2f}  det_ron={b:.6e}  rel={abs(a-b)/abs(b):.3e}")

实际输出：

.. code-block:: text

   kx_frac=0.25  det_ron=2.125622e+02-3.698001e-04j  rel=1.847e-06
   kx_frac=0.50  det_ron=2.348827e+02-3.879698e-04j  rel=8.160e-06
   kx_frac=1.00  det_ron=3.452823e+02-4.605834e-04j  rel=1.464e-02
   kx_frac=2.00  det_ron=1.124469e+03-7.499993e-04j  rel=3.133e+00
   kx_frac=4.00  det_ron=9.624153e+03-1.891206e-03j  rel=2.031e+01

``kx_frac`` 从 0.25 增到 0.5，相对差别只有 ``1.8e-6`` 到 ``8.2e-6``；到 ``kx_frac = 1`` 已经约 1.5%，到 ``kx_frac = 2`` 相对差别超过 300%，两条路径的符号都可能不同。两条路径不是可以静默互换的“同一个答案”：有限谐波求和受 ``lmx = 5`` 截断影响，Ronnmark 路径受 ``J = 8`` 极点近似影响，各自的适用域不同。这个函数不做收敛性验证，也不判断哪一条更接近真实；它只把两条路径的结果并排返回，供调用者做交叉检查。

**这一节不能推出什么。** 行列式评估不是求根，``det`` 不为零不代表“没有波”，只代表这个波点不是根；``det`` 接近零也不自动给出模式身份。两条路径在某个小 ``kx_frac`` 上一致，不能外推到更大波数，也不能证明其中任何一条的绝对精度。张量分量依赖基底；有限谐波截断和极点阶数都需要独立的收敛检查。这个入口没有自动模式识别、没有全局根枚举，也没有物理有效性证书。

什么时候用哪一层
----------------

- 只需要平衡尺度和波矢投影：用 :doc:`../reference/generated/scirel.kinetic.species-equilibrium-scales` 和 :doc:`../reference/generated/scirel.geometry.planar-wavevector-projection`。
- 只需要快速估计 RF 背景下的各向异性介电响应，不关心动理学阻尼：用 :doc:`../reference/generated/scirel.dielectric.cold-plasma-tensor`。
- 想在一个复频率处检查 Maxwellian 静电响应：用 :doc:`../reference/generated/scirel.kinetic.maxwellian-electrostatic-mode`。
- 已有频率种子，想求一条根并检查残差：用 :doc:`../reference/generated/scirel.kinetic.maxwellian-electrostatic-solver`。
- 想沿同一分支扫多个波数：用 :doc:`../reference/generated/scirel.kinetic.generalized-root-scans`。
- 想用小波数渐近式做独立检查：用 :doc:`../reference/generated/scirel.kinetic.generalized-small-k`。
- 想用固定极点近似反复评估色散函数：用 :doc:`../reference/generated/scirel.kinetic.evaluate-maxwellian-jpole`；需要精确参考值时用 :doc:`../reference/generated/scirel.kinetic.plasma-dispersion-function`。
- 想在同一个磁化平衡快照上比较有限谐波和 Ronnmark 两条路径：用 :doc:`../reference/generated/scirel.kinetic.kinetic-dispersion-relation`。

本章没有覆盖离子声波、束流、任意速度分布、Vlasov 初值问题、多流体谱方法和复波数根扫描。这些主题各有自己的入口和归一化；不要因为本章的 ``langmuir`` 扫描能跑通，就把同样的种子、同样的单位或同样的“根即模式”假设搬到那些入口。

完整参数、失败行为与验证边界
----------------------------

本章只讲了每条路径上的一个代表点。完整参数、数组形状、异常类型和更大参数域的验证在 API 参考页；这里只列几个最容易踩的边界。

- 冷张量要求频率有限且严格为正，磁场形状为 ``(..., 3)``；物种是包含 ``density_m3``、``charge_c``、``mass_kg`` 的映射。零磁场是支持的，张量退化为各向同性；精确回旋共振会整次拒绝（``ColdPlasmaResonanceError``），不可表示的中间量会抛出 ``ColdPlasmaOverflowError``，而不是返回 NaN。
- 静电求根器接受 ``xtol``、``residual_tolerance``、``max_evaluations``；接受一个根需要求解器成功、预算未超、归一化残差和误差门同时通过。失败会抛 ``RuntimeError``，不返回部分结果；误差估计不是严格上界。
- 根扫描遇到任何一点失败会拒绝整个扫描；``k_values`` 的顺序会被保留，``initial_guess`` 的单位随家族不同（Langmuir 是相位，generalized 是频率），不要混用。扫描不保证唯一性、不保证最低阻尼，也不自动识别模式。
- 固定极点入口只接受 ``order = 8, 12, 16, 24``，其他阶数抛 ``ValueError``；下半平面用反射关系，极点处奇异；有限阶数的精度不是全局一致的。极点表选择本身不是精度证书。
- 磁化张量入口要求 SI 物种参数，``T00`` 以 eV 传入；``kz`` 是绝对波数，``kx_frac`` 和 ``omega_frac`` 才是相对 ``kn``、``wn`` 的比例。有限谐波截断、复波数支持和近零波数处理在不同入口之间并不相同，换入口前要确认模型和归一化。
- 本章所有数字都来自一个代表性算例，只证明这些调用在当前环境下能跑通并给出可解释的量级；它们不构成任意参数域的物理验证，也不替代合同里的验证边界。

.. seealso::

   如果你关心“根”如何随参数连续变化，而不只是一次扫描，可以继续读复波数根与扫描的参考页；如果你关心动理学张量在更一般的分布或磁化几何下的行为，请从本章的 API 参考进入具体函数页，先确认单位、符号约定和适用域，再构造新的算例。
