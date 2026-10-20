等离子体平衡：从压强剖面到磁通反馈
====================================

这一章回答一个具体问题：**给定一条中平面压强剖面，怎样把它变成磁通上的压强关系，并用环向电流的 Green 响应做一次（或有限次）平衡反馈？**

我们沿着一条连续路径走：先由压强样本构造 ``P(psi)`` 与 ``dP/dpsi``，再用一个真实的圆环响应矩阵做一次 Picard 更新，然后进入带双残差门的复合入口，最后用一个受控的对角响应说明“收敛”到底检查了什么。每一步都给出实际运行输出，并指出它不能证明什么。

.. note::

   本章是教程，不是合同摘要。函数的完整签名、参数单位、失败行为和适用范围在章末链接的 API 参考页；教程代码只调用 SciRel 的公开函数。

准备：坐标、单位和一条压强剖面
------------------------------

采用柱坐标 ``(R, phi, Z)``，并假设轴对称。极向磁通取

.. code-block:: text

   psi(R, Z) = R * A_phi

单位是 ``Wb/rad``；环向电流 ``I`` 的单位是 ``A``；Green 响应 ``g_psi`` 把电流映射为 ``psi``，单位是 ``Wb/rad/A``。本章所有公式都不额外乘 ``2*pi``，如果你习惯使用整圈磁通，必须自己把因子和单位一起换算。

在本库的离散约定里，平衡的压强部分写成 ``P = P(psi)``。离散电流取

.. code-block:: text

   I_target = R * (dP/dpsi) * dR * dZ

这是把环向电流分配到每个网格面元上的离散闭合关系；它本身不是完整的 Grad–Shafranov 解。总磁通由两部分组成：

.. code-block:: text

   psi_next = g_psi @ I_new + psi_vac

先在一个 ``[Z, R]`` 的规则网格上定义一条线性下降、并在 ``R=0.8`` 处精确为零的压强剖面：

.. code-block:: python

   import numpy as np
   from scirel.equilibrium.pressure_flux_state import build_pressure_flux_state

   r_grid, z_grid = np.meshgrid(
       np.linspace(0.2, 0.8, 4),
       [-0.1, 0.0, 0.1],
   )

   def pressure(radius):
       return max(1.0e6 * (1.0 - radius / 0.8), 0.0)

   for radius in np.linspace(0.2, 0.8, 4):
       print(f"R={radius:.1f}  P={pressure(radius):.0f} Pa")

实际输出：

.. code-block:: text

   R=0.2  P=750000 Pa
   R=0.4  P=500000 Pa
   R=0.6  P=250000 Pa
   R=0.8  P=0 Pa

这里的零是**精确零**，不是 ``1e-12`` 之类的近似零；后面的边界判断依赖这一点。网格也必须包含一条完整的 ``Z=0`` 行，因为压强样本只从这条中平面读取。

这一节不能推出：压强剖面的物理合理性、装置的真实几何，或者 ``psi = R`` 就是某个真实平衡的磁通。我们只是选定了一套自洽的输入约定。

从压强样本到 ``dP/dpsi``
--------------------------

``build_pressure_flux_state`` 做三件事：按物理半径排序中平面样本；在第一个精确零压强点之前截取磁通前缀；用三次样条拟合 ``P(psi)`` 并给出 ``dP/dpsi``。它还返回一个全零的电流向量，那只是“尚未求解”的占位，不是平衡电流。

.. code-block:: python

   state = build_pressure_flux_state(
       r_grid, z_grid, r_grid.copy(), pressure
   )
   print("dP/dpsi [Pa/(Wb/rad)]:")
   print(state["pressure_derivative"].reshape(3, 4).round(1))
   print(f"psi_edge = {state['psi_edge']:.6f} Wb/rad")
   print(f"limiter_index = {state['limiter_index']}")
   print("psi_samples =", state["pressure_of_psi"]["psi_samples"])

实际输出：

.. code-block:: text

   dP/dpsi [Pa/(Wb/rad)]:
   [[-1250000. -1250000. -1250000. -1250000.]
    [-1250000. -1250000. -1250000. -1250000.]
    [-1250000. -1250000. -1250000. -1250000.]]
   psi_edge = 0.800000 Wb/rad
   limiter_index = 3
   psi_samples = [0.2 0.4 0.6 0.8]

因为这里 ``psi = R``，所以 ``P = 1e6 * (1 - psi/0.8)``，导数恒为 ``-1.25e6 Pa/(Wb/rad)``。三个 Z 行相同，是因为输入磁通还没有被电流改变；这不是说二维平衡已经满足。``limiter_index = 3`` 是中平面样本按半径排序后的第 4 个点（从 0 开始计数），不是 C 顺序扁平数组的下标，也不是网格的行号。``psi_edge = 0.8`` 来自第一个精确零压强样本。

``pressure_of_psi`` 里的样条在采样区间外按零外推；导数在 ``psi > psi_edge`` 的单元被清零。这个截断是离散约定，不是从物理边界条件自动推出的。

这一节不能推出：``dP/dpsi`` 在整个二维区域都等于这个常数；零压强边界之外仍有压强；样条拟合可以替代真实的压强输运模型。它只说明在这组样本和这个截断规则下，导数是多少。

一次 Picard 更新：电流、Green 响应与残差
----------------------------------------

现在给一个真空响应矩阵。``get_gpsi`` 把网格上的每个点当作一条单位电流的圆环源，返回目标点上的 ``psi = R * A_phi`` 响应；对角线为零，因为线电流的自场不在这个离散响应里。真实装置当然需要更合适的真空场或平衡响应，这里先用它把“电流 -> 磁通”这一步跑通。

.. code-block:: python

   from scirel.electromagnetism import get_gpsi
   from scirel.equilibrium.isotropic_picard_step import pressure_flux_picard_step

   g_psi = get_gpsi(r_grid, z_grid)
   step = pressure_flux_picard_step(
       r_grid, z_grid, r_grid.copy(), r_grid.copy(), g_psi,
       state["pressure_derivative"], state["psi_edge"],
       state["zero_currents"], 0.0,
   )
   print("plasma_currents [A]:")
   print(step["plasma_currents"].reshape(3, 4).round(1))
   print("psi_next [Wb/rad]:")
   print(step["psi_next"].round(6))
   print(f"residual = {step['residual']:.6e}")

实际输出：

.. code-block:: text

   plasma_currents [A]:
   [[ -5000. -10000. -15000. -20000.]
    [ -5000. -10000. -15000. -20000.]
    [ -5000. -10000. -15000. -20000.]]
   psi_next [Wb/rad]:
   [[0.197026 0.389587 0.581105 0.77836 ]
    [0.196783 0.388643 0.57915  0.77572 ]
    [0.197026 0.389587 0.581105 0.77836 ]]
   residual = 6.901919e-02

电流正好是 ``-25000 * R``：面元面积是 ``dR * dZ = 0.2 * 0.1 = 0.02``，导数 ``-1.25e6``，所以 ``R * (-1.25e6) * 0.02 = -25000 R``。负号来自压强随 ``psi`` 下降。磁通在中平面外缘从 ``0.8`` 降到约 ``0.77836``；上下两行与中平面略有差别，因为 Green 矩阵把不同 Z 位置的电流耦合了进来。

``residual = 6.9e-2`` 是

.. code-block:: text

   ||psi_next - psi_state||_2 / |psi_edge|

它衡量“这一步把磁通改了多少”，不是一个已经收敛的误差，也不是与真实平衡的偏差。对于 ``relax=0`` 的单步，它只描述这一步的步长。

这一节不能推出：再走一步就会收敛；这个 Green 响应足以描述装置；或者电流符号已经对应了正确的物理环向方向。它只证明一次电流组装和一次 Green 收缩在这组输入上是有限且可复现的。

复合入口：为什么“跑完迭代”不等于平衡
--------------------------------------

``solve_isotropic_pressure_flux`` 把上面的步骤放进一个有上限的循环，并同时检查两个残差：

- ``residual``：相邻两次磁通更新的相对范数；
- ``closure_residual``：当前电流与“由新磁通重建的压强目标电流”之间的相对差。

两者都小于 ``tol`` 才算收敛。下面仍用同一个 ``get_gpsi`` 响应，取 ``relax=0.5``、``maxiter=20``：

.. code-block:: python

   from scirel.equilibrium import solve_isotropic_pressure_flux

   result = solve_isotropic_pressure_flux(
       r_grid=r_grid, z_grid=z_grid, pressure_of_radius=pressure,
       psi_vac=r_grid.copy(), g_psi=g_psi,
       tol=1e-8, maxiter=20, relax=0.5,
   )
   print(f"status = {result['status']}")
   print(f"iterations = {result['iterations']}")
   print(f"residual = {result['residual']:.6e}")
   print(f"closure_residual = {result['closure_residual']:.6e}")
   print(f"failure_reason = {result['failure_reason']}")
   print("last update residuals:", np.round(result["residual_history"][-4:], 6))
   print("last closure residuals:", np.round(result["closure_residual_history"][-4:], 6))

实际输出：

.. code-block:: text

   status = maxiter
   iterations = 20
   residual = 7.796787e-03
   closure_residual = 1.912028e-01
   failure_reason = maxiter_reached
   last update residuals: [0.010253 0.007003 0.008676 0.007797]
   last closure residuals: [0.334588 0.499996 0.372273 0.191203]

这里没有收敛。``iterations = 20`` 只表示用完了预算，``status = maxiter`` 才是结论。更新残差已经在 ``1e-2`` 附近徘徊，但闭合残差仍在 ``0.19`` 到 ``0.50`` 之间振荡：当前电流不能复现由更新后磁通重建的压强目标。原因不是某一个数字“算错了”，而是这套组合还不自洽：``get_gpsi`` 产生的磁通把中平面形状改变得不再是简单的 ``psi = R``，于是由同一组压强样本重建的样条导数偏离了原来的线性导数；同时 ``relax=0.5`` 的阻尼让电流始终落后于目标。两个残差必须同时下降，单看较小的更新残差会误判为“快收敛了”。

这一节不能推出：这个物理模型一定不成立，或者换一台装置也会失败。它说明的是，给定的压强剖面、Green 响应、样条表示和阻尼策略在这组离散输入上没有同时满足两个门；也不能把 ``closure_residual`` 当作实验误差或稳定性判据。

一个受控的收敛案例：残差门在检查什么
--------------------------------------

为了把“迭代代数”和“真空响应是否合适”分开，只把响应换成一个对角矩阵：

.. code-block:: text

   g_psi = 4.0e-8 * I

它表示每个单元的电流只在自己的位置上产生一点磁通，显然不是真实的真空场，只用来隔离数值路径。其余输入不变：

.. code-block:: python

   controlled = solve_isotropic_pressure_flux(
       r_grid=r_grid, z_grid=z_grid, pressure_of_radius=pressure,
       psi_vac=r_grid.copy(),
       g_psi=4.0e-8 * np.eye(r_grid.size),
       tol=1e-10, maxiter=20, relax=0.0,
   )
   print(f"status = {controlled['status']}")
   print(f"iterations = {controlled['iterations']}")
   print(f"residual = {controlled['residual']:.6e}")
   print(f"closure_residual = {controlled['closure_residual']:.6e}")
   print("psi midplane [Wb/rad]:", controlled["psi"][1].round(6))
   print("currents midplane [A]:", controlled["plasma_currents"][1].round(2))
   print("update history:", np.round(controlled["residual_history"], 12))

实际输出：

.. code-block:: text

   status = converged
   iterations = 4
   residual = 2.386091e-12
   closure_residual = 1.005293e-12
   psi midplane [Wb/rad]: [0.1998   0.3996   0.599399 0.799199]
   currents midplane [A]: [ -5005.01 -10010.02 -15015.03 -20020.04]
   update history: [2.37408233e-03 2.37646100e-06 2.38100000e-09 2.00000000e-12]

对角响应把磁通写成 ``psi = (1 - eps) * R``；代入 ``P(psi)`` 后导数变为 ``-1.25e6/(1 - eps)``，于是电流是 ``-25000 R/(1 - eps)``，固定点满足 ``eps ≈ 1e-3``。迭代的收缩因子约为 ``4e-8 * 25000 = 1e-3``，所以更新残差每步缩小约一千倍，四次就落到 ``1e-12``。输出的 ``psi`` 和电流也确实对应 ``eps ≈ 0.001``：外缘 ``0.8 * 0.999 ≈ 0.7992``，电流约 ``-5005 A``（而不是 ``-5000 A``）。

这一节不能推出：对角响应描述了真实电磁场；这个固定点就是装置的平衡；或者“收敛”意味着唯一解、稳定平衡。``converged`` 只说明在这组离散输入和这两个残差门下，迭代停止并同时满足两个判据。真实响应下是否收敛，仍要回到上一节那样的实际计算去检查。

易错点
------

- **精确中平面与精确零边界**：``Z=0`` 行必须完整，第一个零压强样本必须精确为零。用 ``1e-12`` 代替零会被拒绝。
- **磁通坐标的因子**：``psi`` 是 ``R * A_phi``（每弧度），Green 矩阵和 ``dP/dpsi`` 必须使用同一个坐标。不要把整圈韦伯和每弧度值混在一起，也不要额外补一个 ``2*pi``。
- **``limiter_index`` 的含义**：它是按物理半径排序后的中平面样本序号，不是 C 顺序扁平下标；存储顺序可以反过来，物理遍历顺序不变。
- **``plasma_mask`` 的方向**：布尔掩码为真时**抑制**该单元的压强导数，它不是“标记等离子体内部”的开关；边界仍由第一个精确零压强点决定。
- **残差不是误差**：``residual`` 是相邻磁通之差的归一化范数，``closure_residual`` 是电流与压强目标之差；两者小只说明离散方程在这组输入上闭合，不说明模型正确。
- **不要用 ``relax=1`` 冻结迭代**：复合入口要求 ``0 <= relax < 1``；``relax=1`` 会保留旧电流而不形成更新，不能当作“完全隐式”步。
- **``maxiter`` 是预算**：``status = maxiter`` 时末态只是预算用完的状态；不能把 ``iterations`` 当作收敛次数。

什么时候用哪个函数
------------------

- 只想把一条中平面压强剖面变成 ``P(psi)`` 和 ``dP/dpsi``：用 :doc:`../reference/generated/scirel.equilibrium.pressure-flux-state`。
- 已有磁通、压强导数和 Green 矩阵，只想看一次电流/磁通更新与残差：用 :doc:`../reference/generated/scirel.equilibrium.isotropic-picard-step`。
- 想跑一个有上界的压力—电流反馈并同时检查两个残差：用 :doc:`../reference/generated/scirel.equilibrium.isotropic-pressure-flux`。
- 需要构造或核对真空圆环响应矩阵：用 :doc:`../reference/generated/scirel.electromagnetism.loop-flux-matrix`。
- 想看各向异性压强如何进入力平衡和环向电流，而不是各向同性闭合：从 :doc:`../reference/generated/scirel.equilibrium.anisotropic-force-balance` 和 :doc:`../reference/generated/scirel.equilibrium.anisotropic-toroidal-current` 继续；它们与本章的 ``P(psi)`` 单步不是同一套模型。
- 想单独诊断迭代残差：用 :doc:`../reference/generated/scirel.diagnostics.picard-flux-residual`。

完整参数、失败行为、适用范围与验证边界
--------------------------------------

本章的数值只对应这套离散设定：规则 ``[Z, R]`` 网格、一条完整 ``Z=0`` 行、非负且精确归零的中平面压强、至少四个严格递增的磁通前缀样本，以及调用者提供的方阵 Green 响应。函数不会替你验证网格的物理合理性、压强剖面的来源、Green 矩阵是否来自真实真空场，也不会证明连续极限收敛、MHD 稳定性或约束性能。

复合入口只保证在给定输入下执行有界反馈并报告两个残差；``converged`` 不是“物理上正确的平衡”的同义词，``maxiter`` 也不是“模型失败”的证明。需要异常类型、参数形状、单位表和更大参数域的证据时，请从本章的 API 参考进入具体函数页。

本章没有展开各向异性力平衡、各向异性 Picard 反馈、镜约束闭合、表格压强闭合以及约化 Hall 漂移等路径；它们各自有独立的压强张量、边界和停止条件，不能把这里的 ``dP/dpsi`` 或残差直接套用。

.. seealso::

   继续读 :doc:`../reference/generated/scirel.equilibrium.axisymmetric-anisotropic-picard`，看各向异性电流与磁通反馈如何组合；也可以回到 :doc:`/user-guide/index` 选择其他领域。
