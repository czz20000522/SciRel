# 三线圈格林边界与双反馈的二维场反转平衡

这是一个有限 17×33 网格、有限线圈采样和三层停止协议的 FRC 反馈题。题目需要公开
SciRel wheel 中的 scirel.equilibrium.solve_finite_frc_feedback；若运行环境没有该
公开包，必须报告 HOLD_PUBLIC_RUNTIME_MISSING，不能把“程序结构存在”说成完整科学结果。

输出必须带机器可判定的 status 和 termination_reason：
RESULT_AVAILABLE_FINITE_PROTOCOL 表示所有有限协议条件满足；
HOLD_NONCONVERGED_FINITE_STATE + maxiter_reached 表示保留了有限的最后状态但达到
协议上限；HOLD_NONFINITE_OR_UNDEFINED、HOLD_INVALID_INPUT 和
HOLD_PUBLIC_RUNTIME_MISSING 分别表示数值、输入或公开运行时失败。返回
converged=false/maxiter_reached 是合法的有界计算状态，但不是科学上完整收敛的
FRC 平衡。HTML/CSV 和展示图表仍属于 agent glue。完整模型、输入和输出字段见
model.md、inputs.json、output-spec.json。
