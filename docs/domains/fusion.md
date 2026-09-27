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

两个关系可能参与同一上层诊断，但目前不存在已审核的公共组合图把它们连接起来。DT 功率源项、alpha 电子/离子沉积、快离子减速、燃料/杂质密度与截面仍属待整合能力；不能仅凭这些关系推断这些功能已具备。

## 模型条件与证据

反应率采用 Bosch-Hale Maxwellian 拟合，温度必须已经以 keV 给出。SciRel 不隐式截断温度；正温度的数值可计算性不等于拟合在全域具备物理精度。ASCOT5 保存的编译源码金值与 TokaGrad 的 source-free DT 方程/不变量测试仍是有界开发证据；两项目原严格 D1 资格均已撤回，不能视为当前合格原料。TokaGrad 实现另有舍入系数与夹取，具体比较及资格更正见[开发整合记录](../evaluations/intake-2026-09-25-bosch-hale-reactivity.md)。DD 能量关系的常量和非相对论适用性限制见其 exact document。

专家待决：各反应拟合的可信温度范围、来源许可证、TokaGrad 变体是否保留、聚变功率及快离子分配的标准身份和组合边界。文档未覆盖的科学关系不能由下游 Agent 自行补造为可信资产。
