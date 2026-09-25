# 各向异性参数反演关系族草稿

状态：**开发期关系索引，待领域专家组织和确认**。以下描述当前实现及其证据上限，不证明真实观测反演的物理有效性，也不构成可信版本或发行批准。

## 关系与组合

- [拉丁超立方采样](../../catalog/examples/scirel.inference.latin-hypercube-sampling.json)可按给定参数边界和种子生成可重复的初始样本；它不判断参数边界是否具有物理意义。
- [观测残差归约](../../catalog/examples/scirel.diagnostics.observation-residuals.json)对已匹配的磁通环与选定 Thomson 类预测逐项除以 `sigma`，再计算残差平方和；它不完成观测对齐、相关误差建模或诊断标定。
- [单次试探](../../catalog/examples/scirel.inference.anisotropic-trial-evaluation.json)调用由使用者提供的平衡求解和诊断函数，再调用残差归约函数。嵌套求值抛异常时，它返回单元素 `1e12` 惩罚残差、`equilibrium=None` 和失败原因；这不是一个有效的平衡解。
- [参数优化](../../catalog/examples/scirel.inference.anisotropic-parameter-optimization.json)使用 SciPy 搜索，可先从拉丁超立方样本选择初值，并保留已记录的最佳试探及优化器状态。有限次成功运行不保证全局最优或物理可辨识性。
- [直接各向异性反演图](../../catalog/examples/scirel.inference.direct-anisotropic-inversion.json)把以上关系连接起来，但平衡求解器与合成诊断仍是调用方端口。图内的单次试探是明确的科学算子节点，不是隐藏在 glue 中的关系；本图不固定使用某一种平衡或诊断 TaskGraph。

当前图的合成测试使用调用方给定的求解和诊断端口恢复简单参数，并覆盖失败惩罚、无效方法及输入端口；其中一个组合案例在等向压力极限接入 SciRel 自由边界各向异性平衡、非零 Green 响应与解析磁通环目标。图自身不规定磁通单位；接入该平衡时 `psi=R A_phi` 为 `Wb/rad`，`g_psi` 为 `Wb/rad/A`，案例的调用方诊断端口显式计算圆环磁通 `2πψ`（`Wb`）。[现有平衡合成点诊断图](../../catalog/examples/scirel.diagnostics.equilibrium-synthesis-diagnostics.json)的历史 `flux_loops` 键只采样 `psi`，不做该转换；不能把其 `Wb/rad` 输出直接与 `Wb` 观测比较。该案例不验证真实装置数据、任意各向异性压力闭合、观测协方差、反演唯一性或跨模型适用域。历史 Pleiades 来源映射仍是开发证据；当前没有合格的新 L1 交付。

## 专家待决

参数身份与单位、边界和先验选择；调用方平衡/诊断模型的科学适用性与版本绑定；观测位置和误差尺度是否匹配；异常惩罚 `1e12` 对搜索结果的影响；优化器成功、最佳试探与嵌套平衡收敛之间的接纳规则；来源资格和公开分发许可证。只有确认这些条件后，才能讨论某个具体反演任务是否落在本关系族的能力内。
