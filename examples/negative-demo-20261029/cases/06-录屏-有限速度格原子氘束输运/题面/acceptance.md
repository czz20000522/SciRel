# 公开判定与接受边界

必须安装当前包内的 SciRel wheel，并实际调用 `scirel.kinetic.solve_atomic_slab_transport`。

入口正向密度、边界分布积分和总密度的含义必须可读回；派生求解网格不能用原始 50 点背景网格替代。输出数组必须绑定实际 `x_m`、速度轴和形状。

若 `generation_stopped=false` 且 `generation_stop_reason=max_generations`，结果状态必须为 `HOLD_GENERATIONS`；这仍可保存诊断分布，但不属于正常完成。

若公开 API 没有返回题面要求的某个字段，返回必须列出 `missing_outputs` 和具体原因，不能用零、形状占位、平滑或插值掩盖缺失。

本题的物理/数值科学接受仍 pending；代次截断值是内部停止量，不是最终误差保证。
