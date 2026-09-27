# SciRel 项目文档

SciRel 按长期独立 Python 项目维护。文档只保存稳定合同、可复用流程和当前实现边界；单次任务参数、临时进度与重复状态不进入这里。本页是稳定目录入口：指向各权威文档，并给出"当前实现边界"以最新冻结 review-version 证据为准的读取规则。

## 权威文档目录

- [架构与科学资产合同](architecture.md)：Operator、TaskGraph、科学身份、公共 API 和治理边界。
- [规模化目录合同](catalog.md)：数万资产下的分片、渐进检索、依赖索引与一致性要求。
- [标准化资产文档需求](requirements/asset-documentation.md)：每条资产必须提供的科学、调用、证据和 provenance 字段。
- [薄 MCP 适配合同](requirements/thin-mcp-adapter.md)：固定 catalog 的发现、文档读取、callable 绑定与调用边界。
- [科学请求工作流需求](requirements/scientific-request-workflow.md)：从用户需求规范化、能力匹配和动态组合到结果检查与解释的出库行为。
- [Catalog 与适配器设计](design/catalog-and-adapters.md)：framework-neutral 投影、MCP/CLI/云适配边界和 CodeFusion 交付清单。
- [科学请求工作流设计](design/scientific-request-workflow.md)：四类逻辑产物、harness/SciRel 职责和轴对称平衡首轮样例。
- [保存的 L1 inventory 参考探针](design/l1-inventory.md)：可选多项目结构索引的能力与边界。
- [外部 Agent 整合方法](integration/external-harness-workflow.md)：Claude Code、Codex、CodeFusion 等 harness 使用同一 SciRel skill 对照 L1 与当前库的方法边界。
- [CodeFusion 消费合同](integration/codefusion-consumer-contract.md)：发行绑定、导出集合、文档入口、callable/MCP、错误语义及跨项目职责差异。
- [开发与增量整合流程](development-process.md)：首次/增量整合、验证分层和发行候选流程。
- [SciRel L1 到 Release 需求](requirements/scirel-workflow.md)：领域生命周期、状态、标准化、审核和 release 门禁。
- [CodeFusion 宿主插件需求](requirements/codefusion-plugin.md)：中性 Agent 调用与专家审核插件边界。
- [SciRel Workflow 设计](design/scirel-workflow.md)：host-independent workflow 与 artifact 适配设计。
- [CodeFusion Plugin Contract](integration/codefusion-plugin-contract.md)：中性 invocation、审核 UI 和领域/平台失败边界。
- [CodeFusion 中性 Agent 验收](integration/codefusion-runner-acceptance.md)：与 Claude Code/Codex 使用同一输入和 skill 的对照方法。
- [SciRel 求解 skill](../skills/usage/scirel-solving/SKILL.md)：供不同 harness 规范化、规划、执行和解释用户科学请求的共同方法。
- [L1 wire smoke](../scripts/run_l1_wire_smoke.py)：开发期确定性 body 合同测试工具，不是语义整合入口。
- [贡献指南](../CONTRIBUTING.md)：开发环境、改动分类、兼容性和提交前检查。
- [科学领域导航](domains/README.md)：领域草稿的问题入口、科学边界与专家待决事项。

## 当前实现边界（以最新冻结证据为准）

当前开发树版本、资产数量与 exact-document 覆盖**不写死在本页**，以最新冻结 review-version manifest 为准。撰写本文时为 r81-v1：`0.1.0.dev58`、169/169 exact documents、`pending_unapproved`、无可信基线，快照 `build/verification/review-2026-09-27-r81-npa-store-family-v1/manifest.json`，专家版本说明 `evaluations/review-version-2026-09-27-r81.md`。后续冻结版落地后，更新本节指向新的快照与说明即可，其余链接保持稳定。

## 各类材料的职责与读取方式

- **冻结证据（`build/verification/…`，不入库目录树）**：每个 pending_unapproved 版本的 manifest、exact documents 摘要、wheel、catalog、review dossier 与 test evidence 的精确字节绑定。manifest 是该版本"当前实现边界"的唯一权威；`pending_unapproved` 只表示等待专家审核，不表示任何 D1 资格或专家认可。历史版本的快照原样保留，是治理记录，不是当前能力声明。
- **历史 provisional 来源**：`provenance/` 下的旧迁移样本（如 `admitted-assets.json`）与兄弟 checkout 中的保存 L1 包（KN1DPy、FIDASIM、GSEQ 等）只支持有界历史开发比较。旧 `admission`/决定标签与保存包的 ledger 声明都不是当前批准事实，也不是合格 L1 消费；合格 L1 交付根以当轮冻结记录的复核为准（近期各轮均复核为空）。
- **workflow/plugin 文档**：`requirements/`、`design/`、`integration/` 中的 workflow、catalog、插件与适配合同描述稳定机制与边界，不描述单批资产。旧逐项批准到 release 的 workflow/插件/脚本入口已阻断，现存实现只用于迁移与测试，不作为可用发行入口。
- **tests 与门禁**：`tests/` 中的领域回归、合同测试、计数同步测试与受影响选择器是开发门禁；`scripts/check.ps1`（affected/focused/full）与冻结脚本产生的实测回执记录在各版 `build/test-evidence-*.md`。测试通过不扩张科学合同，也不等于专家认可。
- **评估记录（`evaluations/`）**：`review-version-2026-09-27-r6x…r81.md` 是各冻结版的专家入口说明（增量、对照裁定、证据上限、开放问题）；`candidate-review-materials-index-2026-09-25.md` 按批绑定候选三件套的路径与 SHA-256。这些记录描述证据与待决，不伪造任何人工审核结论。
- **review_candidates/**：各批候选 proposal（代码副本、exact document 副本、family 测试）与 review.md，是专家审阅入口；digest 以索引与冻结 manifest 绑定为准。

## 边界速记

真实 L1 的理解与整合由 skill 驱动的模型完成，不属于状态机能力。版本级专家认可、生产审核插件接线、完整 L1 整合、v1 合同冻结、固定发行工具链和正式发布授权均未完成。新增长期机制时，优先扩展上述权威文档和可执行检查；只有出现独立 owner、不同生命周期或明显不同读者时才拆新文档，避免用报告数量代替项目治理。
