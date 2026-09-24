# 双温磁镜动理学与准中性闭合草稿

状态：**开发期领域索引草稿，待领域专家组织和确认**。本页只整理已实现的关系、组合和证据边界；精确端口与失败行为以链接的 asset document 为准，不构成科学认可。

## 问题与关系

- [双温镜约束速度矩](../../catalog/examples/scirel.kinetic.mirror-constrained-moments.json)以局部磁场、通量标签、电势和参考态计算离子密度、平行/垂直压强及俯仰积分。左右镜塞与电势可选，损失锥再填充比例改变被截断的粒子贡献；它不求解自洽电势。
- [准中性参考电子密度](../../catalog/examples/scirel.closures.quasineutral-reference-density.json)从正离子参考密度与电荷态给出单离子种的参考电子密度。[Boltzmann 电子响应](../../catalog/examples/scirel.closures.boltzmann-quasineutrality.json)在给定电势和参考态下返回电子密度、压强与电荷残差。两者并非一般多组分电荷平衡模型。
- [准中性电势二分求根](../../catalog/examples/scirel.closures.quasineutral-potential.json)只拥有有界括根和迭代控制；调用方提供随电势变化的对数电荷残差。残差的动力学/电子模型、单调方向和根的物理意义不由求根算子验证。
- [双温镜总压强状态组装](../../catalog/examples/scirel.kinetic.mirror-total-pressure.json)把已经计算出的离子矩和电子状态合并为总平行/垂直压强，并保留组分与残差。它不重新计算速度矩，也不判定准中性是否达到调用方阈值。
- [镜端准中性 TaskGraph](../../catalog/examples/scirel.closures.mirror-quasineutral-closure.json)在上述五个关系上反复评估离子矩和电子响应，以二分电势闭合局部准中性，再组装终态。迭代状态由图拥有，普通依赖仍是无环的。

## 证据与接线边界

直接图测试覆盖无镜塞解析极限、损失锥分支、零参考密度与 `profile(psi)` 输入；算子直接测试另外覆盖各自数值与错误输入。保存的 Pleiades 候选是开发来源证据，不是当前合格冻结 D1 交付或专家认可。历史压强组装描述与现实现有差异：后者只验证压强字段，密度和残差原样透传，调用方提供的电势也可保留；不能从旧描述推断额外校验。所有函数在 SciRel wheel 中作为 Python callable 运行，不依赖原项目 checkout。

当前图的 `psi` 是传递给剖面回调和动理学关系的通量标签，旧图合同标为 `Wb`；它与真空场链 `psi = R A_phi` 的 `Wb/rad` 约定尚未核对，不能凭名称直接连接。图只处理单个正离子种、等温 Boltzmann 电子和所声明的双温镜闭合；不覆盖多组分、各向异性电子、一般碰撞输运或完整平衡求解。专家待决：标准通量约定及适配、适用的镜端分布与边界、损失锥参数的物理来源、数值收敛范围、来源许可证和首次可信版本认可。
