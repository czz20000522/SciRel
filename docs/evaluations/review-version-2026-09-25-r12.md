# SciRel 首次整版待审 successor r12

状态：**开发期待审材料，不是科学认可或公开发行**。r11 冻结快照保持原样；本轮不修改科学 callable 或 TaskGraph 运行代码，只补 Frank-Egedal 压强闭合关系族的 exact documents、领域草稿和一个与实际实现不符的历史图合同说明，并绑定内部 `0.1.0.dev14` 构建。

## 首次审核范围与增量

目前没有上一可信版本。专家首次审核仍覆盖 **68 个公共资产（56 Operator、12 TaskGraph）** 及其组合合同，而非仅审核 r11 到 r12 的差异。开发 catalog 现为 `partial: 62/68`（52 Operator、10 TaskGraph），还缺 **6** 份 exact documents。原有 57 份 exact documents 仅机械更新 `implementation_version`；版本号变化不构成新的科学证据或批准。

本轮新增的五份文档是 [径向包络](../../catalog/examples/scirel.kinetic.frank-egedal-radial-envelope.json)、[源模态投影](../../catalog/examples/scirel.kinetic.frank-egedal-source-projection.json)、[热离子矩](../../catalog/examples/scirel.kinetic.frank-egedal-hot-ion-moments.json)、[压强状态](../../catalog/examples/scirel.kinetic.frank-egedal-pressure-state.json)和[压强闭合 TaskGraph](../../catalog/examples/scirel.kinetic.frank-egedal-pressure-closure.json)。图依赖第五个既有的损失锥谱 exact document；五份新文档与既有文档形成依赖闭包。领域索引草稿见 [Frank-Egedal 压强闭合](../domains/frank-egedal-pressure-closure.md)，仅汇集实现有依据的关系、接线条件、证据和待决项，由专家决定领域结构。

维护的图合同 YAML 原称 `turning_b` 覆盖 `mirror_ratio`，但源模态与热离子矩函数均优先读取 `mirror_ratio`。本轮仅改正 SciRel 测试合同文字，新增同时传入两者和回退路径的回归，以及图精确返回键断言；没有改写冻结来源记录或科学实现。历史描述差异仍是专家需核实的科学合同问题。

## 验证与证据上限

独立审阅对照了五份文档、现有源码、直接测试和历史 provenance，未发现新增文档的阻断性科学合同错误；发现并修正两处当前有效 catalog 文档的旧覆盖数。全套测试 **863 passed、43 skipped**；62 份文档源码态的结构、签名与示例通过。内部 wheel `0.1.0.dev14` 无源码安装态的相关直接/图/公共 API 测试 **34 passed**，62 份文档安装态签名与示例通过。确切 wheel、catalog 和环境边界见快照 `test-evidence.md`。

测试只证明所列数值、输入边界和工程绑定。它们不证明任意镜比下谱的完整性、源模型适用性、默认求积误差、完整磁平衡，或把历史 `psi` 的 `Wb` 标签直接接到真空场链的 `Wb/rad` 约定。本轮没有消费新的合格 L1：第一阶段合格交付根仍为空，保存的 Pleiades 材料仅作为历史开发来源。合格冻结原料到来后须与开发基线和未发布候选重新比较，不按项目名直接导入。

## 专家与跨线待决

- 首次 68 资产及反向依赖的模型、单位、边界、适用域和科学证据审查；剩余 6 份 exact documents。
- `mirror_ratio` 与 `turning_b` 的优先级是否符合目标物理输入习惯，损失锥谱/求积误差的适用域，以及压力、密度、电子能量尺度与 NBI 源模型的依据。
- 历史 `psi` 单位标签与真空场链的换算、同网格物理一致性、来源许可证和后续合格 D1 对照。
- 版本级专家认可与可信晋级尚未实现；公开发行和 `scripts/check.ps1 -Mode release` 继续阻断。

专家只认可部分内容时须在隔离开发版剔除或返工，重新验证并冻结 successor，不改写本快照。
