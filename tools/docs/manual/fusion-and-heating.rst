聚变反应与能量沉积：从 DD 中子能量到加热账本
======================================================================

这一章只有三个公开关系，所以写成一条可运行的小案例，而不是按函数目录铺开。它跟着三个连续的问题走：

1. 给定两个氘核的速度和一条探测视线，D(d,n)3He 反应产生的中子在实验室系有多少能量？
2. 给定一个快离子的诞生能量、电子温度和离子质量，这个局部近似把多少功率分给离子？
3. 给定四个物种已经吸收的功率账本，百分比怎么闭合？

这三个问题处在不同层次：**单次反应的运动学、给定模型的加热分配、已知功率的归一化记账**。它们可以各自运行，但不能自动拼成一个包含反应率、粒子轨迹和能量输运的完整模型。

.. note::

   本章是教程，不是合同摘要。三个函数的完整签名、参数单位、失败行为和适用范围在章末的 API 参考页；代码只使用 SciRel 的公开函数，数字都是实际运行结果。

准备：反应、能量账本与单位
----------------------------------------------------------------------

DD 反应的中子分支是

.. code-block:: text

   D + D -> n + 3He + 3.27 MeV

这里的 ``Q = 3.27 MeV`` 是反应释放的总能量。两个氘核的相对运动提供额外动能，反应后由中子和 3He 按质量分配。非相对论双体运动学写成

.. code-block:: text

   v_cm    = (v1 + v2) / 2
   v_rel   = v1 - v2
   E_avail = Q + (1/2) * (m_D/2) * |v_rel|^2
   E_cm    = m_He3 / (m_n + m_He3) * E_avail
   E_boost = (1/2) * m_n * |v_cm|^2
   E_lab   = E_cm + E_boost + 2 * sqrt(E_cm * E_boost) * cos(theta)

公式里省略了单位换算；实现内部把速度从 cm/s 换成 m/s、质量从 amu 换成 kg，并在最后把 MeV 换成 keV。其中 ``theta`` 是质心速度方向与探测视线之间的夹角。``m_He3/(m_n+m_He3)`` 约等于 0.749，所以静止反应物的中子能量约为 ``0.749 * 3.27 MeV = 2.45 MeV``。最后一项是运动学干涉项：它不是各向同性的角分布，只是同一反应在不同视线上的能量。

单位要特别小心：两个速度用 **cm/s**，探测方向是无量纲单位向量，返回能量用 **keV**。速度与探测向量必须在同一个笛卡尔系里；函数不做坐标变换。探测向量必须是单位向量，误差容限是 ``1e-12``；非单位向量会被拒绝，而不是自动归一化。

实现把 ``E_lab`` 写成两个非负项之和，避免在反向探测、两项几乎抵消时出现舍入负值。这不是给结果加了下限，也没有把零替换成别的数。

静止反应物与运动氘核对：一个能量，两个方向
----------------------------------------------------------------------

先看两个情形：完全静止的反应物，以及一对同向运动的氘核，探测方向分别取前向和后向。

.. code-block:: python

   from scirel.fusion import calculate_dd_neutron_lab_energy_kev

   E = calculate_dd_neutron_lab_energy_kev
   still = E(
       reactant1_velocity_cm_s=(0.0, 0.0, 0.0),
       reactant2_velocity_cm_s=(0.0, 0.0, 0.0),
       detector_unit_vector=(1.0, 0.0, 0.0),
   )
   v1, v2 = (1.0e8, 0.0, 0.0), (5.0e7, 0.0, 0.0)
   forward = E(reactant1_velocity_cm_s=v1, reactant2_velocity_cm_s=v2,
               detector_unit_vector=(1.0, 0.0, 0.0))
   backward = E(reactant1_velocity_cm_s=v1, reactant2_velocity_cm_s=v2,
                detector_unit_vector=(-1.0, 0.0, 0.0))
   print(f"stationary : {still:.9f} keV")
   print(f"forward    : {forward:.9f} keV")
   print(f"backward   : {backward:.9f} keV")

实际输出：

.. code-block:: text

   stationary : 2450.475899416 keV
   forward    : 2624.190695809 keV
   backward   : 2284.596359041 keV

静止时 ``E_boost = 0``，干涉项也为零，结果就是质量分配能 ``2450.475899416 keV``。这是 DD 中子常用的 2.45 MeV 锚点；它比 ``0.75 * 3.27 MeV`` 略低，因为质量比是 ``3.01603/(1.008665+3.01603)``，不是精确的 3/4。

``v1 = 1e8 cm/s``、``v2 = 5e7 cm/s`` 时，质心速度是 ``7.5e7 cm/s``，相对速度是 ``5e7 cm/s``。前向探测得到 ``2624.19 keV``，后向得到 ``2284.60 keV``，两者相差约 ``339.6 keV``。这个差来自质心运动和干涉项，不是 Q 值变了：同一个反应，换的只是探测方向。

两个方向的平均值约 ``2454.4 keV``，比静止值高约 ``3.9 keV``。这部分来自相对运动抬高的 ``E_avail`` 和质心 boost；不要把它当成一个新的 Q 值或“平均反应能”。

这一节不能推出：每次调用只给出一对速度、一个方向上的一个中子能量。它不计算反应率、产额、角分布权重或中子后续输运。它也是非相对论关系；把速度推到相对论区间，结果没有物理意义。

扫描探测方向：能量不是各向同性的
----------------------------------------------------------------------

固定一束 ``1.3e8 cm/s`` 的氘核打静止氘靶，让探测方向在 ``x-y`` 平面内从 0 转到 180 度：

.. code-block:: python

   import numpy as np
   from scirel.fusion import calculate_dd_neutron_lab_energy_kev

   for deg in (0, 30, 60, 90, 120, 150, 180):
       theta = np.deg2rad(deg)
       detector = (np.cos(theta), np.sin(theta), 0.0)
       energy = calculate_dd_neutron_lab_energy_kev(
           reactant1_velocity_cm_s=(1.3e8, 0.0, 0.0),
           reactant2_velocity_cm_s=(0.0, 0.0, 0.0),
           detector_unit_vector=detector,
       )
       print(f"{deg:3d} deg  {energy:9.3f} keV")

实际输出：

.. code-block:: text

     0 deg   2606.618 keV
    30 deg   2586.880 keV
    60 deg   2532.955 keV
    90 deg   2459.292 keV
   120 deg   2385.628 keV
   150 deg   2331.703 keV
   180 deg   2311.965 keV

能量随角度单调下降，前向与后向相差约 ``295 keV``，约为 90 度值的 12%。90 度值 ``2459.292 keV`` 正好是 0 度和 180 度的平均：``(2606.618 + 2311.965)/2 = 2459.2915``。这不是巧合，而是 ``cos(theta)`` 项在 90 度消失、在 0/180 度取 ±1 的结果。

这条曲线是**固定速度对、固定反应道的视线能量**，不是测量到的角分布。前向探测器看到更高的中子能量，不代表那个方向的中子更多；产额需要反应率和角分布，这两个量都不在本次调用里。

这一节不能推出：不能把这条曲线当成 DD 中子能谱，也不能用它推断探测器的计数。要得到谱，需要许多速度对（分布函数）和一个角分布权重；本章的三个函数都不提供这些。

从反应能量到加热：快离子分配
----------------------------------------------------------------------

知道了单次反应的中子能量，还不等于知道功率去了哪里。下一个关系回答一个更局部的问题：一个诞生能量为 ``E_birth`` 的快离子，在电子温度 ``T_e`` 的等离子体中，按规定的局部近似把多少功率分给离子？

.. code-block:: python

   from scirel.plasma import fast_ion_fractional_heating

   for birth in (0.0, 10.0, 100.0, 1000.0, 3500.0):
       fraction = fast_ion_fractional_heating(birth, 10.0, 2.0)
       print(f"E_birth = {birth:6.0f} keV  f_i = {fraction:.6f}")

   a = fast_ion_fractional_heating(100.0, 1.0, 2.0)
   b = fast_ion_fractional_heating(1000.0, 10.0, 2.0)
   print(f"same x^2: {a:.9f} vs {b:.9f}")
   print(f"alpha, 3.5 MeV, T_e=10 keV: {fast_ion_fractional_heating(3500.0, 10.0, 4.0):.6f}")

实际输出：

.. code-block:: text

   E_birth =      0 keV  f_i = 1.000000
   E_birth =     10 keV  f_i = 0.995559
   E_birth =    100 keV  f_i = 0.883525
   E_birth =   1000 keV  f_i = 0.308602
   E_birth =   3500 keV  f_i = 0.110967
   same x^2: 0.308601931 vs 0.308601931
   alpha, 3.5 MeV, T_e=10 keV: 0.199848

这个关系是

.. code-block:: text

   x^2 = E_birth / (10 * m_fast * T_e)
   f_i = (2 / x^2) * integral_0^x t / (1 + t^3) dt

``E_birth`` 和 ``T_e`` 用 keV，``m_fast`` 用 amu，``f_i`` 无量纲。它只给出离子份额；在这个两通道记账里，电子份额可以写成 ``1 - f_i``，但函数不返回电子份额，也不模拟两条通道各自的慢化历史。

几个数可以这样读：诞生能量远低于 ``10 * m_fast * T_e`` 时，``f_i`` 接近 1；能量升高，``f_i`` 下降。在 ``T_e = 10 keV``、氘质量 2 amu 时，10 keV 的 ``f_i`` 是 0.9956，100 keV 是 0.8835，1000 keV 降到 0.3086。3500 keV 的氘核给出 0.1110；同样 3.5 MeV 但质量 4 amu 的 alpha 给出 0.1998，因为 ``x^2`` 里还有质量。

``100 keV, T_e=1, m=2`` 和 ``1000 keV, T_e=10, m=2`` 都给 ``x^2=5``，所以 ``f_i`` 相同到 ``0.308601931``。这是一个检查：函数只通过 ``x^2`` 依赖这三个输入，不是分别拟合 ``E``、``T_e``、``m``。

``E_birth = 0`` 返回精确的 1.0，这是积分在 ``x -> 0`` 的连续极限，不代表真的存在零能量快离子。它是数学边界，不是实验点。

这一节不能推出：``f_i`` 是给定局部近似的分配比例，不是粒子轨迹或慢化模拟；它没有空间输运、剖面演化、碰撞算符或实验标定。它也不告诉你功率在何处沉积、沉积多快。 ``x^2`` 里的 10 是这个近似的一部分，不是普适常数。

从功率账本到百分比：吸收份额
----------------------------------------------------------------------

第三个关系处理另一层：如果四个物种的**已吸收功率**已经给定，怎样把它们闭合为百分比？

.. code-block:: python

   import numpy as np
   from scirel.diagnostics import compute_species_absorption_fraction

   ledger = [3.0, 2.0, 0.8, 0.2]   # MW，按调用者给定的四个物种顺序
   out = compute_species_absorption_fraction(ledger)
   print("total:", out["total_power"], "MW")
   print("percent:", np.round(out["species_fraction_percent"], 6))
   print("sum:", out["total_fraction_percent"])
   print("residual:", out["fraction_sum_residual_percent"])
   print("branch:", out["branch"])

   try:
       compute_species_absorption_fraction([0.0, 0.0, 0.0, 0.0])
   except ValueError as exc:
       print("zero total ->", exc)

实际输出：

.. code-block:: text

   total: 6.0 MW
   percent: [50.       33.333333 13.333333  3.333333]
   sum: 99.99999999999999
   residual: -1.4210854715202004e-14
   branch: nonzero_total
   zero total -> zero total_power has no source-defined percentage result

四个数按调用者给的顺序解释，函数不推断物种名称，也不重排。总功率是 6.0 MW，份额分别是 50%、33.333333%、13.333333%、3.333333%。返回的份额之和是 ``99.99999999999999``，残差 ``-1.42e-14``。这个残差是双精度浮点的舍入，不是有功率丢失；函数返回的是**实际返回的百分比**之和，不是未舍入的有理数之和。

零总功率会抛 ``ValueError``：百分比份额没有定义。负的账本项是允许的，它表示一个有符号的贡献，函数按计算值报告而不截断。极端抵消会让单个份额的舍入放大，此时返回的和可能明显偏离 100；``fraction_sum_residual_percent`` 就是用来暴露这种情况的。

这一节不能推出：这个函数不计算吸收物理。它不知道四个物种分别是谁，也不验证这些功率是否物理。它只做账本闭合；吸收功率必须由你或上游模型提供。

三个层次不能自动拼成什么
----------------------------------------------------------------------

把这三个关系放在一起，很容易产生一种错觉：是不是可以从 DD 中子能量一路算到加热和吸收？目前不能。它们回答的是不同层次的问题：

.. list-table::
   :header-rows: 1

   * - 关系
     - 输入
     - 输出
     - 不提供
   * - DD 中子实验室系能量
     - 两个氘核速度、探测方向
     - 一个中子能量（keV）
     - 反应率、角分布、后续输运
   * - 快离子加热分配
     - 诞生能量、电子温度、快离子质量
     - 离子分配比例（无量纲）
     - 轨迹、剖面、实验标定
   * - 物种吸收份额
     - 四个已吸收功率
     - 百分比与闭合残差
     - 吸收物理、物种识别

一个完整的能量沉积链至少还需要反应率 ``<sigma v>``、分布函数、角分布、慢化/沉积剖面和输运模型。本章的三个函数各自只负责其中一小段；把它们相乘或串联之前，必须先明确缺的是哪一段。

常见误用与边界
----------------------------------------------------------------------

- **速度单位**：DD 入口用 cm/s，不是 m/s。传错单位不会报错，但能量会差 ``10^4`` 量级。
- **探测向量**：必须是单位向量，容限 ``1e-12``；非单位向量会被拒绝，不会自动归一化。速度与探测向量必须在同一笛卡尔系。
- **反应道**：``Q = 3.27 MeV`` 只对应 D(d,n)3He。不要把它套到 D(d,p)T 或 D-T 上（后者的 ``Q`` 约为 17.6 MeV）。
- **相对论**：关系是非相对论的，没有速度截断；但速度很大时，非相对论近似本身不再适用。
- **角权重**：函数只返回能量，不返回角分布权重。前向能量更高不等于前向产额更大。
- **加热输入**：``E_birth`` 可为 0；``T_e`` 和 ``m_fast`` 必须严格为正。``E_birth = 0`` 的 ``f_i = 1`` 是数学极限，不是物理粒子。
- **加热含义**：``f_i`` 是局部近似下的离子分配比例，不是“离子温度”或“沉积功率”。要得到功率，需要乘上你拥有的快离子功率，而那是另一个模型输入。
- **账本**：必须恰好四项；总功率为零会失败；负项是有符号贡献，不是错误。极端抵消时，检查 ``fraction_sum_residual_percent``，不要假设和一定接近 100。
- **残差不是误差**：百分比闭合残差是舍入量，不是吸收模型的误差估计。

三个函数的 API 参考与完整失败行为：

- :doc:`../reference/generated/scirel.fusion.dd-neutron-lab-energy`
- :doc:`../reference/generated/scirel.plasma.fast-ion-heating`
- :doc:`../reference/generated/scirel.diagnostics.species-absorption-fraction`

.. seealso::

   如果你关心的是反应率、碰撞截面或分布函数，应回到 :doc:`/user-guide/index` 选择原子碰撞或动理学领域；本章的三个关系不替代那些模型，也不能单独组成能量输运闭环。
