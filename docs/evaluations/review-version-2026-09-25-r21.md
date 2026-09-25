# SciRel 直接反演端口单位与组合证据待审 successor r21

状态：**开发期待审，不是科学认可或公开发行**。r20 保持原样；目前没有上一可信版本，首次专家审核仍覆盖全部 68 个公共资产。本轮没有合格新 L1，也没有修改运行代码、公共签名、数值默认值或 `0.1.0.dev15` 内部 wheel。

## 科学增量与适用边界

[直接各向异性反演图](../../catalog/examples/scirel.inference.direct-anisotropic-inversion.json)的 `solver_config` 是调用方求解器的输入，不固定磁通规范，也不执行单位转换。原文档把历史 N6 的 `Wb`/`Wb/A` 标签写成此端口单位；该标签不能用于当前 [自由边界各向异性 Picard 图](../../catalog/examples/scirel.equilibrium.free-boundary-anisotropic-picard.json)的接线。现在明确：接当前 SciRel 平衡时 `psi=R A_phi` 为 `Wb/rad`，`g_psi` 为 `Wb/rad/A`；其他调用方求解器由其自身合同决定。保存的 L1 合同和历史来源证据没有改写。

新增的公共组合回归使用均匀 `B_Z=1 T`、等向压力极限 `p_perp=p_parallel=2+p0 R`、非零对角 Green 和规则 `R-Z` 网格。由压力梯度得到 `J_phi=p0`，单元电流为 `p0 dR dZ`，故选定点的 `psi` 增量为 `g_psi p0 dR dZ`；调用方诊断端口再显式将圆环磁通计算为 `2*pi*psi`。以独立解析值生成一个合成观测，反演图恢复 `p0` 并检查返回平衡的 `psi`。这保护了当前两个公共图的一个有限接线实例，也防止把 `Wb/rad` 无声明地当成完整 `Wb` 观测。

该制造案例不验证各向异性压力闭合、真实诊断标定、任意 Green/边界、源码 parity、反演可辨识性或全局最优。`solver_config` 仍只受结构检查，实际维度相容性由调用方和领域审阅负责；不能把该测试推广为自动单位门禁。旧 L1 合同中的单位文字是历史证据，不因本次修正文档而取得当前来源资格。来源许可证、模型适用域与首次可信版本资格仍需专家决定。确切执行结果、开发 catalog 和快照摘要见本版 `test-evidence.md`。
