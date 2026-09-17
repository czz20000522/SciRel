# SciRel 项目文档

SciRel 按长期独立 Python 项目维护。文档只保存稳定合同、可复用流程和当前实现边界；单次任务参数、临时进度与重复状态不进入这里。

- [架构与科学资产合同](architecture.md)：Operator、TaskGraph、科学身份、公共 API 和治理边界。
- [规模化目录合同](catalog.md)：数万资产下的分片、渐进检索、依赖索引与一致性要求。
- [标准化资产文档需求](requirements/asset-documentation.md)：每条资产必须提供的科学、调用、证据和 provenance 字段。
- [薄 MCP 适配合同](requirements/thin-mcp-adapter.md)：固定 catalog 的发现、文档读取、callable 绑定与调用边界。
- [Catalog 与适配器设计](design/catalog-and-adapters.md)：framework-neutral 投影、MCP/CLI/云适配边界和 CodeFusion 交付清单。
- [CodeFusion 消费合同](integration/codefusion-consumer-contract.md)：发行绑定、导出集合、文档入口、callable/MCP、错误语义及跨项目职责差异。
- [开发与增量整合流程](development-process.md)：首次/增量整合、验证分层和发行候选流程。
- [贡献指南](../CONTRIBUTING.md)：开发环境、改动分类、兼容性和提交前检查。

## 当前实现边界

当前 `0.1.0.dev5` 是 52 条已准入资产的待发行候选。普通 Python callable、精确准入绑定、基于资产与反向图依赖的测试选择、admitted-only wheel、内容锁、科学回归和无源码验收已经存在。标准化文档、catalog builder 与薄 MCP adapter core 目前只覆盖依赖闭合的 4 条 pilot；剩余 48 条迁移、生产 MCP transport/server、固定发行工具链和正式发布授权尚未完成。相关文档必须区分目标合同与已实现覆盖范围。

新增长期机制时，优先扩展上述权威文档和可执行检查。只有出现独立 owner、不同生命周期或明显不同读者时才拆新文档，避免用报告数量代替项目治理。
