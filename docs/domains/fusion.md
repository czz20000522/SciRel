# 聚变反应与源项领域草稿

状态：**开发期领域索引草稿，待领域专家组织和确认**。这里描述关系与缺口，不批准具体资产；精确端口和证据范围以各 asset document 为准。

## 问题与现有能力

- [Bosch-Hale 热反应率](../../catalog/examples/scirel.fusion.bosch-hale-reactivity.json)：按四个反应通道，以离子温度求 Maxwellian `<sigma v>`。输入为 keV，输出为 `m^3/s`。这是局部反应率，不处理燃料组成、密度、反应功率或快离子能量沉积。
- [DD 中子实验室能量](../../catalog/examples/scirel.fusion.dd-neutron-lab-energy.json)：从两个 D 离子速度和探测方向计算 D(d,n)3He 中子实验室动能。这是非相对论二体运动学，不提供反应率、角分布权重或谱强度。

两个关系可能参与同一上层诊断，但目前不存在已审核的公共组合图把它们连接起来。DT 功率源项、alpha 电子/离子沉积、快离子减速、燃料/杂质密度与截面仍属待整合能力；不能仅凭这两条关系推断这些功能已具备。

## 模型条件与证据

反应率采用 Bosch-Hale Maxwellian 拟合，温度必须已经以 keV 给出。SciRel 不隐式截断温度；正温度的数值可计算性不等于拟合在全域具备物理精度。ASCOT5 来源有编译源码金值，TokaGrad 的 DT 实现只提供 source-free 方程/不变量证据且含舍入系数与夹取，具体比较见[开发整合记录](../evaluations/intake-2026-09-25-bosch-hale-reactivity.md)。DD 能量关系的常量和非相对论适用性限制见其 exact document。

专家待决：各反应拟合的可信温度范围、来源许可证、TokaGrad 变体是否保留、聚变功率及快离子分配的标准身份和组合边界。文档未覆盖的科学关系不能由下游 Agent 自行补造为可信资产。
