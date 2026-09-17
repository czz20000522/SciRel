# SciRel 规模化目录合同

本文定义 SciRel 从当前 52 条资产扩展到数万 Operator、数千 TaskGraph 时的目录边界。catalog 服务发现、依赖分析和发行核对；它是从已选发行内容重建的索引，不拥有准入、科学身份或发布权威。

标准资产字段的权威需求见[标准化资产文档需求](requirements/asset-documentation.md)，catalog builder 与 MCP/CLI/云适配边界见[设计](design/catalog-and-adapters.md)。当前 `catalog/examples/` 是 4/52 的依赖闭合 pilot，不代表完整目录。

## 设计目标

- 不要求 Python import 全部模块来发现能力。
- 不要求模型、开发者或工具一次加载全量合同。
- 精确记录与运行 wheel、revision lock 和内容摘要保持一致。
- 支持按领域增量更新、确定性重建、反向依赖查询和旧 release 恢复。
- 检索失败与“没有能力”分开；缺元数据、预算耗尽和不适用有不同结果。

## 逻辑投影

一个 release 生成以下只读逻辑投影。物理文件可按规模分片，但逻辑字段和摘要规则必须稳定。

| 投影 | 内容 | 典型读取范围 |
| --- | --- | --- |
| release manifest | schema/release、根摘要、数量、分片引用、构建环境 | 每次检索一次 |
| route index | asset ID、kind、领域、输出、关系方向及高区分度 facets | 相关分片 |
| capability summary | 简短用途、关键输入输出、模型/几何/边界、适用域、证据上限 | 有界候选集 |
| exact record | 完整合同、public callable、signature、revision/dependencies、provenance 与摘要 | 最终 shortlist |
| reverse dependency index | Operator/TaskGraph 到直接消费者 | 变更影响分析 |

推荐物理布局如下；具体分片键属于发行实现细节，不能进入资产身份：

```text
catalog/
  release.json
  routes/<shard>.jsonl
  summaries/<shard>.jsonl
  records/<prefix>/<asset-id>.json
  reverse-dependencies/<shard>.jsonl
```

每个分片在 release manifest 中保存条目数、字节数和内容摘要。写入先进入新 staging，完成 schema、唯一性、引用闭包和摘要验证后再原子发布整个 snapshot；不得原地修改上一 release。

## 稳定身份与精确记录

`asset_id` 是稳定科学身份，不等同于源码路径、展示名称或某个 release 的 callable。每个 exact record 至少包含：

```text
asset_id, kind, taxonomy, aliases
public_module, public_symbol, signature
inputs[], outputs[]
relation_direction, model, geometry, coordinates, boundary, closure
units, axes, shape, dtype, indexing, normalization
state_lifecycle, failure_behavior, applicability
revision_ref, implementation_digest, dependencies[]
provenance_refs[], evidence_ceiling
```

TaskGraph 记录还包含节点、类型化端口边、分支、状态所有权、反馈/收敛合同和精确依赖。运行参数与本次状态不进入 exact record。缺少不能可靠推导的字段时记录明确的 metadata gap；禁止按名字、文档相似度或函数签名自动补造科学含义。

公共 callable 可以在兼容期增加 alias 或迁移，但 asset ID 不随模块整理而变化。不同模型、几何、边界或失败合同保持不同资产 ID，即使共享实现。相同身份的新工程实现使用新的 revision/digest，不复制第二个身份。

## 渐进检索

检索固定采用正向、可审计的披露顺序：

```text
release + route shard
  -> bounded summaries
  -> exact records and dependency closure
```

路由优先比较目标输出与关系方向，再比较模型、几何、坐标、边界/闭合、状态生命周期、单位、轴序、shape/dtype、适用域和证据上限。关键词、别名、来源与向量检索只用于召回，不能覆盖类型化冲突。

调用方在读取前给出或选择有界的 summary/exact-record 预算，并记录实际 snapshot、分片、接受/拒绝候选和未搜索区域。预算耗尽返回 shortlist 或 `metadata_gap`；只有授权范围和兼容组合均完成检查后才能返回 `asset_unavailable`。

模型上下文只承载本次路由和最终候选。资产总量增长主要增加索引存储和检索成本，不应线性增加单次推理 token。对常用任务可以发布绑定精确 revision 的 TaskGraph，但不能把一次运行参数固化成新的公共资产。

## 构建与增量更新

catalog builder 的输入只能是同一待发行内容锁中的可信合同与 revision，不读取 CodeFusion 数据库、源项目 checkout 或网络。增量构建可重用未变化分片，但最终 snapshot 必须重新验证：

- asset ID、public callable 和 revision 的唯一性；
- 所有依赖和反向依赖的双向一致性；
- TaskGraph 依赖闭包及普通边无环、反馈边显式有界；
- signature 与实际安装 callable 一致；
- 每个分片摘要和 release 根摘要确定；
- 删除、替换和 alias 符合兼容与弃用策略。

catalog 不必进入 `import scirel` 的热路径。运行时按 public callable 直接调用；平台检索层读取对应索引与精确记录。不得建立需要在进程启动时 import 数万模块的全局 registry。

## 当前迁移边界

现有 `provenance/admitted-assets.json` 与 wheel `_admitted_manifest.json` 已提供公共 callable、准入 revision、依赖绑定和内容摘要，但不是完整 catalog。`scirel.asset-document.v1`、验证器和 route/summary/exact/reverse-dependency builder 已由 `catalog/examples/` 的依赖闭合 4 条 pilot 验证；该 pilot 的 coverage 必须保持 `partial: 4/52`。

下一阶段是逐项核对 TaskGraph YAML、科学测试和实现，把剩余 48 条资产迁移为 exact documents；不得批量按名称或源码猜测元数据。完整 52 条闭包稳定后，再测量分片字节、token、查询延迟和增量重建成本，并据此选择生产分片和索引策略。只有小批次及完整批次门禁都成立后才扩展到数万资产。
