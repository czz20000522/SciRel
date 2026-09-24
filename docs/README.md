# SciRel 项目文档

SciRel 按长期独立 Python 项目维护。文档只保存稳定合同、可复用流程和当前实现边界；单次任务参数、临时进度与重复状态不进入这里。

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
- [动理学等离子体波领域草稿](domains/kinetic-plasma-waves.md)：当前关系族、组合边界、证据与专家待决问题。
- [各向同性平衡与点诊断领域草稿](domains/isotropic-equilibrium-and-observations.md)：有界 Picard 反馈、只读观测投影及跨图缺口。
- [各向异性 Picard 平衡领域草稿](domains/anisotropic-picard-equilibrium.md)：压强力、磁通松弛、调用方闭合和终态门槛。
- [各向异性参数反演领域草稿](domains/anisotropic-parameter-inference.md)：观测残差、单次试探、参数搜索和调用方模型边界。
- [双温磁镜动理学与准中性闭合领域草稿](domains/mirror-kinetics-and-quasineutrality.md)：镜端速度矩、Boltzmann 响应、准中性求根及组合边界。
- [Frank-Egedal 压强闭合领域草稿](domains/frank-egedal-pressure-closure.md)：损失锥模态、热离子矩、压强组装和历史合同差异。

## 当前实现边界

当前 `0.1.0.dev15` 开发树包含 52 条历史资产候选和 16 条后续开发资产；当前 68 条公共资产均有 catalog exact document，但尚未经整版专家认可。workflow 已具备 host-independent 状态协调、artifact 关联、逐项审核/release 的旧门禁和最小 fixture；真实 L1 的理解与整合由 skill 驱动的模型完成，不属于状态机能力。版本级专家认可、生产审核插件接线、完整 L1 整合、v1 合同冻结、固定发行工具链和正式发布授权尚未完成。

新增长期机制时，优先扩展上述权威文档和可执行检查。只有出现独立 owner、不同生命周期或明显不同读者时才拆新文档，避免用报告数量代替项目治理。
