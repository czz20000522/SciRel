# SciRel 轴对称各向异性图磁通合同待审 successor r16

状态：**开发期待审，不是科学认可或公开发行**。r15 原样保留；目前仍无上一可信版本，专家首次审核仍须覆盖 68 个公共资产。本轮没有新合格 L1，不改科学运行代码或 dev15 wheel。

## 图级增量

[轴对称各向异性 Picard 图](../../catalog/examples/scirel.equilibrium.axisymmetric-anisotropic-picard.json)内部每轮以 `B_R=-(1/R)dpsi/dZ`、`B_Z=(1/R)dpsi/dR` 解释 `psi`，其反馈叶算子和 P4 圆丝/镜像 Green 已在 r15 对齐 `psi=R A_phi`。本轮据此把该图当前开发合同及维护的 TaskGraph YAML 中的 `psi_vac`/返回 `psi` 改标为 `Wb/rad`、`g_psi` 改标为 `Wb/rad/A`，并要求调用方压力闭合以相同 `psi` 坐标解释剖面。签名、数值、默认值和物理门禁未改变；冻结历史来源仍保留原样。曾按完整 `Wb` 理解旧标签的消费者有语义兼容影响，不能只改文字或只缩放单个端口。

新增真实图级制造回归：17x17 对称 R-Z 网格、外部圆丝 `psi_vac`、镜像 Green 和一个 active plasma cell；各向同性线性径向压强给出非零 cell current。图的默认严格平行力相容门禁保持开启，仅运行一轮且不要求收敛。目标点的等离子体通量增量与独立逐丝 Green 计算一致，返回 `B_R/B_Z` 与两个圆丝直接场在 2% 内一致。该测试既观察到非零 Green 反馈，也检查没有偷偷乘 `2*pi`。

`pwsh ./scripts/check.ps1 -Mode affected` 仅选本图直接回归与文档测试，**25 passed**；原 dev15 wheel 以 `python -I` 从隔离 venv 的 `site-packages` 执行本图回归 **11 passed**。本轮文档校验、catalog 和冻结摘要见快照 `test-evidence.md`。r15 的 38 项受影响、68 份文档及 24 项安装态验证针对未改变的叶算子/wheel 仍可引用，但不冒充本轮图级重跑。

证据只覆盖这一制造输入和已测试的图端口，不证明任意压力律、真实装置、奇异自场、收敛或完整来源复现。reduced-Hall、free-boundary、kinetic-mirror 及其镜端闭合的旧 `Wb` 合同继续待迁移；自由边界图的墙修正还存在 `psi` 与返回 `BR/BZ` 不同步的问题。r14 的近零分母相容性限制、来源许可证、专家认可、可信晋级和公开发行均未解决。
