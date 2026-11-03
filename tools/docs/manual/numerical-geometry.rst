数值几何与场采样：从一张 R-Z 网格到一条磁通面
==============================================

这一章回答一个具体问题：**已经有一张轴对称场在 ``R-Z`` 网格上的节点值，怎样在任意点上取值、沿一条磁通面累加弧长和 ``dl/B``、再把结果映射到笛卡尔求解网格？**

读完你应该能判断三件事：什么时候可以把节点值插值到点上，什么时候“看起来闭合”的等值线其实没有闭合，以及把场映射到求解网格后哪些点只是被夹到边界、并不能当作已知物理。整章走一条连续路径：网格查询 → 等值线与场线 → 路径积分 → 笛卡尔映射。

.. note::

   本章是教程，不是合同摘要。每个入口的完整签名、失败行为和适用范围在章末链接的 API 参考页。代码按顺序累加；单独复制某一节时，请保留前面的模型定义。

模型：一个磁通面为圆的解析场
----------------------------

为了避免把几何问题和平衡求解混在一起，这一章使用一个手工构造的轴对称场。取 ``B0 = 2 T``、``R0 = 1.5 m``、``r_s = 0.4 m``，定义

.. code-block:: text

   psi(R,Z) = B0/(2*R0) * ((R-R0)^2 + Z^2)
   B_R(R,Z) = -B0*Z/(R*R0)
   B_Z(R,Z) =  B0*(R-R0)/(R*R0)
   |B|(R,Z) =  B0/(R*R0) * sqrt((R-R0)^2 + Z^2)

``psi`` 的单位是 ``Wb/rad``，磁场单位是 ``T``，长度单位是 ``m``。等 ``psi`` 线是以 ``(R0, 0)`` 为圆心、半径 ``r`` 的圆；在 ``r = r_s`` 的磁通面上，``|B| = B0*r_s/(R*R0)``。

这个场是**制造场**：它让磁通面恰好是圆，便于用解析值检查每一步；它不是 Grad–Shafranov 方程的解，也不对应真实装置。

两个坐标约定要先记住：

- ``sample_rectilinear_field`` 的网格数组按 ``[Z, R]`` 索引，查询点按 ``[R, Z]`` 排列；
- ``map_axisymmetric_equilibrium_to_cartesian_grid`` 的平衡场数组按 ``[R, Z]`` 索引，输出是 ``(x, y, z)`` 网格上的三维矢量。

在网格上查询：节点精确，单元内部不精确
--------------------------------------

先建一张 ``R in [0.9, 2.1] m``、``Z in [-0.8, 0.9] m`` 的规则网格，把解析 ``psi`` 放在节点上，再用双线性采样器查询。为了看插值误差，分别在节点、单元中心和三种分辨率下取值。

.. code-block:: python

   import numpy as np
   from scirel.geometry import sample_rectilinear_field

   B0, R0, rs = 2.0, 1.5, 0.4

   def psi_analytic(R, Z):
       return B0/(2*R0)*((R-R0)**2 + Z**2)

   def grid(nr, nz):
       r = np.linspace(0.9, 2.1, nr)
       z = np.linspace(-0.8, 0.9, nz)
       return np.meshgrid(r, z)

   def bilinear_error(nr, nz):
       R, Z = grid(nr, nz)
       psi = psi_analytic(R, Z)
       rc = 0.5*(R[0, :-1] + R[0, 1:])
       zc = 0.5*(Z[:-1, 0] + Z[1:, 0])
       RC, ZC = np.meshgrid(rc, zc)
       points = np.column_stack([RC.ravel(), ZC.ravel()])
       sampled = sample_rectilinear_field(R, Z, psi, points)['samples']
       return np.max(np.abs(sampled - psi_analytic(RC, ZC).ravel()))

   for nr, nz in ((17, 11), (33, 22), (65, 43)):
       print(f"nr={nr:3d} nz={nz:3d}  max error = {bilinear_error(nr, nz):.3e}")

   R, Z = grid(49, 34)
   psi = psi_analytic(R, Z)
   nodes = np.array([[R[10, 20], Z[10, 20]], [R[28, 4], Z[28, 4]]])
   print("node samples =", sample_rectilinear_field(R, Z, psi, nodes)['samples'])
   print("node analytic =", psi_analytic(nodes[:, 0], nodes[:, 1]))

   mid = np.array([[(R[10, 20] + R[10, 21])/2, (Z[10, 20] + Z[11, 20])/2]])
   sample = sample_rectilinear_field(R, Z, psi, mid)['samples'][0]
   exact = psi_analytic(mid[:, 0], mid[:, 1])[0]
   print("midpoint sample =", round(sample, 8))
   print("midpoint analytic =", round(exact, 8))
   print("midpoint error =", sample - exact)

   try:
       sample_rectilinear_field(R, Z, psi, [[2.2, 0.0]])
   except ValueError as exc:
       print("outside ->", exc)

实际输出：

.. code-block:: text

   nr= 17 nz= 11  max error = 5.754e-03
   nr= 33 nz= 22  max error = 1.327e-03
   nr= 65 nz= 43  max error = 3.316e-04
   node samples = [0.06075911 0.44180594]
   node analytic = [0.06075911 0.44180594]
   midpoint sample = 0.0504027
   midpoint analytic = 0.04985623
   midpoint error = 0.0005464684726048316
   outside -> diagnostic point lies outside the R-Z grid

节点上的样本与解析值逐位一致，因为双线性插值在角点上就是节点值本身；单元中心则出现 ``5.46e-4`` 的误差。网格加倍时最大误差约降到四分之一（``5.75e-3 → 1.33e-3 → 3.32e-4``），这是二阶收敛的经验表现，来自 ``psi`` 在单元内的二次变化。

``R = 2.2 m`` 的查询落在闭网格之外，入口直接拒绝，不做夹取或外推。这一点和下一节的笛卡尔映射不同：采样器选择“拒绝”，映射选择“夹取并报告”。

**这一节不能推出**：二阶收敛只是这个二次场在这个网格序列上的观察，不是任意场的误差上界；节点值精确不等于节点之间已知；``Z`` 网格故意取 34 个点，避开了 ``(R0, 0)``，因为那里 ``|B| = 0``，下游的逆场积分会拒绝非正场强。

从等值线到闭合场线：选择、闭合与弧长
------------------------------------

有了 ``psi`` 网格，下一步是取一条等值线。实际工作流里，``contourset`` 通常由等值线提取器给出；这里用解析圆直接构造一个只含 ``levels`` 和 ``allsegs`` 的最小对象，把注意力放在 SciRel 的选择、定向和弧长计算上。

.. code-block:: python

   from types import SimpleNamespace
   from scirel.geometry import get_fieldlines, FieldLine, get_fieldline_distance

   psi_s = B0*rs**2/(2*R0)
   theta = np.linspace(0.0, 2*np.pi, 64, endpoint=False)
   circle = np.column_stack([R0 + rs*np.cos(theta), rs*np.sin(theta)])
   circle = np.vstack([circle, circle[:1]])

   contours = SimpleNamespace(levels=[psi_s], allsegs=[[circle]])
   selected = get_fieldlines(contours, psi_s, clockwise=False)
   line = FieldLine(psi_s, selected)

   print("psi_s =", psi_s)
   print("vertices =", selected.shape[0],
         " closed =", bool(np.all(selected[0] == selected[-1])))
   print("polyline length =", get_fieldline_distance(selected)[-1])
   print("spline length   =", line.get_length())
   print("exact 2*pi*rs   =", 2*np.pi*rs)
   print("spline error    =", line.get_length() - 2*np.pi*rs)

   q = (line.verts[:, 0] - R0)/rs
   dq = line.d_ds(q)
   print("dq/ds range =", dq.min(), dq.max(), " 1/rs =", 1/rs)

实际输出：

.. code-block:: text

   psi_s = 0.10666666666666669
   vertices = 65  closed = True
   polyline length = 2.512264925563802
   spline length   = 2.513269177501545
   exact 2*pi*rs   = 2.5132741228718345
   spline error    = -4.945370289277662e-06
   dq/ds range = -2.4999845232953835 2.4999845232953284  1/rs = 2.5

``get_fieldlines`` 要求请求的等值线级别在 ``contours.levels`` 中精确出现，然后取顶点数最多的那一段，并按 ``clockwise`` 定向。我们构造的是逆时针圆，所以传入 ``clockwise=False``；若用默认的 ``clockwise=True``，定向实现会反转路径，反转后的末点不再等于首点，``closed`` 就会变成假。

闭合本身也有陷阱。用 ``np.linspace(0, 2*pi, 64)`` 时，最后一点的 ``Z`` 是 ``-9.8e-17`` 而不是 ``0``，首末坐标不是逐位相等，``is_closed()`` 会判为假，后续性能参数化也不再按周期处理。这里先用 ``endpoint=False`` 生成 64 个不同点，再显式把首点复制到末尾，才得到真正的闭合折线。

折线长度 ``2.5122649 m`` 略小于解析周长 ``2.5132741 m``，这是用 64 条弦代替圆弧的离散误差；样条重参数化后的长度 ``2.5132692 m`` 更接近解析值，残差约 ``-4.95e-6 m``。``q = (R-R0)/r_s`` 在圆上是 ``cos(theta)``，对极角求导的范围是 ``[-1, 1]``；对弧长求导则要再除以 ``r_s``，输出范围约 ``[-2.5, 2.5]``。两者差一个几何因子，不能把 ``dq/dtheta`` 当成 ``dq/ds``。

**这一节不能推出**：等值线提取不在 SciRel 里完成；``closed=True`` 只说明首末坐标相等，不证明这条线在物理上是完整磁通面；样条长度误差小只针对这条光滑圆，换成尖角或开放曲线要重新检查。

沿磁通面的逆场测度与加权平均
----------------------------

现在沿这条闭合路径做两个路径归约：``integral(dl/B)``，以及标量 ``Q = 1/R`` 的 ``B`` 加权平均。被积函数来自网格上的 ``|B|``，路径点由上一节给出。

.. code-block:: python

   from scirel.geometry import compute_flux_surface_inverse_field_average

   r_axis = np.linspace(0.9, 2.1, 49)
   z_axis = np.linspace(-0.8, 0.9, 34)
   R, Z = np.meshgrid(r_axis, z_axis)
   B = B0/(R*R0)*np.hypot(R-R0, Z)
   Q = 1.0/R

   for n in (17, 33, 65, 129, 257):
       th = np.linspace(0.0, 2*np.pi, n, endpoint=False)
       path = np.column_stack([R0 + rs*np.cos(th), rs*np.sin(th)])
       path = np.vstack([path, path[:1]])
       res = compute_flux_surface_inverse_field_average(R, Z, B, path, Q)
       print(f"n={n:3d}  dl/B={res['dl_B']:.9f}  <1/R>={res['flux_surface_average']:.9f}")

   print("exact dl/B =", 2*np.pi*R0**2/B0)
   print("exact <1/R> =", 1/R0)

实际输出：

.. code-block:: text

   n= 17  dl/B=7.028420845  <1/R>=0.666666690
   n= 33  dl/B=7.057912219  <1/R>=0.666666663
   n= 65  dl/B=7.065832624  <1/R>=0.666666664
   n=129  dl/B=7.067885629  <1/R>=0.666666664
   n=257  dl/B=7.068408285  <1/R>=0.666666664
   exact dl/B = 7.0685834705770345
   exact <1/R> = 0.6666666666666666

解析值可以直接算出来。路径上 ``dl = r_s dtheta``，``B = B0 r_s/(R R0)``，所以

.. code-block:: text

   integral(dl/B) = integral((R*R0)/(B0*r_s) * r_s dtheta)
                  = (R0/B0) * integral(R dtheta) = 2*pi*R0^2/B0

对 ``Q = 1/R``，分子是 ``integral((R0/(B0*r_s)) * r_s dtheta) = 2*pi*R0/B0``，除以 ``integral(dl/B)`` 正好得到 ``1/R0``。表中的 ``dl/B`` 随路径点加密单调逼近 ``7.068583471``，误差从 ``4.02e-2`` 降到 ``1.75e-4``；``<1/R>`` 在很粗的路径上就已经很接近 ``2/3``，因为 ``Q`` 的权重和 ``B`` 的 ``1/R`` 依赖在这个特殊几何里大幅抵消。

这不是巧合，也不能推广：它依赖 ``B ∝ 1/R`` 和圆形路径。函数内部用 ``RectBivariateSpline`` 在路径点上插值 ``B`` 和 ``Q``，再用梯形法对折线弧长积分；所以误差同时来自 ``B`` 的样条插值和路径的折线近似。

**这一节不能推出**：``dl/B`` 小只说明离散积分收敛，不证明这条路径是完整磁通面，也不提供磁通面体积归一化；``B`` 必须在网格和插值后的路径点上都严格为正，磁轴附近的零点会被拒绝；路径必须整体落在网格内，且相邻点不能重合。

把轴对称平衡映射到笛卡尔求解网格
--------------------------------

最后一步是把同一套 ``(R, Z)`` 场搬到三维求解器的 ``(x, y, z)`` 网格上。``map_axisymmetric_equilibrium_to_cartesian_grid`` 要求平衡场按 ``[R, Z]`` 存放，输入轴是严格递增的一维数组。

.. code-block:: python

   from scirel.geometry import map_axisymmetric_equilibrium_to_cartesian_grid

   equilibrium = {
       'r_m': r_axis, 'z_m': z_axis,
       'psi_wb_per_rad': psi_analytic(R, Z).T,
       'br_t': (-B0*Z/(R*R0)).T,
       'bz_t': (B0*(R-R0)/(R*R0)).T,
   }
   x = np.linspace(-2.0, 2.0, 21)
   y = x.copy()
   z = np.linspace(-0.8, 0.9, 9)
   mapped = map_axisymmetric_equilibrium_to_cartesian_grid(equilibrium, x, y, z)

   covered = mapped['covered_mask']
   print("grid points =", covered.size, "covered =", covered.sum(),
         "fraction =", round(covered.mean(), 4))
   print("radially clamped =", mapped['radially_clamped_point_count'])
   print("axially clamped =", mapped['axially_clamped_point_count'])

   xx, yy = np.meshgrid(x, y, indexing='ij')
   print("planar points with R <", r_axis[0], "=",
         np.count_nonzero(np.hypot(xx, yy) < r_axis[0]))

   Bvec = mapped['magnetic_flux_density_t']
   i = np.argmin(np.abs(x - 1.4)); j = np.argmin(np.abs(y)); k = np.argmin(np.abs(z - 0.05))
   print("B(1.4,0,0.05) =", np.round(Bvec[i, j, k], 6),
         "|B| =", round(float(np.linalg.norm(Bvec[i, j, k])), 6))
   i0 = j0 = np.argmin(np.abs(x))
   print("B(0,0,0.05) =", np.round(Bvec[i0, j0, k], 6))

实际输出：

.. code-block:: text

   grid points = 3969 covered = 2520 fraction = 0.6349
   radially clamped = 828
   axially clamped = 0
   planar points with R < 0.9 = 69
   B(1.4,0,0.05) = [-0.047619 -0.       -0.095238] |B| = 0.106479
   B(0,0,0.05) = [ 0.        0.       -0.888889]

``3969`` 个笛卡尔点里有 ``2520`` 个落在原始 ``R-Z`` 映射盒内，占 ``63.49%``。``828`` 个点因为 ``R > 2.1 m`` 被径向夹到外边界；另有 ``69`` 个平面位置（乘上 9 个轴向层，共 ``621`` 个网格点）的 ``R < 0.9 m``，被夹到内边界，但它们**没有**计入 ``radially_clamped_point_count``——这个计数只统计超过上界的一侧。判断哪些点是真实覆盖的，应该直接看 ``covered_mask``，不要用两个计数器相加。

在 ``(1.4, 0, 0.05)`` 处，解析式给出 ``B_R = -2*0.05/(1.4*1.5) = -0.047619``、``B_Z = 2*(1.4-1.5)/(1.4*1.5) = -0.095238``，与输出一致，``|B| = 0.106479``。在 ``(0, 0, 0.05)`` 处，``R = 0``，径向方向没有定义，所以两个径向分量置零；但这里的 ``B_Z = -0.888889`` 来自被夹到 ``R = 0.9 m`` 的边界值，不是物理上磁轴处的场。

**这一节不能推出**：``covered_mask`` 为真只表示该点落在映射盒内，不表示场在那里已被验证；夹取把盒外点变成边界值，不能用它外推真实场；映射只做几何搬运，不包含材料分类、PML/PEC 边界或平衡求解。平衡场数组若沿用采样器的 ``[Z, R]`` 布局，会在形状检查处以 ``must have shape (49, 34)`` 失败，必须先转置。

什么时候该用哪一层
------------------

- 二维实值场在闭矩形域内取点：:doc:`../reference/generated/scirel.geometry.bilinear-grid-sampling`。
- 一维磁通剖面排序、去重和线性插值：:doc:`../reference/generated/scirel.geometry.flux-surface-profile`。
- 沿已有 ``R-Z`` 折线做 ``dl/B`` 与加权平均：:doc:`../reference/generated/scirel.geometry.flux-surface-inverse-field-average`。
- 从等值线级别选择一段并定向、截断：:doc:`../reference/generated/scirel.sampling.select-fieldline` 和 :doc:`../reference/generated/scirel.sampling.parse-segment`。
- 累计折线弧长：:doc:`../reference/generated/scirel.sampling.path-distance`。
- 用样条重参数化场线并计算弧长导数：:doc:`../reference/generated/scirel.fieldline.fieldline` 和 :doc:`../reference/generated/scirel.fieldline.arclength-derivative`。
- 把轴对称平衡映射到 ``(x, y, z)`` 求解网格：:doc:`../reference/generated/scirel.geometry.axisymmetric-equilibrium-grid-mapping`。
- 需要三维复值场插值掩码、最近点/散点采样、材料支撑分类或多项式/样条基：见本章末尾的覆盖边界。

易错点与边界
------------

- **三套布局不要混。** 二维采样网格 ``quantity[Z, R]``、采样点 ``[R, Z]``、平衡映射场 ``[R, Z]`` 是三套不同的约定；转置漏掉一次就会得到形状错误或悄悄交换的物理量。
- **闭合要逐位相等。** 用三角函数生成圆周时，``theta = 2*pi`` 的 ``sin`` 不是精确零；``FieldLine.is_closed()`` 检查的是首末坐标完全相等，不是几何上的接近。
- **定向会改变闭合。** 默认 ``clockwise=True`` 可能反转你构造的路径；对闭合轮廓，先确认构造方向，或显式传入与构造一致的 ``clockwise``。
- **磁轴是这套制造场的奇点。** ``|B|`` 在 ``(R0, 0)`` 为零，逆场积分要求严格正场强；真实装置有环向场，不能把这个零点当成普遍物理结论。
- **夹取不是外推。** 映射入口把盒外查询夹到边界并计数，采样器则直接拒绝域外点；两种策略不能互换，也不能把夹取结果当成域外场。
- **计数器不等于覆盖。** ``radially_clamped_point_count`` 只统计外边界一侧；内半径以下被夹取的点要看 ``covered_mask``。
- **样条有支持域。** ``RectBivariateSpline`` 要求每个轴至少四个点；``FieldLine.interpolate_onto`` 在支持域外返回无效值，逆场平均入口则直接拒绝越界路径。

本章没有覆盖的三维复值插值、最近点/散点/矩形样条采样、材料支撑分类、弦几何、坐标旋转、参数样条与稠密伪逆，属于同一领域的其他路径。它们各自的单位和失败模式见对应的 API 参考页；不要把本章的二维双线性、圆形磁通面和正磁场假设直接套过去。

.. seealso::

   想继续看“观测点上的预测如何进入反演”，可以读 :doc:`diagnostics-and-inference`；想回到领域导读，可以读 :doc:`/user-guide/index`。
