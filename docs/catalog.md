# SciRel 规模化目录合同

本文定义 SciRel 从当前 68 条开发资产扩展到数万 Operator、数千 TaskGraph 时的目录边界。catalog 服务发现、依赖分析和发行核对；它是从已选发行内容重建的索引，不拥有准入、科学身份或发布权威。

标准资产字段的权威需求见[标准化资产文档需求](requirements/asset-documentation.md)，catalog builder 与 MCP/CLI/云适配边界见[设计](design/catalog-and-adapters.md)。当前 `catalog/examples/` 是 53/68 的依赖闭合开发 pilot，不代表可信发布目录或完整领域覆盖。

## 设计目标

- 不要求 Python import 全部模块来发现能力。
- 不要求模型、开发者或工具一次加载全量合同。
- canonical record 与运行 wheel 的实现版本保持一致，精确内容由 release manifest 集中绑定。
- 支持按领域增量更新、确定性重建、反向依赖查询和旧 release 恢复。
- 检索失败与“没有能力”分开；缺元数据、预算耗尽和不适用有不同结果。

## 逻辑投影

一个 release 生成以下只读逻辑投影。物理文件可按规模分片，但逻辑字段和摘要规则必须稳定。

| 投影 | 内容 | 典型读取范围 |
| --- | --- | --- |
| release manifest | schema/release、根摘要、数量、分片引用、构建环境 | 每次检索一次 |
| route index | asset ID、kind、领域、输出、关系方向及高区分度 facets | 相关分片 |
| capability summary | 简短用途、结构化关键输入输出及默认值、模型/几何/边界、适用域、限制和证据上限 | 有界候选集 |
| exact record | 完整合同、public callable、signature、implementation version、dependencies 与 provenance | 最终 shortlist |
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

同一 snapshot 的 `release_version` 必须等于其中每条 exact record 的 `version.implementation_version`。版本不一致不是可由 adapter 猜测修复的 metadata gap，而是 catalog 构建失败。wheel 文件摘要、release manifest digest 与 catalog root digest 由消费方作为一个发行绑定整体固定，但不逐项复制到资产文档。

## 稳定身份与精确记录

`asset_id` 是稳定科学身份，不等同于源码路径、展示名称或某个 release 的 callable。每个 exact record 至少包含：

```text
asset_id, kind, taxonomy, aliases
public_module, public_symbol, signature
inputs[], outputs[]
relation_direction, model, geometry, coordinates, boundary, closure
units, axes, shape, dtype, indexing, normalization
state_lifecycle, failure_behavior, applicability
implementation_version, dependencies[]
provenance_refs[], evidence_ceiling
```

TaskGraph 记录还包含节点、类型化端口边、分支、状态所有权、反馈/收敛合同和稳定依赖 asset IDs。运行参数与本次状态不进入 exact record。缺少不能可靠推导的字段时记录明确的 metadata gap；禁止按名字、文档相似度或函数签名自动补造科学含义。

公共 callable 可以在兼容期增加 alias 或迁移，但 asset ID 不随模块整理而变化。不同模型、几何、边界或失败合同保持不同资产 ID，即使共享实现。每个 asset ID 只维护一份当前 canonical record；历史由 Git 和不可变 catalog release 保存，不复制逐次源码快照文档。

## TaskGraph 粒度与关系分类

TaskGraph 的合适粒度由它解决的功能、输入输出合同和独立可验证性决定。拆解时“一个图不超过一个框架图节点、通常至少两个算子”是帮助模型切分的经验，不是允许 catalog 自动合并或删除资产的规则。任务图可以嵌套；一次用户请求的动态图属于运行实例，不能因为可运行就写入公共 catalog。

去重和整合必须记录可审计的关系，而不是只保留一个相似度分数：

- `equivalent`：科学合同等价，可收敛为一个 canonical asset；
- `subsumes`：A 的功能范围包含 B，但 B 仍可能作为可复用子图保留；A 包含 B 不等于可以删除 B；
- `overlaps`：中间节点或局部功能重叠，但整体目标或输入输出不同；
- `variant`：模型、几何、单位、坐标、边界、适用域或失败行为存在科学差异；
- `incompatible`：不能安全连接或替换；
- `undetermined`：证据不足，保持分离并记录待决条件。

部分重叠通常不构成重复；判断重点是整体功能、科学合同和可替换性，而不是源码或节点数量。只有在合同等价证据充分时才允许 canonical 收敛。

## 渐进检索

检索固定采用正向、可审计的披露顺序：

```text
release + route shard
  -> bounded summaries
  -> exact records and dependency closure
```

路由优先比较目标输出与关系方向，再比较模型、几何、坐标、边界/闭合、状态生命周期、单位、轴序、shape/dtype、适用域和证据上限。关键词、别名、来源与向量检索只用于召回，不能覆盖类型化冲突。

调用方在读取前给出或选择有界的 summary/exact-record 预算，并记录实际 snapshot、分片、接受/拒绝候选和未搜索区域。预算耗尽返回 shortlist 或 `metadata_gap`；只有授权范围和兼容组合均完成检查后才能返回 `asset_unavailable`。

模型上下文只承载本次路由和最终候选。资产总量增长主要增加索引存储和检索成本，不应线性增加单次推理 token。对常用任务可以发布绑定稳定依赖身份的 TaskGraph，但不能把一次运行参数固化成新的公共资产。

## 构建与增量更新

catalog builder 的输入只能是同一待发行版本中的可信 canonical contracts，不读取 CodeFusion 数据库、源项目 checkout 或网络。增量构建可重用未变化分片，但最终 snapshot 必须重新验证：

- asset ID 与 public callable 的唯一性；
- 所有依赖和反向依赖的双向一致性；
- TaskGraph 依赖闭包及普通边无环、反馈边显式有界；
- signature 与实际安装 callable 一致；
- 每个分片摘要和 release 根摘要确定；
- 删除、替换和 alias 符合兼容与弃用策略。

catalog 不必进入 `import scirel` 的热路径。运行时按 public callable 直接调用；平台检索层读取对应索引与精确记录。不得建立需要在进程启动时 import 数万模块的全局 registry。

## 当前迁移边界

现有 `provenance/admitted-assets.json` 与 wheel `_admitted_manifest.json` 已提供 52 条历史开发样本的 callable、来源 revision、依赖绑定和内容摘要，但不是完整 catalog。`scirel.asset-document.v1`、验证器和 route/summary/exact/reverse-dependency builder 已由 `catalog/examples/` 的依赖闭合 53 条开发 pilot 验证；该 pilot 的 coverage 必须保持 `partial: 53/68`。第一阶段当前合格交付根暂为空；保存的历史开发样本不能据此获 SciRel 专家认可。

下一阶段是逐项核对 TaskGraph YAML、科学测试和实现，把剩余 18 条资产补齐为 exact documents；不得批量按名称或源码猜测元数据。完整 68 条闭包稳定后，再测量分片字节、token、查询延迟和增量重建成本，并据此选择生产分片和索引策略。只有小批次及完整批次门禁都成立后才扩展到数万资产。
