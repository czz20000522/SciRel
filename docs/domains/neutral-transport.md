# 中性粒子输运

状态：开发期叶子关系导航，待领域专家划定完整输运问题；不代表 KN1D 代际迭代、碰撞闭合或终端诊断已经整合。

## 开发样例关系

- [中性物种热速度标度](../../catalog/examples/scirel.kinetic.thermal-speed-scale.json)从 eV 温度和以保存氢质量为基准的质量因子计算 m/s 速度；历史参数名 `mass_amu` 不表示标准原子质量单位。
- [单代中性分布密度归约](../../catalog/examples/scirel.kinetic.generation-density-reduction.json)按调用方提供的柱坐标权重和轴向单元宽度，将 `(nvr, nvx, nx)` 分布归约为 `(nx,)` 密度；它不构造速度网格或求解输运方程。
- [入射中性边界通量归一化](../../catalog/examples/scirel.kinetic.incoming-boundary-flux-normalization.json)按正向轴向速度半空间的预缩放通量，将调用方的边界形状缩放到目标通量的绝对值；目标为零时返回零尺度与零边界。
- [空间源形状归一化](../../catalog/examples/scirel.kinetic.spatial-source-shape-normalization.json)用调用方空间坐标的梯形积分将非负源剖面归一化，并返回原始积分。
- [圆柱速度空间积分权重](../../catalog/examples/scirel.kinetic.cylindrical-velocity-quadrature.json)从归一化 `vr`、`vx` 网格构造 ghost 面、环形径向测度、体积权重和差分系数；`volume` 可作为 Maxwellian 速率平均的 `cylindrical_volume` 输入。
- [平移 Maxwellian 离散种子](../../catalog/examples/scirel.kinetic.shifted-maxwellian-seed.json)在调用方速度网格和体积权重上构造逐 shift 归一化指数初值，保留来源的严格内部 `-80` clamp；输出尚未经过离散矩补偿。

这六项没有直接资产依赖；边界归一化接收调用方提供的热速度和柱坐标权重，不在函数内部构造它们。积分权重与种子、速率平均的端口组合由直接测试覆盖。链接指向 `catalog/examples/` 开发 pilot 的 exact documents，不代表专家批准或公开发布。

## 证据与待整理项

有效实数输入上的有限保存点与摘要锁定的 KN1DPy 归档实现精确相等；SciRel 对非实数输入、热速度派生质量下溢、密度溢出以及边界归一化的非有限输入和输出采用已声明的失败合同。来源项目的 whole-source D1 资格已撤回，有限点比较不能替代重新冻结、科学审核或许可证决定。其余中性输运算子、组合顺序、状态与停止条件仍待逐项核对。
