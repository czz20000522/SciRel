电磁学：从一圈电流到极向场
======================================================================

这一章跟着一个具体问题走：**给定一组轴对称线圈的几何和驱动电流，怎样在空间点上得到磁通与磁场；如果手里只有磁通网格，又怎样恢复极向场？**

路径是连续的：先算一个圆环在几个点上的 Green 响应，再把矩形截面离散成有序电流丝并按电流叠加，然后用 ``Device`` 组合一对线圈，接着从磁通网格恢复 ``B_R``、``B_Z``，最后把响应写成矩阵并说明导体边界修正。章末单独解释两种都叫 ``psi`` 的量为什么不能直接相减。

.. note::

   本章是教程，不是合同摘要。每个函数的完整签名、参数单位、失败行为和适用范围在章末的 API 参考页；代码只使用 SciRel 的公开函数。

准备：坐标、单位与 Green 响应
----------------------------------------------------------------------

在柱坐标 ``(R, phi, Z)`` 中考虑轴对称场：所有量不依赖 ``phi``。取矢量势的环向分量 ``A_phi(R, Z)``，定义

.. code-block:: text

   psi = R * A_phi
   B_R = -(1/R) * dpsi/dZ
   B_Z =  (1/R) * dpsi/dR

``psi`` 的单位是 Wb/rad（每弧度磁通），``B`` 的单位是 T。这里的“每弧度”不是可选的记账方式：一整个环向回路的磁通是 ``2*pi*psi``，所以 ``psi`` 和 ``Wb`` 不能直接混用。

一个半径为 ``R_s``、轴向位置为 ``Z_s``、权重为 ``w`` 的理想圆电流丝，对目标点 ``(R, Z)`` 的响应记为

.. code-block:: text

   (gpsi, gBR, gBZ)   单位：Wb/rad/A, T/A, T/A

它是**单位电流**的响应；权重已经乘进返回值。给定每根丝的电流 ``I_i``，总场就是 ``sum_i I_i * g_i``。这个线性关系是后面所有叠加的基础，也是本模型唯一允许的“组合”方式。

坐标一律用米，电流用安培。``R=0`` 是柱轴；轴上 ``B_R=0``，``psi=0``。理想电流丝没有有限半径，也没有导体内部；精确落在丝上的目标点在聚合入口按离散零自项处理，不是物理自场。

先算一个圆环：响应、对称性与轴线上限
----------------------------------------------------------------------

从最小的问题开始：半径 0.35 m 的圆环，通 1 A，在四个点上它的磁通和磁场是多少？

.. code-block:: python

   import numpy as np
   from scirel.field import circular_filament_green_response

   loop = [[0.35, 0.0, 1.0]]              # R (m), Z (m), weight
   targets = np.array([[0.20, -0.10], [0.20, 0.10], [0.0, 0.0], [0.35, 0.30]])
   g = circular_filament_green_response(loop, targets)

   print("gpsi (Wb/rad/A):", np.array2string(g["gpsi"], precision=9))
   print("gBR  (T/A)     :", np.array2string(g["gBR"], precision=9))
   print("gBZ  (T/A)     :", np.array2string(g["gBZ"], precision=9))

   mu0 = 4e-7 * np.pi
   axis = mu0 * 0.35**2 / (2.0 * (0.35**2)**1.5)
   print("axis analytic BZ/A:", axis)
   print("ratio:", g["gBZ"][2] / axis)

实际输出：

.. code-block:: text

   gpsi (Wb/rad/A): [3.408844654e-08 3.408844654e-08 0.000000000e+00 3.406704663e-08]
   gBR  (T/A)     : [-5.941571148e-07  5.941571148e-07  0.000000000e+00  4.269269023e-07]
   gBZ  (T/A)     : [1.800093910e-06 1.800093910e-06 1.795195802e-06 3.220178423e-07]
   axis analytic BZ/A: 1.7951958020513107e-06
   ratio: 0.9999999999999999

前两个目标点关于 ``Z=0`` 镜像：``gpsi`` 和 ``gBZ`` 相同，``gBR`` 反号。这正是圆环的镜像对称性：轴向场同向，径向场随场线绕行方向换号。轴上点的 ``gBR`` 为 0，``gBZ`` 与解析式

.. code-block:: text

   B_Z(axis) = mu0 * I * R_s^2 / (2 * (R_s^2 + Z^2)^(3/2))

在 ``I=1 A`` 时给出 ``1.795195802e-6 T``，比值是 1。这是对核函数和轴上极限的检查，不是对真实线圈的验证。

第四个点 ``(0.35, 0.30)`` 的 ``gBZ`` 是 ``3.220e-7 T/A``，约为 ``(0.20, 0.10)`` 的 1/5.6，符合“离丝越远越弱”的直觉。但它的 ``gpsi`` 是 ``3.4067e-8 Wb/rad/A``，和前两个点几乎一样。``psi`` 是磁通函数，不是场强；两个点可以落在相近的磁通面上，而 ``B`` 的大小差很多。

这一节不能推出：这些数是每安培的响应，要得到 1000 A 的结果需要乘 1000；模型没有有限丝半径、绝缘层、导体内部或丝上自场。聚合入口把精确重合的目标点当作离散零自项跳过，这不等于物理自场为零。

把截面离散成有序电流丝
----------------------------------------------------------------------

真实线圈有截面。这里把矩形截面近似为一组理想圆丝，先只看几何：

.. code-block:: python

   import numpy as np
   from scirel.field import discretize_rectangular_coil

   points = discretize_rectangular_coil(
       r0=0.35, z0=0.0, nr=3, nz=3, dr=0.06, dz=0.06
   )
   print(points)

实际输出：

.. code-block:: text

   [[ 0.29 -0.06]
    [ 0.29  0.  ]
    [ 0.29  0.06]
    [ 0.35 -0.06]
    [ 0.35  0.  ]
    [ 0.35  0.06]
    [ 0.41 -0.06]
    [ 0.41  0.  ]
    [ 0.41  0.06]]

输出顺序是**径向索引在外、轴向索引在内**：先固定 ``R=0.29``，走完 ``Z=-0.06, 0, 0.06``，再换到 ``R=0.35``。``dr`` 和 ``dz`` 是相邻丝的间距，不是截面的半宽；``nr=3, dr=0.06`` 给出的径向跨度是 ``0.12 m``，不是 ``0.06 m``。旋转以 ``(r0, z0)`` 为中心，角度用度。

这一节只生成了几何，没有电流、权重或匝数。9 根丝不自动等于 9 匝线圈；函数没有匝数或填充信息，它只是一个矩形点阵的离散表示。

这一节不能推出：加密点阵不自动等于更准确。不同的 ``nr, nz`` 是同一个截面的不同离散，除非你同时定义要比较的泛函（例如轴上 ``B_Z``）并做收敛序列，否则不能说哪一个“更真”。

按电流叠加：从单环到 9 根丝
----------------------------------------------------------------------

现在给 9 根丝分配总电流 1000 A，每根 ``1000/9 A``，权重保持 1，并在同样的目标点上比较单环和丝束：

.. code-block:: python

   import numpy as np
   from scirel.field import (
       circular_filament_green_response,
       dense_axisymmetric_green_response,
       discretize_rectangular_coil,
       superpose_current_green_field,
   )

   targets = np.array([[0.20, -0.10], [0.0, 0.0], [0.35, 0.30]])
   points = discretize_rectangular_coil(0.35, 0.0, 3, 3, 0.06, 0.06)
   rzw = np.column_stack((points, np.ones(len(points))))
   g = dense_axisymmetric_green_response(targets, rzw)       # (target, source)

   currents = np.full(len(points), 1000.0 / len(points))      # total 1000 A
   field = superpose_current_green_field(
       currents, g["gpsi"], g["gBR"], g["gBZ"]
   )
   print("matrix shape:", g["gBZ"].shape)
   print("BZ 9-filament (T):", np.array2string(field["BZ"], precision=9))

   single = circular_filament_green_response([[0.35, 0.0, 1000.0]], targets)
   print("BZ single loop (T):", np.array2string(single["gBZ"], precision=9))

实际输出：

.. code-block:: text

   matrix shape: (3, 9)
   BZ 9-filament (T): [0.001811259 0.001774477 0.000330107]
   BZ single loop (T): [0.001800094 0.001795196 0.000322018]

``dense_axisymmetric_green_response`` 返回 ``(target, source)`` 矩阵，``superpose_current_green_field`` 使用同一个方向合同：第一轴是目标、第二轴是源，沿源列与电流向量收缩，输出保持目标顺序。因此这里不需要转置。若矩阵是方阵，目标轴与源轴长度相同，误把源放在第一轴不会报错，却会静默地按错误轴收缩；调用时始终按 target-row/source-column 解释矩阵。

把电流摊到 ``R=0.29..0.41``、``Z=-0.06..0.06`` 后，轴上 ``B_Z`` 从 ``1.7952e-3 T`` 变成 ``1.7745e-3 T``，低约 1.2%；``(0.20,-0.10)`` 处高约 0.6%；``(0.35,0.30)`` 处高约 2.5%。这些差异不是“修正量”，而是两个不同的源模型：单环把所有电流放在一条丝上，丝束把同样的总电流摊开。

这一节不能推出：一个分辨率不能证明收敛；等权重也是一个建模选择。真实绕组有已知的填充和排列，不能只凭截面几何反推。若把 1000 A 同时当作每根丝的电流，总电流会变成 9000 A，这是最常见的量级错误之一。

用 Device 组合一对线圈
----------------------------------------------------------------------

单个线圈很少单独使用。``Device`` 按属性赋值顺序注册子源，并用共享网格求场。下面把两个相同的线圈放在 ``Z=+0.25`` 和 ``Z=-0.25``，先同向，再翻转下方电流：

.. code-block:: python

   import numpy as np
   from scirel.geometry import RectMesh
   from scirel.electromagnetism import Device, RectangularCoil

   mesh = RectMesh(rmin=0.0, rmax=0.65, nr=66, zmin=-0.4, zmax=0.4, nz=41)
   device = Device(mesh=mesh)
   device.upper = RectangularCoil(0.355, 0.25, 2, 2, 0.045, 0.03, current=250.0)
   device.lower = RectangularCoil(0.355, -0.25, 2, 2, 0.045, 0.03, current=250.0)

   def midplane(d):
       psi = d.psi().reshape(mesh.shape)
       br = d.BR().reshape(mesh.shape)
       bz = d.BZ().reshape(mesh.shape)
       iz = np.argmin(np.abs(mesh.Z[:, 0]))
       ir = np.argmin(np.abs(mesh.R[0, :] - 0.35))
       return psi[iz, ir], br[iz, ir], bz[iz, ir]

   print("children:", [type(s).__name__ for s in device.current_sets])
   print("currents:", device.current)
   psi, br, bz = midplane(device)
   print(f"same direction: psi={psi:.6e}  BR={br:.3e}  BZ={bz:.6e}")
   device.lower.current = -250.0
   psi, br, bz = midplane(device)
   print(f"opposite      : psi={psi:.6e}  BR={br:.6e}  BZ={bz:.3e}")

实际输出：

.. code-block:: text

   children: ['RectangularCoil', 'RectangularCoil']
   currents: [250. 250.]
   same direction: psi=8.656565e-05  BR=-1.271e-19  BZ=7.915351e-04
   opposite      : psi=1.482308e-21  BR=-1.145770e-03  BZ=4.659e-21

两个子源按赋值顺序出现，``device.current`` 返回 ``[250, 250]``。``psi()`` 返回的是展平后的目标点顺序；这里用 ``reshape(mesh.shape)`` 还原成 ``(nz, nr)`` 网格。``mesh.Z[:, 0]`` 和 ``mesh.R[0, :]`` 分别是轴向和径向坐标轴。

同向时，中平面中心的 ``B_Z`` 相加到 ``7.915e-4 T``，``B_R`` 因镜像对称抵消到 ``1e-19`` 量级；反向时，``B_Z`` 抵消到 ``5e-21``，``B_R`` 相加到 ``-1.146e-3 T``。这就是“同向对”和“反向对”的差别：前者在中心给出轴向场，后者给出径向场。把反向对叫四极场是一种有用的类比，但这里只算了一个点，不能据此宣称整个场就是四极场。

修改 ``device.lower.current`` 后，子源缓存失效，下一次调用会重新求响应；如果先保存了旧的 ``psi`` 数组，它是不会自动更新的。

``Device`` 也接受整体覆盖：标量电流会作用到所有子源，向量电流按子源顺序逐个对应。后者是检查“哪个子源拿到哪个电流”的最直接方式。

这一节不能推出：这是真空、理想丝、轴对称的线性叠加；没有等离子体响应、导体壳、线圈盒或三维几何。中心的零值是特定对称性的结果，不是全局的场零点。

从磁通网格恢复极向场
----------------------------------------------------------------------

``Device`` 已经能直接给出 ``B_R`` 和 ``B_Z``。但在很多工作流里，磁通才是被求解或保存的量；场需要从 ``psi`` 网格恢复。下面用同一对同向线圈，比较直接场和由 ``psi`` 差分得到的场：

.. code-block:: python

   import numpy as np
   from scirel.geometry import RectMesh
   from scirel.electromagnetism import Device, RectangularCoil
   from scirel.field import compute_poloidal_field_magnitude, poloidal_field_from_flux

   mesh = RectMesh(rmin=0.0, rmax=0.65, nr=66, zmin=-0.4, zmax=0.4, nz=41)
   device = Device(mesh=mesh)
   device.upper = RectangularCoil(0.355, 0.25, 2, 2, 0.045, 0.03, current=250.0)
   device.lower = RectangularCoil(0.355, -0.25, 2, 2, 0.045, 0.03, current=250.0)

   psi = device.psi().reshape(mesh.shape)
   bz = device.BZ().reshape(mesh.shape)
   br = device.BR().reshape(mesh.shape)
   rec = poloidal_field_from_flux(mesh.R, mesh.Z, psi)

   window = (mesh.R >= 0.15) & (mesh.R <= 0.25) & (np.abs(mesh.Z) <= 0.10)
   print("max |dBZ| in window (T):", np.abs(rec["B_Z"] - bz)[window].max())
   print("max |dBR| in window (T):", np.abs(rec["B_R"] - br)[window].max())

   iz = np.argmin(np.abs(mesh.Z[:, 0]))
   for r0 in (0.0, 0.15, 0.30, 0.45):
       ir = np.argmin(np.abs(mesh.R[0, :] - r0))
       print(f"R={r0:4.2f}  direct BZ={bz[iz, ir]:.6e}  recovered={rec['B_Z'][iz, ir]:.6e}")

   mag = compute_poloidal_field_magnitude(rec["B_R"], rec["B_Z"])
   print(f"B0_default = {mag['B0_default']:.6e} T")
   print(f"max |B|    = {mag['B'].max():.6e} T")

实际输出：

.. code-block:: text

   max |dBZ| in window (T): 1.821192022434786e-06
   max |dBR| in window (T): 2.2966746331177005e-06
   R=0.00  direct BZ=1.931877e-03  recovered=1.931621e-03
   R=0.15  direct BZ=1.790702e-03  recovered=1.789815e-03
   R=0.30  direct BZ=1.131914e-03  recovered=1.130874e-03
   R=0.45  direct BZ=2.094011e-04  recovered=2.096862e-04
   B0_default = 1.689570e-03 T
   max |B|    = 7.481667e-03 T

``poloidal_field_from_flux`` 要求 ``R``、``Z``、``psi`` 是等形状的二维数组，并且网格是严格的矩形网格、每轴至少 3 个点。它用稳定的局部差分求 ``dpsi/dZ`` 和 ``dpsi/dR``，再除以 ``R``。在 ``R=0`` 这一列，``B_R`` 被置零，``B_Z`` 用 ``2*(psi[:,1]-psi[:,0])/R[1]**2`` 的偶函数极限。

在选定的光滑窗口里，``B_Z`` 的最大绝对误差是 ``1.82e-6 T``，``B_R`` 是 ``2.30e-6 T``；窗口内 ``B_Z`` 的最大值约 ``2e-3 T``，所以相对误差约 ``0.1%``。轴上点的 ``1.931877e-3`` 与恢复值 ``1.931621e-3`` 相差约 ``0.013%``。这些差异来自有限差分截断，不是两套物理。

靠近线圈的点不在这个窗口里。那里场变化很快，``psi`` 的局部差分误差会显著增大。因此不要把恢复场直接用在绕组表面，也不要用它去判断“线圈附近的峰值”。

``compute_poloidal_field_magnitude`` 返回 ``B = hypot(B_R, B_Z)``，并把幅值下限截到 ``1e-30``；``B0_default`` 是这些幅值的中位数，不是中心场，也不是自动应用的归一化因子。这个下限是数值合同的一部分，不代表物理场真的非零。

这一节不能推出：恢复场不是独立测量，它只是同一份 ``psi`` 的导数；网格分辨率和差分格式决定了它的精度。``B0_default`` 只是一个描述性参考值。

响应矩阵、零自项与边界修正
----------------------------------------------------------------------

把响应写成矩阵，可以更清楚地看到线性叠加的轴。``get_gpsi`` 在给定 ``R,Z`` 节点上返回 ``(target, source)`` 的磁通矩阵；``green_response_matrices`` 则允许目标和源是两组不同的点：

.. code-block:: python

   import numpy as np
   from scirel.electromagnetism import get_gpsi, green_response_matrices
   from scirel.field import circular_filament_green_response

   R, Z = np.meshgrid([0.2, 0.35, 0.5], [-0.3, 0.0, 0.3])
   G = get_gpsi(R, Z)
   print("G shape:", G.shape)
   print("diagonal:", np.diag(G))
   print("symmetry error:", np.max(np.abs(G - G.T)))

   sources = np.array([[0.355, 0.25, 1.0], [0.355, -0.25, 1.0]])
   targets = np.array([[0.15, 0.0], [0.30, 0.10], [0.50, -0.05]])
   gpsi, gbr, gbz = green_response_matrices(targets, sources)
   currents = np.array([250.0, 250.0])
   print("matrix shapes:", gpsi.shape, gbr.shape, gbz.shape)
   print("BZ via matrix:", np.array2string(gbz @ currents, precision=9))

   single = circular_filament_green_response(sources, targets)
   print("BZ via kernel:", np.array2string(single["gBZ"] * 250.0, precision=9))

实际输出：

.. code-block:: text

   G shape: (9, 9)
   diagonal: [0. 0. 0. 0. 0. 0. 0. 0. 0.]
   symmetry error: 4.1359030627651384e-24
   matrix shapes: (3, 2) (3, 2) (3, 2)
   BZ via matrix: [4.487214325e-04 3.466000653e-04 7.971540153e-07]
   BZ via kernel: [4.487214325e-04 3.466000653e-04 7.971540153e-07]

``G`` 是 ``9x9``：目标行、源列，节点自身与自身的项按离散零自项约定置零。它的对称性误差是 ``4.1e-24``，这个同节点矩阵与同轴圆环的互感矩阵只差一个 ``2*pi`` 因子（这里存的是每弧度磁通）；但**对角线为零不是物理自感**。这个模型不提供有限截面导体的自感，把零对角元拿去做电感计算会得到错误结果。

``green_response_matrices`` 返回三元组；``dense_axisymmetric_green_response`` 和 ``circular_filament_green_response`` 返回 ``scirel._result.Result`` 映射。``Result`` 仍像字典一样按键读取，同时支持按字段名读取属性。两类接口的返回类型不同，读代码时要看清。矩阵收缩写成 ``gbz @ currents``，与逐丝核函数求和一致。

矩阵还可以用来做边界修正。下面的例子只有 3 个场点和 2 个边界采样，是一个线性代数演示，不是导体壁模型：

.. code-block:: python

   import numpy as np
   from scirel.field import correct_ideal_conductor_boundary_flux

   psi = np.array([3.0, -1.0, 2.0])          # 3 个场点上的未修正磁通
   S = np.array([[1.0, 0.0, 0.0], [0.0, 0.5, 0.5]])  # 2 个边界采样
   Gbb = np.diag([2.0, 4.0])                 # 边界->边界
   Gbf = np.array([[2.0, 0.0], [-1.0, 3.0], [1.0, 5.0]])  # 边界->场点

   out = correct_ideal_conductor_boundary_flux(psi, S, Gbb, Gbf)
   print("corrected flux:", out["corrected_field_flux"])
   print("boundary currents:", out["boundary_currents"])
   print("singular values:", out["singular_values"])
   print("effective rank:", out["effective_rank"])
   print("residual:", out["residual"], "norm:", out["residual_norm"])

实际输出：

.. code-block:: text

   corrected flux: [ 0.     0.125 -0.125]
   boundary currents: [-1.5   -0.125]
   singular values: [4. 2.]
   effective rank: 2
   residual: [0. 0.] norm: 0.0

调用先采样边界磁通 ``S @ psi``，解 ``Gbb @ I = -S @ psi``（用相对奇异值截断 ``rcond=1e-10``），再把 ``Gbf @ I`` 加回场点。这里 ``S @ Gbf`` 恰好等于 ``Gbb``，所以修正后边界采样为零、残差为零、有效秩为 2。

真实系统不一定这么整齐：截断 SVD 可能留下非零残差，函数会把残差和有效秩一起返回，而不是声称“理想导体一定把磁通完全抵消”。这一节不能推出：零残差是这个小系统的构造性质，不是物理正确性的证据；``S``、``Gbb``、``Gbf`` 的形状和数值仍要由具体问题给出。

两种 ``psi`` 不能直接相减
----------------------------------------------------------------------

还有一个容易踩的坑：同样叫 ``psi``，直接 Green 响应和径向积分给出的参考点不同。下面在 121 个径向点、7 个轴向点的网格上同时算两者：

.. code-block:: python

   import numpy as np
   from scirel.field import circular_filament_green_response, integrate_filament_vacuum_field

   filaments = [[0.355, 0.25, 250.0], [0.355, -0.25, 250.0]]
   r_grid, z_grid = np.meshgrid(
       np.linspace(0.05, 0.6, 121), np.linspace(-0.3, 0.3, 7)
   )
   integ = integrate_filament_vacuum_field(r_grid, z_grid, filaments)
   direct = circular_filament_green_response(
       filaments, np.column_stack((r_grid.ravel(), z_grid.ravel()))
   )
   psi_direct = direct["gpsi"].reshape(r_grid.shape)

   diff = integ["psi"] - psi_direct
   print("max variation within a row:", np.abs(diff - diff[:, :1]).max())
   print("offset (first row):", diff[0, 0])
   print("offset (middle row):", diff[3, 0])
   print("max |BZ difference|:", np.abs(integ["b_z"] - direct["gBZ"].reshape(r_grid.shape)).max())

实际输出：

.. code-block:: text

   max variation within a row: 1.3331215369254684e-08
   offset (first row): -6.283337877550199e-07
   offset (middle row): -6.025826977395476e-07
   max |BZ difference|: 0.0

``integrate_filament_vacuum_field`` 用同一个 Green 核求 ``B_R``、``B_Z``，然后对 ``R*B_Z`` 做累积梯形积分，并把第一个径向节点当作 ``psi=0``。直接 Green 响应的 ``psi`` 则以柱轴为零点。两者之差在每一行上是一个常数，等于 ``-psi_direct(R0)``；在这个网格上，行内变化只有 ``1.3e-8``，剩下的差异是积分求积误差。

``B_Z`` 的最大差是 0，因为两者用的是同一个核；如果只看 ``B_Z``，你会以为两套结果完全一致，然后拿 ``psi`` 直接相减，得到一个随 ``Z`` 变化的偏移。正确做法是先减去各自的参考值，或者从一开始就明确“这个 ``psi`` 的零点在哪里”。

两种 ``psi`` 都不含 ``2*pi``。整个环向回路的磁通是 ``2*pi*psi``；把 Wb/rad 当 Wb 用，会差一个 ``2*pi``。这一节不能推出：径向积分是一种数值求积，不是新的物理模型；它的精度取决于径向网格，第一节点只是参考点，不是物理边界条件。

什么时候用哪个函数
----------------------------------------------------------------------

- 只想要一个圆环或一小组加权丝在点上的响应：:doc:`../reference/generated/scirel.field.circular-filament-green`。
- 想直接拿 ``compute_greens`` 的三元组响应（目标与正半径源完全重合时会抛错）：:doc:`../reference/generated/scirel.electromagnetism.circular-filament-green`。
- 已经有丝位置和电流，想按源列做矩阵收缩：:doc:`../reference/generated/scirel.field.current-green-superposition`；需要显式矩阵时用 :doc:`../reference/generated/scirel.field.dense-axisymmetric-green`。
- 只想把矩形截面变成有序点：:doc:`../reference/generated/scirel.field.rectangular-coil-filaments`；需要带电流和网格的源对象时用 :doc:`../reference/generated/scirel.electromagnetism.rectangular-coil`。
- 想直接给一组矩形线圈记录并一次得到网格场：:doc:`../reference/generated/scirel.field.multi-coil-vacuum-field`。
- 想按名字注册多个子源、共享网格并整体覆盖电流：:doc:`../reference/generated/scirel.electromagnetism.device`；任意点源用 :doc:`../reference/generated/scirel.electromagnetism.arbitrary-points`。
- 想从 ``psi`` 网格恢复极向场和幅值：:doc:`../reference/generated/scirel.field.poloidal-field-from-flux`、:doc:`../reference/generated/scirel.field.poloidal-field-magnitude`。
- 想构造同节点磁通矩阵或目标-源响应矩阵：:doc:`../reference/generated/scirel.electromagnetism.loop-flux-matrix`、:doc:`../reference/generated/scirel.electromagnetism.green-response-matrices`。
- 想做截断 SVD 的边界修正：:doc:`../reference/generated/scirel.field.ideal-conductor-boundary`。
- 想在镜像对称的 Z 网格上构造等离子体磁通响应矩阵：:doc:`../reference/generated/scirel.field.mirror-plasma-green`。
- 想走椭圆积分分支，自己检查模数、``K``、``E`` 和闭合形式：:doc:`../reference/generated/scirel.field.coil-green-geometry`、:doc:`../reference/generated/scirel.field.complete-elliptic-integrals-approx`、:doc:`../reference/generated/scirel.field.filament-coil-green-field`。
- 想用径向积分得到以第一径向节点为零点的 ``psi``：:doc:`../reference/generated/scirel.field.filament-vacuum-field`。
- 想用固定几何的磁环或装置：:doc:`../reference/generated/scirel.electromagnetism.magnet-ring`、:doc:`../reference/generated/scirel.field.permanent-ring-filaments`、:doc:`../reference/generated/scirel.electromagnetism.trex-coil`、:doc:`../reference/generated/scirel.electromagnetism.brb`、:doc:`../reference/generated/scirel.electromagnetism.wham`。这些是几何与丝排列，不是材料磁化或实验标定。

常见误用与边界
----------------------------------------------------------------------

- **单位**：``R,Z`` 用米。若把厘米当米传，场和磁通会差几个量级，而且不会报错。
- **总电流与每丝电流**：``current`` 是每根丝（或每个子源）的电流；``weights`` 是无量纲权重。先决定总电流怎么分，再传电流。把总电流同时传给每根丝会放大总电流。
- **轴顺序**：``dense_axisymmetric_green_response`` 和 ``green_response_matrices`` 都是 ``(target, source)``；``superpose_current_green_field`` 按第二轴（源列）与电流收缩并保留目标行。不要转置响应矩阵。
- **零对角元**：``get_gpsi`` 和聚合入口的零自项是离散约定，不是有限导体的自感。不要用它算电感或近丝场。
- **重合点**：``compute_greens`` 在目标与正半径源完全重合时抛 ``ValueError``；``circular_filament_green_response`` 把这种点当作零自项跳过。两者不是同一个失败约定。
- **磁通零点**：直接 Green ``psi`` 与径向积分 ``psi`` 的参考点不同；先对齐零点，再比较。
- **``B0_default``**：它是幅值数组的中位数，不是自动归一化；``1e-30`` 下限是数值合同，不是物理场。
- **边界修正**：``correct_ideal_conductor_boundary_flux`` 是截断 SVD 的线性代数修正；零残差不等于真实导体壁正确。
- **固定几何**：``MagnetRing`` 是带符号的丝近似，不是磁化模型；``TREXCoil``、``BRB``、``WHAM`` 保留几何常数，不提供实验装置标定。

本章的模型边界是：真空、轴对称、理想圆电流丝、线性叠加。它不包含有限丝半径、导体内部、磁芯、等离子体响应、三维几何、线圈盒、力或能量。需要这些时，应回到具体函数页确认模型，而不是把这里的数直接外推。

.. seealso::

   如果下一步关心的是磁通如何与等离子体平衡或诊断量连接，可以先回到 :doc:`/user-guide/index` 选择领域；每个函数页给出完整签名、失败行为和验证边界。
