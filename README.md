# SciRel

SciRel 是一个面向聚变与等离子体物理的 Python 科学零件库。

它的特点是：**每一个公开函数都附带一份机器可读的"合同"**，写清楚这个函数用的是什么物理模型、
输入输出的单位是什么、在什么范围内可信、出错时会怎样、以及凭什么是正确的。
它不做"从输入文件跑到输出结果"的大程序，而是提供可以单独拿出来用的标准零件，由使用者自己组装。

完整叙事（为什么这样设计、三层角色、真值链、三层角色分工）：[`docs/maintainer/why-and-how.md`](docs/maintainer/why-and-how.md)。

## 为什么要做这个

做聚变或等离子体研究的人大多见过这几种情况：同一个公式被反复重写、彼此略有不同；一个很好用的
截面拟合藏在某个大程序的深处，想单独用就得带上半个程序；程序允许接收的数值范围被误当成有物理证据
支撑的范围；输入越界时悄悄截断，然后给一个"看起来正常"的数字。

同时，越来越多的计算工作交给 AI agent 来做，而 agent 的会话记忆不可靠、会漏掉隐含的异常信号、
部署环境未必有源码。所以**重要的限制和失败不能只藏在某个人的经验里，必须能从交付物中查到**。

SciRel 的回答是：把散落在各个程序里的聚变物理关系，整理成一套可复用、有边界、有证据、
人和 agent 都能放心用的标准零件。

## 六条核心思想

1. **每个函数一份合同。** 合同是结构化记录，不是注释：模型、单位、形状、适用与排除范围、
   失败方式、证据与已知局限。
2. **物理正确靠独立证据。** 代码之所以是对的，只因为文献、被拆解项目的实际行为、解析恒等式、
   守恒量支持它——不是因为它通过了测试，也不是因为和另一份实现一致。
3. **按物理分层，依赖单向。** 楼上的层可以调楼下的，楼下不能往上借。能力增长是在层内加领域与模型族，
   不是加层。
4. **同一族模型合成一个函数，用 `method=` 选算法。** 判据只有一句：调用的人只改 `method`、
   别的参数一个都不动，拿到的是不是同一个物理量。
5. **为 agent 设计接口。** 报错自带下一步（选错名字列出全部合法名字）、越界不静默、索引由权威内容生成。
6. **物理正确优先于忠于原代码，但要拿证据。** 从来源拆出来的东西，发现物理有错就改，
   前提是能拿出文献、推导或独立对照；而且判定「来源错了」之前要先排除它是有意的近似。

## 凭什么可信：证据，不是测试绿灯

这里有一条**真值链：证据 → 代码 → 合同 → 文档**。三条箭头各有各的失败模式：

| 现象 | 结论 |
| --- | --- |
| 合同与代码不符 | **合同错了**，按代码实际行为改写合同。这不证明代码对 |
| 代码与证据不符 | **代码错了**，开工单、按安全默认处理，等人工裁决。不得把错误行为写进合同让它变成"已声明" |
| 证据拿不到 | 如实记"无法建立"，写清卡点。测试钉住当前行为**不等于**证据 |

这套做法有外部出处，不是我们自创的标准：OpenFOAM 社区用 exact solution / manufactured solution
验证求解器——造一个已知精确解，让求解器把它解回来，判据是"能不能对上那个精确解"。
我们的闭式解、精确有理重算、守恒恒等式、高位 mpmath 对照是同一套思想。
对照见 [`docs/maintainer/reference-projects.md`](docs/maintainer/reference-projects.md)。

由此还引出一条记账规矩：**报告测试规模时必须把"证据测试"和"行为回归"分开说**。
前者证伪"物理算错了"，后者证伪"改动破坏了别处"，两者都要有，混成一个数字既吓人又没有信息量。

## 能力从哪来：三条线

供给者提取候选，合并者把候选并入库，消费者用分发包解决问题。

- **拆解线**把别人的实现变成我们的能力：拆解者手上永远有一份冻结版合同，可以先比对、再取补集。
- **合并线**只消费"拆解包"，只判题、不重写：交来的必须已是最终形态，且通过与合并线完全相同的检查。
- **出库线**通过"缺口信号"影响拆解方向，不直接派任务。

三层角色各自的入口 skill 见 [`skills/README.md`](skills/README.md)；操作细节见
[`docs/maintainer/supply-pipeline.md`](docs/maintainer/supply-pipeline.md)。

## 刻意不做的事

SciRel 提供科学零件，也提供有合同、有直接测试的**可复用组合零件**（例如多线圈加权叠加）。
但具体研究任务的总体流程仍由用户程序负责：采用哪些假设、怎样准备装置数据、如何安排整个模拟、
输出什么报告。**SciRel 不要求用户改用另一套配置语言或全局运行框架。**

边界是：库负责标准元件与标准组件，用户负责把它们装成自己的研究程序。不能因为几个元件各自正确，
就省掉它们组合之后的单位、坐标、适用假设和失败路径检查。

## 参照项目

**结构参照 scipy，流程参照 OpenFOAM。** 两者是参照，不是依赖，也不是要模仿的完成度：

- scipy 管"这个库长什么样"：分层、模块粒度、公开面组织、`method=` / `kind=` / `bc_type=` 这类
  选择参数的用法。
- OpenFOAM 管"能力怎么被造出来、怎么被验收"：同族共用接口、报错列合法值、准入与验收、
  演示案例与验证案例分开、案例即回归、制造解验证。

与我们**最大的真实差距不在模块数量，而在索引结构**：scipy 的公开面是"少模块、多名字"，
用户靠命名空间层级和名字就能缩小范围；我们是"多模块、少名字"，用户要靠合同检索，
而检索目前只能按词面 AND 命中。这一条与"族的划分"是同一个问题的两面，
记录在 [`docs/maintainer/reference-projects.md`](docs/maintainer/reference-projects.md)，
不改代码。

## 安装与最小示例

尚未发布到 PyPI，从源码安装（需要 Python 3.12 或更高版本）：

```bash
pip install .            # NumPy + SciPy + mpmath
```

```python
from scirel.field import compute_poloidal_field_magnitude

result = compute_poloidal_field_magnitude([[3.0]], [[4.0]])
assert result["B"][0, 0] == 5.0
```

公共 API 按科学领域放在 `scirel.<domain>` 下。调用不需要来源 checkout、数据库或网络；
绘图与文件格式适配器不在库的运行依赖里。

## 文档

手册分两层：**用户指南**是手写教程，从科学问题出发讲模型、代码、实际输出与解释；
**API 参考**从正式合同生成，逐函数给出签名、参数、返回值、失败行为、适用范围与示例。
没有手写教程的章节保持空白，不会用合同摘要填充。

```bash
pip install . --group docs
python scripts/validate_asset_documents.py catalog/examples
python scripts/scirel_docs.py build --output .runtime/docs-snapshot
python scripts/scirel_docs.py serve --snapshot .runtime/docs-snapshot
```

维护者文档（不在文档站内）：

| 文件 | 内容 |
| --- | --- |
| [`codebase-map.md`](docs/maintainer/codebase-map.md) | 当前代码地图 |
| [`why-and-how.md`](docs/maintainer/why-and-how.md) | 完整叙事：我们做什么、为什么、怎么做 |
| [`audiences.md`](docs/maintainer/audiences.md) | 对物理专家 / 软件开发者怎么讲、常见问题、30–45 分钟讲解顺序 |
| [`supply-pipeline.md`](docs/maintainer/supply-pipeline.md) | 供给线流程、分级评审与工单格式 |
| [`reference-projects.md`](docs/maintainer/reference-projects.md) | scipy / OpenFOAM 各自参照什么、不参照什么 |
| [`module-granularity.md`](docs/maintainer/module-granularity.md) | 模块粒度的显式决策与"一族一模块"规则 |
| [`family-rule-audit.md`](docs/maintainer/family-rule-audit.md) | 族规则执行情况的一次性审计 |
| [`durable-vs-status.md`](docs/maintainer/durable-vs-status.md) | 什么该留在总纲、什么该进仓库，以及怎么防止漂移 |
| [`status.md`](docs/maintainer/status.md) | **会随版本变**的状态快照：规模、进度、证据覆盖 |
| [`closeout-ledger.md`](docs/maintainer/closeout-ledger.md) | **结项对账**：`main` 上成立什么、还差什么，每行带命令 |
| [`capability-boundaries.md`](docs/maintainer/capability-boundaries.md) | **包里没有的东西**：缺口的失败方式与证据 |

## 仓库结构

目录逐项说明见 [`docs/maintainer/codebase-map.md`](docs/maintainer/codebase-map.md)。本文件随 wheel 分发，
因此不列举不随包分发的目录——那样在只装了 wheel 的机器上会指向不存在的位置。

## 开发与验收

一个功能 = 实现 + 直接测试 + 正式合同（以及由合同生成的中英双语文档）。
测试以数值对照为准，修改实现必须保持既有断言与容差。

开发环境由宿主机上的 uv 管理：解释器版本由 `.python-version` 固定，依赖由 `uv.lock` 固定。
宿主机只需要 Git、Python 3 启动器和 uv。

```bash
python3 scripts/dev.py prepare  # Windows: py -3
python3 scripts/dev.py check --stage dev   # 开发档：普通批次默认用这一档
python3 scripts/dev.py check               # 发布档：只在下面三种场合跑
```

**门禁按改动落在哪个面上选，不是按批次数量选，也不是"跑得越重越保险"。**

- **开发档是合并门槛的默认。** 它持共享锁、不挡别人，证明"这批改动没破坏别处"。
- **发布档只在这三种场合跑：**
  1. 改动落在**只有发布档能验证**的面上：文档站构建、wheel 构建与暴露、示例执行；
  2. 对外交付声明；
  3. 结项。
- 每条回执写明**用的是哪一档**、**为什么这一档够**。发布档持独占锁，无必要地跑它会挡住同一 clone 里
  所有并发检查。开发档回执**不得**当作发布证据引用。

venv、uv 缓存和临时文件都放在项目内已被忽略的 `.runtime/` 下，不写到项目目录之外。

**案例即回归。** 仓库里的验收固件是可执行资产，不是文档：`c5-delivery-acceptance` 记录 sha256 与复跑命令，
复跑即验证；`c4-usage-acceptance` 是消费者路径的验收；演示类案例（`negative-demo-*`）是给人看的，验收标准
不同。这三类的分离参照 OpenFOAM 的 `tutorials` / `test` 分工，其中"演示与验收案例分开维护"仍是待改进项。
这些固件不随 wheel 分发，路径见 `docs/maintainer/codebase-map.md`。

接手请先读 [`AGENTS.md`](AGENTS.md)。三条线边界与检索策略见 [`ARCHITECTURE.md`](ARCHITECTURE.md)，
项目规则见 [`RULES.md`](RULES.md)，完整贡献流程见 [`CONTRIBUTING.md`](CONTRIBUTING.md)。

## 现在到哪了

本文件不记进度与规模——它们会漂。看这三处：

- 状态快照（规模、各域分布、证据覆盖、结构进度）：[`docs/maintainer/status.md`](docs/maintainer/status.md)
- 待办与整理计划：见仓库中的整理计划文件（不随 wheel 分发，路径见 `docs/maintainer/codebase-map.md`）
- 等人工裁决的问题：`tickets/` 下 `status: open` 的工单

**能力边界冻结中：** 暂停接收新资产，供给线的准入随之中止，先还债、先清理。解除条件由维护者另行决定。

## English

SciRel is a self-contained Python library for fusion and plasma physics. It packages reusable scientific
functions behind plain Python callables, with NumPy, SciPy and mpmath as core dependencies; plotting and
file-format adapters are not part of the runtime dependency set. Every public function carries a formal
asset contract defining its model, inputs/outputs, units, applicability, failure behavior and evidence.

The bilingual manual is generated from those contracts. Libraries carry a truth chain —
**evidence → code → contract → docs** — and the three arrows fail differently: a contract that disagrees
with the code is a wrong contract (not proof the code is right); code that disagrees with the evidence is
wrong code and needs a ticket, not a contract rewrite; and missing evidence is recorded as such rather
than assumed. Tests are reported in two separate classes: evidence tests (closed-form solutions,
exact rational recomputation, conservation identities, high-precision references) and behavior regressions.

The project is pre-release and does not publish wheels yet.
