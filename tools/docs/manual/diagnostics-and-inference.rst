诊断建模与参数优化：从观测残差到有界局部优化
============================================

这一章回答一个具体问题：**已经有一个轴对称平衡模型，并且在几个位置上测到了磁通和压强，怎样把模型预测变成统一尺寸的残差，并把这一层接到有界局部优化上？**

读完之后，你应该能独立完成下面这条链：先在指定 ``R-Z`` 点上采样预测，再用观测标准差把失配归一化，然后用真实的 Picard 前向做一次带罚值的试探，最后用拉丁超立方布点给有界优化器准备初值，并读懂“优化器收敛”与“拟合可信”之间的差别。

.. note::

   本章是教程，不是合同摘要。每个入口的完整参数、失败行为和适用范围在章末链接的 API 参考页。教程代码按顺序累加；单独复制某一节时，请保留前面的模型定义。

准备：一个两参数的制造平衡
--------------------------

考虑一个轴对称、纯极向的制造模型。计算域是 ``R in [0.2, 0.6] m``、``Z in [-0.2, 0.2] m`` 的 ``7 x 7`` 网格。真空场取

.. code-block:: text

   psi_vac(R) = B0 * R^2 / 2,   B0 = 1 T

压强剖面由径向压强梯度 ``a`` 和各向异性比 ``r`` 给出：

.. code-block:: text

   p_perp(R)     = 5 Pa + a * R^2 / 2
   p_parallel(R) = r * p_perp(R)

压强通过一条给定的 rank-one Green 响应反馈到极向磁通。取常数 ``g = 0.6``、``C = 0.064``，平衡场幅值满足

.. code-block:: text

   B = (B0 + sqrt(B0^2 + 4 * g * a * C)) / 2
   psi(R,Z) = B * R^2 / 2

``psi`` 的单位是 ``Wb/rad``，约定为 ``psi = R A_phi``；单匝完整磁通是 ``2*pi*psi``，单位 ``Wb``。这是一个**制造模型**：常数、响应和观测位置都是为了把推断链讲清楚而选定的，不对应任何真实装置。

三个观测约定贯穿全章：

- 场数组按 ``[Z, R]`` 索引，观测点按 ``[R, Z]`` 排列；
- 磁通请求必须显式选择 ``raw_psi`` 或 ``magnetic_flux``，并给出单位；
- 压强通道必须显式给出单位，``Pa`` 是当前实现接受的单位。

从平衡状态到观测点上的预测
--------------------------

先只做“正向”这一步：给定参数，算出观测点上的预测值。``synthesize_equilibrium_diagnostics`` 用双线性采样器在网格上取点，只返回你明确请求的通道。

.. code-block:: python

   import numpy as np
   from scirel.diagnostics import synthesize_equilibrium_diagnostics

   B0, a_true, ratio_true = 1.0, 1.7, 1.6
   R, Z = np.meshgrid(np.linspace(0.2, 0.6, 7), np.linspace(-0.2, 0.2, 7))
   points = np.array([[R[2, 2], Z[2, 2]], [R[-2, -2], Z[-2, -2]]])

   def analytic_state(gradient, ratio):
       gain, C = 0.6, 0.064
       B = (B0 + np.sqrt(B0**2 + 4*gain*gradient*C)) / 2
       p_perp = 5.0 + gradient * R**2 / 2
       return {'psi': B*R**2/2, 'psi_unit': 'Wb/rad',
               'profiles': {'p_parallel': ratio*p_perp, 'p_perp': p_perp},
               'profile_units': {'p_parallel': 'Pa', 'p_perp': 'Pa'}}

   def predict(state, request):
       return synthesize_equilibrium_diagnostics(
           R=R, Z=Z, equilibrium=state, observations=request)

   request = {'flux_loops': {'points': points, 'quantity': 'magnetic_flux', 'unit': 'Wb'},
              'thomson': {'points': points,
                          'p_parallel': {'unit': 'Pa'}, 'p_perp': {'unit': 'Pa'}}}
   linked = predict(analytic_state(a_true, ratio_true), request)
   raw = predict(analytic_state(a_true, ratio_true),
                 {'flux_loops': {'points': points,
                                 'quantity': 'raw_psi', 'unit': 'Wb/rad'}})

   print("flux_loops (Wb) =", np.round(linked['flux_loops'], 9))
   print("raw psi (Wb/rad) =", np.round(raw['flux_loops'], 9))
   print("p_parallel (Pa) =", np.round(linked['thomson']['p_parallel'], 9))
   print("p_perp (Pa)     =", np.round(linked['thomson']['p_perp'], 9))
   print("units =", linked['units'])
   print("p_parallel/p_perp =",
         linked['thomson']['p_parallel'] / linked['thomson']['p_perp'])

实际输出：

.. code-block:: text

   flux_loops (Wb) = [0.3705327  0.94856371]
   raw psi (Wb/rad) = [0.05897211 0.1509686 ]
   p_parallel (Pa) = [8.15111111 8.38684444]
   p_perp (Pa)     = [5.09444444 5.24177778]
   units = {'flux_loops': 'Wb', 'thomson': {'p_parallel': 'Pa', 'p_perp': 'Pa'}}
   p_parallel/p_perp = [1.6 1.6]

第一个观测点 ``R = 0.3333 m`` 上的 ``raw_psi`` 是 ``0.05897211 Wb/rad``，完整磁通是 ``0.37053270 Wb``，正好相差 ``2*pi``。第二个点半径更大，两个量都更大。两个点的压强比都严格等于输入的 ``1.6``，因为剖面是按同一比例构造的。

``flux_loops`` 这个名字也容易误解：当前入口只在这些 ``(R, Z)`` 点上采样磁通，不沿线做回路积分，也不会自动乘入线圈匝数或参考环差分。``thomson`` 则是历史命名空间，这里只表示“在点上采样给定的剖面”，不是 Thomson 散射仪器模型。两个观测点正好落在网格节点上，所以这一节的采样没有插值误差；把点移到单元内部，就会引入双线性误差。

**这一节不能推出**：预测里有单位标签，不等于输入数据已经被正确标定；``Wb/rad`` 只在调用者明确声明该规范时才被乘 ``2*pi``；也没有任何线圈匝数、参考环差分或仪器响应被自动加入。

把失配变成固定顺序的残差
------------------------

有了预测，还需要把不同量纲的失配合成一个优化器能用的向量。``reduce_observation_residuals`` 先冻结观测布局，再按固定顺序计算 ``(prediction - value) / sigma``。

.. code-block:: python

   from scirel.diagnostics import reduce_observation_residuals

   observations = {
       'flux_loops': {'points': points, 'values': linked['flux_loops'], 'sigma': 1e-3,
                      'unit': 'Wb', 'quantity': 'magnetic_flux'},
       'thomson': {'points': points,
                   'p_parallel': {'values': linked['thomson']['p_parallel'],
                                  'sigma': 0.02, 'unit': 'Pa'},
                   'p_perp': {'values': linked['thomson']['p_perp'],
                              'sigma': 0.02, 'unit': 'Pa'}},
   }
   trial = predict(analytic_state(1.0, 1.2), request)
   reduced = reduce_observation_residuals(predicted=trial, observations=observations)

   print("residual_vector =", np.array2string(reduced['residual_vector'], precision=6))
   print("chi2 =", round(reduced['chi2'], 1))
   print("residual count =", reduced['residual_vector'].size)

实际输出：

.. code-block:: text

   residual_vector = [  -8.541339  -21.865827 -104.222222 -110.808889   -1.944444   -4.977778]
   chi2 = 23720.5
   residual count = 6

向量的顺序是固定的：先两个 ``flux_loops``，再两个 ``p_parallel``，最后两个 ``p_perp``；每个通道内部保持输入的 C 顺序。负号表示预测小于观测。``sigma`` 在这里是调用者声明的权重：磁通 ``1e-3 Wb``、压强 ``0.02 Pa``，所以同样的绝对失配在压强通道里被放大得更多。``chi2`` 就是这个六维向量的平方和。

这个初始点 ``(a, r) = (1.0, 1.2)`` 离真值 ``(1.7, 1.6)`` 很远，各向异性比错得最多，所以 ``p_parallel`` 的两个残差最大；磁通残差只有约 ``-8.5`` 和 ``-21.9`` 个 ``sigma``。这说明不同通道对参数的敏感度不同，但**不能**据此判断哪个参数“更错”。

**这一节不能推出**：``chi2`` 不是 p 值，也不是拟合优度检验；这里没有协方差、没有自由度校正、没有仪器系统误差。``sigma`` 是声明值，不是从重复测量估计出来的。残差大只说明在这个权重和这组参数下失配大，不说明模型物理上被否定。

一次真实前向试探：收敛、固定点残差与失败罚值
--------------------------------------------

上一节的预测来自解析式。真正做反演时，前向通常是数值求解器。这里用轴对称各向异性 Picard 求解器：给定参数，它迭代求解力平衡，返回 ``psi``、压强、收敛标志和固定点残差。

.. code-block:: python

   from scirel.equilibrium import solve_axisymmetric_anisotropic_picard
   from scirel.inference import evaluate_anisotropic_trial

   def picard(payload, maxiter=150):
       gradient, ratio = payload['params']['gradient'], payload['params']['ratio']
       p_perp = 5.0 + gradient * R**2 / 2
       state = solve_axisymmetric_anisotropic_picard(
           r_grid=R, z_grid=Z, psi_vac=B0*R**2/2,
           g_psi=0.6*(R**2/2).ravel()[:, None]*np.ones((1, R.size)),
           tol=1e-12, maxiter=maxiter, relax=0.2,
           pressure_closure=lambda _b, _psi: {
               'p_parallel': ratio*p_perp, 'p_perpendicular': p_perp})
       return {**state, 'psi_unit': 'Wb/rad',
               'profiles': {'p_parallel': state['p_parallel'],
                            'p_perp': state['p_perpendicular']},
               'profile_units': {'p_parallel': 'Pa', 'p_perp': 'Pa'}}

   good = evaluate_anisotropic_trial(
       params={'gradient': 1.7, 'ratio': 1.6}, observations=observations,
       solver_config={'r_grid': R, 'z_grid': Z},
       equilibrium_solver=picard,
       diagnostic_evaluator=lambda payload: synthesize_equilibrium_diagnostics(payload["equilibrium"], payload["R"], payload["Z"], payload["observations"]),
       residual_reducer=reduce_observation_residuals)

   print("valid =", good['valid'], " status =", good['status'])
   print("chi2 =", f"{good['chi2']:.3e}")
   print("iterations =", good['equilibrium']['iterations'])
   print("fixed_point_residual =", f"{good['equilibrium']['fixed_point_residual']:.3e}")
   print("max |psi_picard - psi_analytic| =",
         f"{np.max(np.abs(good['equilibrium']['psi']
                          - analytic_state(1.7, 1.6)['psi'])):.3e}")

实际输出：

.. code-block:: text

   valid = True  status = valid
   chi2 = 1.314e-21
   iterations = 15
   fixed_point_residual = 3.759e-14
   max |psi_picard - psi_analytic| = 6.800e-15

把参数固定在真值，Picard 迭代 15 次收敛，数值 ``psi`` 与解析制造解的最大差只有 ``6.8e-15``，固定点残差 ``3.8e-14``。这两个数说明“数值前向确实复现了这个制造状态”，也是后面能恢复参数的前提；它们本身不是对任何实验装置的验证。

再看一个故意只给一次迭代的试探：

.. code-block:: python

   bad = evaluate_anisotropic_trial(
       params={'gradient': 1.0, 'ratio': 1.2}, observations=observations,
       solver_config={'r_grid': R, 'z_grid': Z},
       equilibrium_solver=lambda payload: picard(payload, maxiter=1),
       diagnostic_evaluator=lambda payload: synthesize_equilibrium_diagnostics(payload["equilibrium"], payload["R"], payload["Z"], payload["observations"]),
       residual_reducer=reduce_observation_residuals)

   print("valid =", bad['valid'], " status =", bad['status'])
   print("failure_reason =", bad['failure_reason'])
   print("penalty residuals =", bad['residuals'])
   print("chi2 =", bad['chi2'])

实际输出：

.. code-block:: text

   valid = False  status = forward_nonconvergence
   failure_reason = equilibrium solver did not converge
   penalty residuals = [1.e+12 1.e+12 1.e+12 1.e+12 1.e+12 1.e+12]
   chi2 = 6e+24

前向没有收敛时，诊断和残差归约都不会被调用；入口直接返回与观测数相同的六维正罚值，并保留 ``valid=False`` 和明确的状态。``1e12`` 和 ``6e24`` 是给优化器的数值控制量，不是物理观测，也不是“这个参数不可行”的证明——它只说明这次前向没有给出可用状态。

**这一节不能推出**：单次试探的 ``valid`` 只表示这条前向链路走通；固定点残差小不代表残差 ``chi2`` 小，更不代表参数可辨识或最优。

用分层初值设计起点
------------------------

优化器需要一个起点。``sample_latin_hypercube`` 在每个参数的每个分层里各取一个点，再用随机排列组合，避免初值都挤在盒子中央。``n_samples`` 必须是正整数；布尔值会按非法参数抛 ``ValueError``，而不是泄漏 NumPy 的 ``TypeError``。

.. code-block:: python

   from scirel.inference import sample_latin_hypercube

   design = sample_latin_hypercube(
       bounds={'gradient': (0.2, 3.0), 'ratio': (1.1, 2.5)},
       n_samples=8, seed=3)
   for row in design['initial_samples'][:3]:
       print(f"design gradient={row['gradient']:.6f} ratio={row['ratio']:.6f}")
   print("strata(gradient) =",
         sorted(int((row['gradient'] - 0.2)/2.8*8)
                for row in design['initial_samples']))

实际输出：

.. code-block:: text

   design gradient=2.451594 ratio=1.921838
   design gradient=2.817668 ratio=2.026226
   design gradient=0.955909 ratio=1.625261
   strata(gradient) = [0, 1, 2, 3, 4, 5, 6, 7]

固定随机种子后，每个坐标的八个样本恰好落在八个分层里各一个；两个坐标的排列互相独立。它是初值设计，不是后验分布，也不代表这些点“覆盖了物理上合理的参数”。

.. note::

   端到端反演（把前向端口、诊断端口和固定维数残差直接接起来的 direct anisotropic inversion）不在当前安装包内：
   ``src/scirel/inference/`` 里没有这个实现，``scirel.inference`` 也不导出它。
   本章只讲到有界局部优化这一层，不提供“观测 → 试探 → 自动拟合”的完整路径。
   需要这一层时，先按上面的端口各自用起，再自己接。

什么时候该用哪一层
------------------

- 只想从给定平衡状态在指定点得到预测：:doc:`../reference/generated/scirel.diagnostics.equilibrium-synthesis-diagnostics`。
- 已有预测和观测，只想得到固定顺序残差与平方和：:doc:`../reference/generated/scirel.diagnostics.observation-residuals`。
- 有自己的前向、诊断和残差端口，只做一次带罚值的试探：:doc:`../reference/generated/scirel.inference.anisotropic-trial-evaluation`。
- 只需要分层初值设计：:doc:`../reference/generated/scirel.inference.latin-hypercube-sampling`。
- 已有 ``trial_evaluator``，只做有界局部优化：:doc:`../reference/generated/scirel.inference.anisotropic-parameter-optimization`。

易错点与边界
------------

- **顺序是合同的一部分。** 残差先磁通、再 ``p_parallel``、再 ``p_perp``，通道内部按 C 顺序展平；交换顺序不会报错，但会让不同调用之间的 ``chi2`` 不可比。
- **单位标签不是单位换算。** 观测和预测的 ``unit`` 必须一致；``magnetic_flux`` 只在源 ``psi`` 声明为 ``Wb/rad`` 时乘 ``2*pi``，声明为 ``Wb`` 时原样返回。
- **``sigma`` 是声明的权重。** 它不来自重复测量，也不含系统误差；``chi2`` 只是该对角权重下的代数平方和。
- **罚值不是物理。** ``1e12`` 只让无效试探在优化中排序靠后，不构成可行性、可辨识性或物理正确性的证据。
- **三种“收敛”要分开读。** ``optimizer_converged`` 是数值停止，``forward_converged`` 是前向固定点，``converged`` 是组合状态；它们都不等于残差达到实验阈值。
- **边界会改变答案。** 真值在盒外时，最优点会贴边并扭曲其它参数；先检查 ``best_parameters`` 是否落在边界上，再解释数值。

本章的数值只对应这个制造的两参数模型。换 Green 响应、换观测噪声、换参数化或换装置，都不能把这里的 ``gradient``、``ratio`` 和 ``chi2`` 直接套用。完整参数校验、异常类型和更大参数域的验证边界见上面的 API 参考页；那里是由合同生成的参考层，本章只负责把从诊断合成到有界优化的每一层端口讲清楚。

.. seealso::

   想继续看“观测点如何从网格采样”，可以读 :doc:`numerical-geometry`；想回到领域导读，可以读 :doc:`/user-guide/index`。
