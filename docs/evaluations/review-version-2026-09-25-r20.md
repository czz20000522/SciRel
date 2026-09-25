# SciRel 各向同性压力磁通合同待审 successor r20

状态：**开发期待审，不是科学认可或公开发行**。r19 原样保留；没有上一可信版本，首次专家审核仍覆盖全部 68 个公共资产。本轮没有合格新 L1，没有修改科学运行代码或 `0.1.0.dev15` 内部 wheel。

## 科学增量与兼容边界

[压力磁通状态](../../catalog/examples/scirel.equilibrium.pressure-flux-state.json)、[各向同性 Picard 单步](../../catalog/examples/scirel.equilibrium.isotropic-picard-step.json)和[有界压力磁通图](../../catalog/examples/scirel.equilibrium.isotropic-pressure-flux.json)现统一以 `psi=R A_phi` 的 `Wb/rad` 作为开发合同。对应 `g_psi` 是 `Wb/rad/A`，`dP/dpsi` 是 `Pa/(Wb/rad)`，`psi_edge` 与样条磁通坐标为 `Wb/rad`。维护的 TaskGraph YAML 和领域草稿同步更正；签名、数值、默认值和失败语义不变。历史 L1/审核记录未改写。

压力状态的单独坐标缩放回归显示：将 `psi` 乘 `2*pi`，样条导数除以 `2*pi`，边界坐标随之乘 `2*pi`。真实各向同性图在一个 active 单元、单步制造输入下，产生非零 cell current，离源目标点的等离子体磁通增量与圆丝直接 `R A_phi` 响应一致。反例将真空磁通和 Green 同时乘 `2*pi` 而保持同一压力函数：图的电流缩小 `2*pi`，磁通增量未随之放大，说明当前 `R*dP/dpsi` 电流公式不支持只靠磁通/Green 同步缩放就改成完整 `Wb`。曾按完整 `Wb` 理解旧标签的调用方须审查压力剖面、导数、电流公式与 Green 的整条链，不能局部换算。

该证据是同一圆丝关系族的有限制造输入与坐标变换反例，不是独立源码 parity、任意压强律/Green 的物理证明或真实装置平衡。尤其这张图不返回完整 `BR/BZ`、边界或压强场；不能只凭 `psi` 字段把它接入诊断或材料支撑。来源许可证、模型适用域、真实边界、收敛域和首次可信版本资格仍需专家判断。确切测试、catalog 与快照摘要见本版 `test-evidence.md`；开发通过不触发可信晋级或公开发行。
