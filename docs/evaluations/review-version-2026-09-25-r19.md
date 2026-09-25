# SciRel 自由边界 Picard 磁通合同待审 successor r19

状态：**开发期待审，不是科学认可或公开发行**。r18 原样保留；没有上一可信版本，首次专家审核仍覆盖全部 68 个公共资产。本轮没有合格新 L1，历史 Pleiades 材料仍只作开发来源。科学运行代码和 `0.1.0.dev15` 内部 wheel 均未改变。

## 本轮科学增量

[电流反馈叶算子](../../catalog/examples/scirel.equilibrium.anisotropic-picard-feedback.json)和[自由边界 Picard 图](../../catalog/examples/scirel.equilibrium.free-boundary-anisotropic-picard.json)的开发合同现在将 `psi_vac`、返回 `psi`、墙通量修正及墙残差标为 `psi=R A_phi` 的 `Wb/rad`，将等离子体与墙磁通 Green 标为 `Wb/rad/A`。调用方压力闭合须按这一 `psi` 坐标解释剖面；曾按完整 `Wb` 使用旧标签的消费者必须重新核对数据及转换，不能只改一个端口。对应的维护 TaskGraph YAML 与领域草稿同步更新；历史冻结来源不回写。

叶算子回归在规则 R-Z 网格上构造真空圆丝、稠密 `gpsi/gBR/gBZ` 和单个非零电流单元，选离源目标点与直接逐丝 `psi/BR/BZ` 对照。真实自由边界图的**无墙分支**用调用方压力律产生非零 cell current，同一目标点的三场增量也与直接圆丝响应相符。这固定了当前实现不额外乘 `2*pi` 的约定，但只是有限制造输入、同一圆丝关系族的内部对照，不是独立源码 parity 或任意 Green/压强律的物理证明。

## 审核上限与待决

可选墙修正目前仅改变 `psi`，不把墙响应同步施加到返回的 `BR/BZ`；现有测试保护该行为。因此墙分支的三场不能宣称导数自洽，本轮不改科学运行代码，也不凭无墙证据批准该分支的物理适用性。专家还需审查墙响应与边界采样的一致性、调用方压力闭合的科学域、来源许可证、真实装置/源码同输入比较以及首次可信版资格。受影响测试、安装态验证、文档与 catalog 摘要和确切快照见本版 `test-evidence.md`；开发通过不触发可信晋级或公开发行。
