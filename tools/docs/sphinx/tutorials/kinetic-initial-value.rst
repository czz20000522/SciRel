静电根与线性初值演化
================================

这里求解两个相关而不同的问题：先在给定平衡分布下追踪静电色散关系的一条根分支，再从给定扰动出发推进一个线性 Vlasov–Poisson 初值问题。频域根与时域初值响应不能直接混同；初值响应一般包含多种模态及连续谱效应。

本例使用 ``scirel-0.2.0.dev9+scientific.core``，Linux ARM64、Python 3.14.7、NumPy 2.5.4 与 SciPy 1.18.1。以下计算不读取原来源项目、预存答案或网络，也不需要 MATLAB、Octave 或绘图。

沿波数追踪静电根
----------------------------

使用归一化频率与波数，求解 Maxwell 分布的介电函数零点。每个复方程化为实部、虚部两个方程；除了求解器状态，还检查最终介电残差。默认扫描使用 19 个波数和合同约定的初猜，结果仅属于这条寻根路线。

.. code-block:: python

   import numpy as np
   from scirel.kinetic import scan_gpdf_roots

   scan = scan_gpdf_roots("langmuir")
   max_residual = float(np.max(scan["dielectric_residual"]))
   print(len(scan["k"]), f"{max_residual:.6e}")
   assert len(scan["k"]) == 19 and max_residual < 1e-9

实际输出：

.. code-block:: text

   19 1.038328e-12

这里的残差衡量返回频率代入同一介电方程后的闭合程度，不是频率相对真根误差，也不证明所有根都已找到。改变初猜、扫描方向或模型参数可以选中其他分支；任一点不收敛会拒绝整个扫描，调用者不会得到混有失败点的“成功数组”。参数、频率与相速度约定见 :doc:`../reference/generated/scirel.kinetic.generalized-root-scans`。

从扰动状态推进电场
----------------------------

选择 Maxwell 平衡分布 ``Fn=1``，其他参数使用明确的公开默认值：波数 ``k=0.15``、速度区间 ``[-20, 20]``、2048 个速度子区间、时间步 ``dt=0.01``、2000 步。速度、时间、波数与电场均采用该合同的无量纲归一化，不能直接按 SI 值解释。

复合入口依次执行状态初始化、离散 Poisson 闭合、按顺序的 RK4 演化、场幅值包络与峰值诊断。每一步保持同一个速度网格和扰动状态，而不是把独立函数随意串联。

.. code-block:: python

   from scirel.kinetic import solve_vlasov_poisson

   solution = solve_vlasov_poisson(Fn=1)
   state = solution["state"]
   print(state["df"].size, state["dEt"].size)
   print(f"{state['dE'].real:.6f}", f"{state['dE'].imag:.6f}")
   print(f"{state['TR']:.6f}", solution["diagnostic_status"])

   np.testing.assert_allclose(
       state["dE"],
       1j * state["dv"] * np.sum(state["df"]) / state["k"],
       rtol=1e-13,
   )

实际输出：

.. code-block:: text

   2049 2001
   -0.000000 -0.303128
   2144.660585 available

2049 是包含两个端点的速度节点数；2001 个场样本包含初态和 2000 次更新。末态为 ``t=20``，复电场的实部舍入为零，虚部约为 ``-0.303128``；它的模是幅值，不能仅凭虚部符号判断增长或阻尼。输出的 ``available`` 表示本例有足够峰值供诊断，并不代表任意初态或时间窗都会有诊断结果。

上述断言独立用最终分布重算离散 Poisson 电场，检查状态消费一致性。时间积分另有矩阵指数与步长阶数验证；这里的末态数字不是普遍物理常数，也不替代速度网格、速度盒与时间步收敛研究。离散速度导致的回归时间约为 ``2144.660585``；本次时间窗早于回归，但这个事实本身不能证明连续极限精度。

继续组合与适用边界
----------------------------

需要控制中间状态时，从 :doc:`../reference/generated/scirel.kinetic.vp-init` 创建状态，使用 :doc:`../reference/generated/scirel.kinetic.vp-rk4-step` 或 :doc:`../reference/generated/scirel.kinetic.vp-evolve` 推进，再读取 :doc:`../reference/generated/scirel.kinetic.vp-diagnostic`。直接使用 :doc:`../reference/generated/scirel.kinetic.vp-landau` 可以得到相同科学步骤的单一调用入口。

此功能组适用于一维、单个空间 Fourier 模、固定离子背景的线性扰动；不包含非线性相空间演化、多空间维度或移动离子动力学。有限速度盒、矩形求积、分布拐角及截止项各有明确限制。通用分布的低半平面响应应按其解析延拓或实轴积分合同选择，不能把所有非光滑分布都当作 Gaussian 解析函数。

复现绑定
----------------------------

本例实际安装 wheel 的 SHA-256 为 ``ff2bc189e74736a704a66301ea4159c9d0e15851e5bf56e75cf9c65558c52e79``。代码、执行输出与运行条件由开发侧的 ``provenance/validation/kinetic-tutorial-20261014.json`` 绑定；文档构建只渲染这些已运行结果，不在构建时重新计算科学答案。技术接收、最终人工科学认可与再分发许可分别记录。
