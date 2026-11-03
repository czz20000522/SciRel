# 接受边界

运行前必须确认当前包内 SciRel wheel 已安装，并能导入
scirel.equilibrium.solve_finite_frc_feedback。缺包时返回
status=HOLD_PUBLIC_RUNTIME_MISSING、termination_reason=public_runtime_missing，
保留导入异常和环境信息。

有包时必须实际执行有限协议并保留所有状态、计数器、边界数组、三层收敛布尔值、
status 和 termination_reason。当所有数值有限、三个有限协议条件都满足且
converged=true 时才使用 RESULT_AVAILABLE_FINITE_PROTOCOL；
当结果仍然有限但达到协议上限时使用
HOLD_NONCONVERGED_FINITE_STATE + maxiter_reached。Iw/Be1 为零、出现非有限或
复数时使用 HOLD_NONFINITE_OR_UNDEFINED，输入错误使用 HOLD_INVALID_INPUT。
这些状态都不能包装成“完成科学平衡”。

科学残差、连续极限、网格收敛、物理适用性和人工接受仍独立 pending。
