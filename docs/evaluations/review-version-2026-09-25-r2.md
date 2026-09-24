# SciRel 首次整版待审 successor

状态：**冻结待审材料，未获专家科学认可，不可公开发行**。上一份[开发待审说明](review-version-2026-09-25.md)绑定 `06c1122` 的 `15/63` 快照，是当时的历史证据；本说明不修改它，也不把它视为可信基线。后续确切 Git commit/tree、wheel、catalog、exact documents 与实际验证由 `scirel.review-version.dev` manifest 绑定，任何实质修改再形成新的 successor。

## 首次审核范围

SciRel 仍无上一可信版。因此专家首次整版审核覆盖当前 **64 个公共资产（52 个 Operator、12 个 TaskGraph）**，而非仅审从 `06c1122` 起的 Git diff。`catalog/examples` 现有 **16** 份有效 exact documents，开发 catalog 仍为 `partial: 16/64`；其余 **48** 份的科学合同、来源和测试证据尚未完成精确文档，阻断整版可信晋级。旧 `provenance/admitted-assets.json` 是历史开发证据，不是专家批准。

与上一待审开发提交相比，本 successor 的科学变化是新增[解析等离子体色散函数](../../catalog/examples/scirel.kinetic.plasma-dispersion-function.json)，并在[关系族比较](intake-2026-09-25-plasma-dispersion.md)中分离 PDRK/fluidBW 的数学重合、近似阶数变体和来源合同错误。已有[波矢关系](../../catalog/examples/scirel.geometry.planar-wavevector-projection.json)的实现未改，但其第一阶段严格冻结交接已经到达；原[整合记录](intake-2026-09-25-planar-wavevector.md)保留原判断并追加时间线。两个新增关系都未重绑现有 TaskGraph；这只说明**本次变更**没有新增反向组合影响，不能免除首次基线中 12 个 TaskGraph 的科学审核。

## 可审材料与门禁

- 文档主入口：16 份 `scirel.asset-document.v1` exact documents；每条身份、端口、单位、适用域、失败语义和证据上限以其唯一文档为准。
- 代码和测试：manifest 绑定的 Git tree 含 `src/scirel`、直接科学测试、组合测试及公共 API；逐文件文档摘要、wheel SHA-256、catalog root digest 和测试证据文件摘要均进入同一待审快照。
- 来源：第一阶段在 2026-09-25 的独立交接列明七个停写候选的 source/candidate tree 摘要、严格 D1 门禁、回传位置和证据上限。SciRel 对 PDRF、PDRK、fluidBW 的直接来源代码与包摘要另行固定并作有界比较；D1 证明提取来源闭合，不证明 SciRel 物理标准化获批。
- 验证：以随快照复制的 `test-evidence.md` 为实际结果，不从待审状态推断测试通过。`affected` 应选择新增算子及相关合同测试；整版冻结前另跑全仓和安装态文档/直接测试。缺少真实证据时不得补写“通过”。

## 专家待决

1. 首次基线尚缺 48 份 exact documents；不能只批准 16 份就把包含 64 个可导入资产的整版标可信。可以选择继续补齐，或明确剔除未认可资产并在 successor 重新验证。
2. 波矢 `1/m` 转换与 PDRK 扫描状态未被 SciRel 吸收；专家需审其身份、单位条件及未来组合边界。
3. 色散函数的 `z` 归一化约定、解析 `wofz` 相对 Weideman 截断的数值差异、来源文档错误的修正以及是否保留来源近似变体均需专家裁决。
4. 12 个现有 TaskGraph、许可证、独立离线依赖安装和 `.dev` 到正式 `v1` 合同冻结仍待处理。旧逐项 `approved` action 不授权该整版；`scripts/check.ps1 -Mode release` 保持关闭。

专家部分认可时，不能修改这份快照的标签来掩盖未认可代码；在隔离开发树返工或剔除，重跑受影响验证并冻结新的 successor。
