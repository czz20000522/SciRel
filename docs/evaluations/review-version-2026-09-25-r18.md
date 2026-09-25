# SciRel 镜端动理学/Hall 坐标合同待审 successor r18

状态：**开发期待审，不是科学认可或公开发行**。r17 原样保留；没有上一可信版本时，首次专家审核仍覆盖全部 68 个公共资产。本轮没有新合格 L1，也未改科学运行代码或 dev15 wheel。

## 组合与证据

[约化 Hall 图](../../catalog/examples/scirel.equilibrium.reduced-hall-anisotropic-picard.json)当前以 `psi=R A_phi`、`Wb/rad` 作为磁通函数合同。[动理学镜端 Hall 组合图](../../catalog/examples/scirel.equilibrium.kinetic-mirror-hall-equilibrium.json)不做数值换算，把当前 Hall `B` 与 `psi` 原样传给[网格镜端闭合](../../catalog/examples/scirel.kinetic.grid-mirror-kinetic-closure.json)。本轮将外层 `psi_vac`、`g_psi`、返回 `psi` 分别说明为 `Wb/rad`、`Wb/rad/A`、`Wb/rad`，并说明 `kinetic_config` 中的 `psi` 相关剖面须按这一坐标定义。历史 L1 和审核记录不回写；曾把旧 `Wb` 标签理解为完整链磁通的消费者须审查兼容性。

独立镜端图并不从 `psi` 数值重建磁场，而用它在调用方指定剖面上插值；旧来源将该坐标标为 `Wb`。新增固定剖面回归将整个坐标乘 `2*pi`，选定压力、密度和端电势保持一致；另一条回归保持密度回调的旧尺度不变，则返回密度出现可测变化。这只验证两组制造条件；其他调用方函数或查表数据仍须按传入坐标定义。现有真实双子图回归的真空输入 `psi=0.5 R²` 在内部点给出 `B_Z=1 T`；合成对角 Green 反馈、严格相容性和有界收敛仍通过，但它不是圆丝/镜像 Green 与镜端状态的端到端实物验证。

实际受影响测试、安装态回归、文档验证、开发 catalog 和冻结摘要见本版快照 `test-evidence.md`。待专家确认的是镜端剖面的科学定义、非零 Hall 与真实 Green 的共同适用域、近零分母相容性、来源与许可证；可信晋级和公开发行仍阻断。
