# 聚变反应与源项领域草稿

状态：**开发期领域索引草稿，待领域专家组织和确认**。这里描述关系与缺口，不批准具体资产；精确端口和证据范围以各 asset document 为准。

## 问题与现有能力

- [Bosch-Hale 热反应率](../../catalog/examples/scirel.fusion.bosch-hale-reactivity.json)：按四个反应通道，以离子温度求 Maxwellian `<sigma v>`。输入为 keV，输出为 `m^3/s`。这是局部反应率，不处理燃料组成、密度、反应功率或快离子能量沉积。
- [DD 中子实验室能量](../../catalog/examples/scirel.fusion.dd-neutron-lab-energy.json)：从两个 D 离子速度和探测方向计算 D(d,n)3He 中子实验室动能。这是非相对论二体运动学，不提供反应率、角分布权重或谱强度。
- [DD 中子发射各向异性因子](../../catalog/examples/scirel.fusion.dd-neutron-emission-anisotropy.json)：按 Brown-Jarmie 冻结系数表逐事件把反应物/中子/旋转速度映射为各向异性因子。与上条同源 FIDASIM 但关系不同（能量 vs 角分布归一），输入域受表顶约束（一般条件 `0.5*scale*|v1-vrot|^2 < 116.909 keV`）。
- [一阶 Larmor 引导中心修正](../../catalog/examples/scirel.fusion.first-order-larmor-correction.json)：按源 FLR 0/1/2 阶把引导中心状态映射为粒子状态；order-2 消费调用方供给的 12 项柱坐标磁场态。同属 FIDASIM 快离子运动学链，但合同独立于前两条。
- [NBI 源面射线与孔径接受](../../catalog/examples/scirel.fusion.nbi-source-plane-ray.json)：把调用方提供的源面均匀/发散变量(variate)映射为束坐标源点与单位射线，并按矩形/椭圆孔径逐个判定接受（FIDASIM `mc_nbi` 源面分支，N2）。
- [有限直角束网格射线交点](../../catalog/examples/scirel.fusion.beam-grid-ray-intersection.json)：按源码六面枚举顺序求射线与有限直角束网格的入口/出口与弦长（FIDASIM `grid_intersect` 有限分支）；`in_plasma` 判定仍由框架边拥有。
- [NBI 轨迹初始化图](../../catalog/examples/scirel.fusion.nbi-trajectory-initialization.json)：N2 组合图——归一化先行，`source_ray` 与 `cell_directed` 两分支互斥执行；串行 RNG 状态路径是声明未移植的运行时边界，拒绝重采样由调用方驱动。
- [DCX/HALO 迭代密度反馈](../../catalog/examples/scirel.fusion.halo-iteration-feedback.json)：halo 种群迭代的一轮密度反馈——增长守卫、种群合并、`seed_dcx` 份额与 Fortran 截断的下一轮 marker 数（N3，`src/fidasim.f90:13293-13420`）。
- [DCX/HALO 迭代反馈序列图](../../catalog/examples/scirel.fusion.halo-iteration-feedback-sequence.json)：N3 有界显式反馈序列——状态、顺序、停止分支与迭代上限全部显式声明，序列必须恰好在源停止分支结束；MC marker、reservoir、MPI 与 HDF5 仍在图外。

两个关系可能参与同一上层诊断，但目前不存在已审核的公共组合图把它们连接起来。DT 功率源项、alpha 电子/离子沉积、快离子减速、燃料/杂质密度与截面仍属待整合能力；不能仅凭这些关系推断这些功能已具备。

## 模型条件与证据

反应率采用 Bosch-Hale Maxwellian 拟合，温度必须已经以 keV 给出。SciRel 不隐式截断温度；正温度的数值可计算性不等于拟合在全域具备物理精度。ASCOT5 保存的编译源码金值与 TokaGrad 的 source-free DT 方程/不变量测试仍是有界开发证据；两项目原严格 D1 资格均已撤回，不能视为当前合格原料。TokaGrad 实现另有舍入系数与夹取，具体比较及资格更正见[开发整合记录](../evaluations/intake-2026-09-25-bosch-hale-reactivity.md)。DD 能量关系的常量和非相对论适用性限制见其 exact document。

专家待决：各反应拟合的可信温度范围、来源许可证、TokaGrad 变体是否保留、聚变功率及快离子分配的标准身份和组合边界。文档未覆盖的科学关系不能由下游 Agent 自行补造为可信资产。
- [DCX 热物种选择](../../catalog/examples/scirel.fusion.dcx-thermal-species-selection.json)：按源码物种循环下标选取热离子质量（N3）。
- [DCX/HALO colrad 初态加权](../../catalog/examples/scirel.fusion.dcx-halo-colrad-initial-state.json)：单标记初态密度加权与光子快离子修正；同位素分支按束质量严格相等判定。
- [碰撞辐射速率矩阵组装](../../catalog/examples/scirel.fusion.collisional-radiative-rate-matrix.json)：由调用方三张跃迁表与局域等离子体态组装 colrad 实速率矩阵，保留表坐标插值、低率阈值与 Einstein 对角重写。
- [碰撞辐射本征态推进](../../catalog/examples/scirel.fusion.collisional-radiative-state-advance.json)：本征分解推进一个时间步并投影光子率；零特征值分支按保存臂规则钉定（与 Fortran 源的分歧已登记待专家裁定），等离子体外走弹道分支。
- [DCX/HALO 标记初始化图](../../catalog/examples/scirel.fusion.dcx-halo-marker-initialization.json)：N3 组合图——按源顺序组合位置采样、调用方 plasma/ CX-rate 能力、物种选择、halo 速度与初态加权；colrad 推进与 reservoir 仍在图外。
