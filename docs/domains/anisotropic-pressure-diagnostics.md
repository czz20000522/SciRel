# 各向异性压强诊断草稿

状态：**开发期领域索引草稿，待领域专家组织和确认**。下列判据只对应已记录的实现和样本，不是普适稳定性结论。

- [平行压强关系残差](../../catalog/examples/scirel.diagnostics.parallel-pressure-residual.json)将所有输入样本展平并按磁场幅值 `B` 排序，对 `p_parallel/B` 在 **B 值空间**求有限差分，再与 `p_perp` 比较。它不是 R-Z 或沿场空间导数；`passed` 只表示给定样本与 `rtol` 下的归一化残差通过。
- [火焰管与磁镜裕度](../../catalog/examples/scirel.diagnostics.firehose-mirror-margins.json)计算 Pa 量纲的 `B^2/mu0 + p_perp - p_parallel` 和 `B^2/mu0 - B*d(p_perp)/dB`。导数同样按 B 值排序；两个 `stable` 标志只表示给定样本的最小裕度严格为正。现有各向异性力平衡资产的无量纲 margin 不与这里的 Pa 裕度视为同一端口。
- [逐点火焰管压强裕度](../../catalog/examples/scirel.diagnostics.pointwise-firehose-margin.json)只返回逐点的 Pa 量纲 `B^2/mu0 + p_perp - p_parallel`,与组合诊断的 `firehose_margin` 字段逐位一致。它没有导数、没有磁镜分支、没有最小值、也没有任何 stable 标志;单样本与全等 B 是正常输入域。该资产是 2026-09-27 出库评测(flat-B 与 state-json 两个 holdout)显示的合同级补救:调用方只需要逐点量时,不应触发组合资产中集合依赖的磁镜分支与退化零导数约定。正值不被标注为稳定,也不构成任何完整物理判据。

三项诊断均不检查完整平衡模型是否成立。其中带导数的两项(火焰管与磁镜裕度、平行压强关系残差)对常 B 样本将导数按实现定义为零,非退化样本的重复或近重复 B 会被拒绝;这两条导数/重复-B 规则不适用于逐点火焰管压强裕度,后者不构成任何跨样本量,单样本与全等 B 均为正常输入。保存的 Pleiades 候选、出库评测证据和当前直接测试只支持有界开发证据。专家待决:正 B 与压力适用域、有限差分收敛/采样密度、与具体物理稳定性判据的映射、无量纲 margin 的独立身份或有据适配,以及来源许可证。
