# 完成与失败规则

本题数值比较预算已冻结。结果状态必须为 COMPLETED_BOUNDED_PARTIAL、HOLD_INVALID_INPUT 或 HOLD_NONFINITE_OUTPUT。

逐元素比较采用：
abs(actual-reference) <= atol + rtol*abs(reference)，rtol=1e-7。
绝对预算为：

- BR/BZ/Bmag: 1e-10 T
- psi: 1e-11 Wb
- Phi: 1e-10 Wb
- U/Tmax/delta_U/delta_Tmax: 1e-9
- 反射残差沿用对应场量预算。

所有矩阵必须完整、有限、shape=[5,5]，不得删除点、零填或用全零替代。
安装偏差诊断的工程识别参考线为 delta_U >= 1e-6 或 delta_Tmax_rad >= 1e-6；该识别线不改变数值比较预算。

名义配置必须满足 BR 反射奇对称、BZ/psi 反射偶对称和中平面 BR=0；偏移配置不强制这些对称性。Phi=2*pi*psi，不能把 psi 当作完整圆盘磁通。实际 SciRel 调用、输入身份、输出读回和失败 stderr 必须记录在 agent 回执中。
