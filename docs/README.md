# SciRel 项目文档

SciRel 将已有科研代码整理为可复用的科学算子与任务图，供 Agent 分解用户需求、匹配能力并生成胶水代码，
形成满足需求的可执行程序。单项目内的自定义组合与跨项目组合都使用这一方法，核心科学实现通过资产复用，
本次程序负责正确连接和执行。

## 理解项目与使用方法

- [科学关系手册与查询入口](searchable-documentation.md)：按领域和求解问题阅读导读、已运行案例及正式函数合同，人和 Agent 共用文档快照。
- [项目定位](../README.md)：为什么拆解已有代码，以及科学资产、Agent 和胶水代码各自负责什么。
- [开发项目与科学包交付](design/project-and-distribution.md)：项目开发态、用户安装包、历史样本和分支/worktree 的多版本构建边界。
- [架构与科学资产合同](architecture.md)：Operator、可复用 TaskGraph 与本次运行实例的区别，以及科学实现和编排的边界。
- [科学请求工作流](requirements/scientific-request-workflow.md)：需求规范化、能力匹配、动态组合、执行和结果解释。
- [开发流程](development-process.md)：来源拆解、库整合与用户应用如何交接，怎样扩充和验证能力。
- [独立 D0-D3 拆解 skill 包](../skills/extraction/README.md)：可交给单独 Agent 并行执行，产出合并所需的有界原材料。

以下文档按工作入口组织。需求描述目标，设计描述实现边界，测试和运行证据决定当前能声称什么。
单次 L1 批次、harness 参数和临时进度不提升为长期合同。

## 维护科学库

- [手册编写与维护](handbook-authoring.md)：目录主归属、增章模板、案例执行证据和每批科学资产整合时的同步步骤。
- [架构与科学资产合同](architecture.md)：Operator、TaskGraph、科学身份、公共 API 与治理边界。
- [规模化目录合同](catalog.md)：分片索引、渐进检索和依赖索引。
- [标准化资产文档需求](requirements/asset-documentation.md)与[Catalog/适配器设计](design/catalog-and-adapters.md)：exact document、可验证 catalog 和消费投影。
- [科学领域能力](domains/README.md)：供专家完善的问题域导航；不替代 exact document，也不代表完整覆盖。
- [开发与增量整合流程](development-process.md)及[贡献指南](../CONTRIBUTING.md)：科学变更、受影响测试、固化和发行门禁。
- [AOCI 项目索引与增量维护](design/aoci-index-maintenance.md)：开发认知、稳定批次维护、工作树绑定及规模增长的预算与覆盖边界。

## 从 L1 到审核

- [领域需求](requirements/scirel-workflow.md)与[Workflow 设计](design/scirel-workflow.md)：开发整合、无变化记账、最终冻结审核和 release 的所有权与状态。
- [开发、待审与可信版本](design/development-trust-versions.md)：新政策的目标语义及现有需求、设计和 skill 的最小调整切片；尚非已交付的 workflow。
- [SciRel 整合 skill](../skills/development/integration/scirel-integration/SKILL.md)与[外部 Agent 整合方法](integration/external-harness-workflow.md)：模型比较 L1、冻结基线和未发布候选，产出文档、代码、测试；脚本不替代语义判断。
- [SciRel 开发 skill 包](../skills/development/README.md)：消费拆解包，负责修正、合并、项目交付和最终审核准备；与拆解包独立分发。
- [L1 inventory 参考探针](design/l1-inventory.md)：可选结构检查及不同时间、目录的压测快照；它不是整合协议，也不证明科学覆盖。
- [L1 wire smoke](../scripts/run_l1_wire_smoke.py)：确定性 body/fixture 检查，不是实际项目的科学整合或专家批准。

## 发行与使用

- [科学请求需求](requirements/scientific-request-workflow.md)、[设计](design/scientific-request-workflow.md)和[求解 skill](../skills/development/usage/scirel-solving/SKILL.md)：用户需求到能力匹配、组合、执行与证据有界解释。
- [发行说明索引](release.md)：只记录每个 Git 版本的短变更说明；完整 API、手册和 exact documents 继续维护在当前 `docs/` 树中。
- [发行批次策略](design/scirel-release-batching.md)：区分能力线、维护批次和 post-candidate 工作树，避免每个函数小修都触发完整发行流程。
- [薄 MCP 适配需求](requirements/thin-mcp-adapter.md)及[CodeFusion 消费合同](integration/codefusion-consumer-contract.md)：适配器只消费已发布的 catalog/wheel，不定义新的科学身份。
- [CodeFusion 宿主插件需求](requirements/codefusion-plugin.md)、[插件合同](integration/codefusion-plugin-contract.md)及[中性 Agent 验收](integration/codefusion-runner-acceptance.md)：宿主提供执行、artifact、身份和审核 UI；SciRel 拥有领域结论。

## 当前实现边界

- `src/scirel/` 是可独立调用的科学库；`src/scirel_workflow/` 与 `src/scirel_plugin/` 已有本地状态、合同及 fixture 测试。它们不等于真实 L1 项目经模型整合、专家审核和宿主产品链路联调已完成。
- `catalog/examples/` 仍为部分 exact-document pilot，不代表全部库能力；不能从 catalog 缺项推断没有对应算子，也不能把维护树中的所有代码视为可发布资产。
- `provenance/admitted-assets.json` 与 `scripts/build_admitted_distribution.py` 用于复核历史开发样本，不是新流程的批准事实或发布入口。隔离开发分支允许先集成和验证；最终冻结版本经专家认可及发行验证后才能晋级可信/发布版本。`scripts/release_index.py` 和 `scripts/finalize_release.py` 承担开发期候选索引与逐项固化门禁；旧单 draft release fixture 仅用于生命周期测试。
- 开发期 workflow/plugin 合同仍用 `.dev`；正式上线前应统一冻结为 `v1`。许可证、完整 exact documents、真实宿主接线和发行环境证据均须分别验收，不因本地 fixture 通过而自动获得。

需要判断某一轮是否完成时，以该轮的 L1 输入树、SciRel 基线与候选池、skill 内容、候选三件套、实际测试、专家记录和 release artifact 为证据；不要把历史压测数量当作当前状态。

## 目录职责

- `requirements/`、`design/`、`integration/` 保存可复用的需求、设计和跨系统合同；具体批次的状态、日志及参数不在这里维护。设计中的历史样本只说明当时的适用条件，不是当前进度。
- `domains/` 保存有依据的领域草稿与待专家裁定问题；资产级科学合同以 exact document 为准。
- `evaluations/` 保存带日期和证据引用的评估结论；大体积运行产物、临时工作副本及 wheel 留在 `build/verification/<run>/` 等对应运行目录。`scripts/` 保存可复用的工具，单次运行命令与探针随运行证据保存。
- 已有 manifest、测试或其他工作树引用的证据不直接移动；确需迁移时先核引用方与文件摘要，再在所属线路更新引用并复验。多人工作区中归属不明的文件保持原位。
