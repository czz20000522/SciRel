# SciRel

SciRel 是独立维护的 Python 科学关系库。它将已有科研代码中的科学计算能力拆解、整合为可复用的
算子（Operator）和任务图（TaskGraph），供 Agent 按用户需求选择和组合，并通过胶水代码形成可执行的
自定义程序。科学能力以 Python 包交付，可由 CodeFusion、Codex、Claude Code 或其他 Agent 平台使用。

SciRel 开发项目负责生产和维护这个库；用户的核心交付是确切版本的 `scirel` 包及声明的运行依赖。
skill、来源工件、审核状态、测试、构建工具和平台适配属于项目开发/集成层，不是科学函数的运行依赖。
按版本提供必要使用文档；Agent catalog 是同一科学合同的发现投影。项目、包与多版本工作树的边界见
[开发项目与科学包交付](docs/design/project-and-distribution.md)。

## 查询科学关系

[HTML 科学关系手册与 Agent 查询](docs/searchable-documentation.md)使用同一份正式资产文档，
按学科与求解问题提供目录树、导读、实际运行案例、中文/API 搜索及只读 HTTP/CLI 接口。
每条记录保留自身开发版本与证据边界；新增与变更资产同步遵循[手册维护规范](docs/handbook-authoring.md)。

## 为什么拆解与组装

已有科研项目积累了科学模型、数值实现和验证依据，但其对外接口与执行流程通常围绕原作者的使用场景设计。
新的需求可能需要调用未直接暴露的内部能力、取出中间结果、改变已有能力的组合方式，或连接不同项目中的
计算步骤。直接围绕原项目开发，往往需要阅读和修改源码；让 Agent 从头重写核心科学实现，则会重复造轮子，
并引入需要重新验证的科学代码。

SciRel 把这些能力整理成有明确科学含义、输入输出和适用条件的计算单元，保留来源及验证依据，使其能够
脱离原项目的固定入口被复用。用户需求可以来自单个项目，也可以跨越多个项目；简单需求与复杂需求都遵循
同一方法：分解需求、匹配能力、连接输入输出，再生成和执行满足需求的程序。

## 科学能力与胶水代码如何配合

| 组成 | 职责 |
| --- | --- |
| Operator | 承载有明确科学合同的计算实现，说明模型、输入输出、单位、适用条件和失败行为。 |
| TaskGraph | 将已有科学能力组织为可复用的局部计算流程，保留依赖、顺序和必要的反馈关系。 |
| Agent 与组装 skill | 理解和分解需求，查找适用的算子或任务图，判断它们能否正确连接，并生成本次程序。 |
| 胶水代码 | 组织输入输出适配、参数调用、执行顺序和结果交付，将所选能力串联成可执行程序。 |

已有 TaskGraph 能满足需求时直接复用；没有现成入口但已有能力能够组合时，Agent 可以创建本次任务的
运行实例，无须先把每一种用户需求固化为公共 API。这里的难点是需求分解、科学能力匹配与正确编排，
不以来源项目数量或计算规模判断复用价值。

科学公式、闭合、离散和其他科学计算应由相应科学资产承担，不能藏进胶水代码中重新实现。资产的来源和
验证依据支撑其科学实现；本次程序仍须检查适用条件、单位、端口连接和结果。缺少必要科学能力时应明确
指出缺口并进入能力扩展流程，不能把临时猜写的实现冒充已有能力。

具体合同见[架构与科学资产合同](docs/architecture.md)；从用户需求到可执行结果的方法见
[科学请求工作流](docs/requirements/scientific-request-workflow.md)。

## 开发链路与当前状态

SciRel 拥有从来源预处理、拆解、保存的 L1 产物到库整合、用户应用和 release 的科学领域流程。
D0 在官方只读来源的可编辑副本中整理代码，完成 AOCI/CodeGraph 预处理，固定可分享的版本及上游差异。
D1 忠实抽取冻结 D0 的全部保留功能，保留源码行为对照和新发现的问题记录，不承担科学修正；
Python 入口可封装包内 C/C++/Fortran 等原实现，运行须脱离原源码环境。
`scirel-integration` 统筹 D2 科学判断、比较、去重、修正、组装和开发 wheel；
D3 使用确切版本验证用户任务。正式文档在保留资产代码稳定后生成，阶段入口见 [开发流程](docs/development-process.md)。
CodeFusion、Claude Code、Codex 均是中性 harness；SciRel 拥有科学语义与最终审核/发行绑定。
上传前可合并、替换或撤回草稿，上传时固定逐项初始版本，之后无模型在后台改写队列。
专家查看记录所见版本，领取绑定修改基点，放回保存修改并释放锁，显式提交才完成该项审核。
Agent 可先集成验证开发版；人类在稳定累积增量处拍板，不逐开发提交审批。人工认可和公开发行
分别绑定确切内容；开发进展不改写上游交付或既有待审/可信版本。

SciRel 以 `scirel` wheel 交付科学库；插件、skill 和 catalog 按平台需要单独部署与绑定版本。
CodeFusion 可以预装科学包或通过可选插件接入，但 SciRel 不属于 CodeFusion kernel。
包名与安装方式属于平台实现细节。
普通用户在工作台描述需求并获得计算结果、图表或文件，无需安装包、输入 import 或知道 SciRel 名称。
平台维护者在受控 Python runtime 镜像准备阶段预装经过验证的 wheel；运行任务时直接调用现有能力，
不临时下载或让用户配置依赖。独立源码项目服务于库维护和版本管理，不改变这一用户体验边界。

当前 `0.1.0.dev5` 为开发期候选，而非公开发行。保存的 L1 产物是新 workflow 的重跑输入；
旧的 `provenance/admitted-assets.json` 仅作为历史开发样本和来源证据，不再定义新的准入流程。
当前未发布候选以 `provenance/release-index.dev.json` 为统一入口。冻结、出库、验收和
CodeFusion 联调先选定索引中的确切 `entry_id`，再按该条目的状态、来源绑定、工件摘要与证据引用
核对同一候选；单次 `build/verification/<review-run>/manifest.json` 只绑定该次构建。
新候选不继承旧候选的回执，不能以未冻结的 HEAD、开发版本号或历史 52 项快照代替验收基线。
开发期索引与合同可迭代，在最终正式发布前统一收敛为 `v1`。

这里的开发包“冻结”只固定版本，不表示来源已通过 D1。历史 provisional 输入及其派生开发资产，与
有界源验证通过的 D1 输入必须按已有 provenance 分别解释；`pending_unapproved` 也不表示仅剩人工批准。
可运行 wheel、文档覆盖或 D2 测试不能替代缺少的源实现/数值对照。默认先尽量完成整个来源项目的 D1，
保存可独立接续的项目交付后再进入 D2、D3；阶段可由不同团队隔数周接续，不按单个算子流水调度。
明确约定的局部试点可先整合合格有界批次，但不代表项目完成或日常默认流程；未核验历史包的内部联调
不计作已完成合格入库，详见[开发流程](docs/development-process.md)与[版本边界](docs/design/development-trust-versions.md)。

当前 `provenance/admitted-assets.json` 是旧流程留下的 52 条完整迁移样本，其中包含 41 条 operator
和 11 条 TaskGraph，并保存当时导出的来源、决定标签、版本树、内容摘要和依赖绑定。这些字段只用于
复现和核对早期开发实验；Pleiades 及该账本没有在新生命周期下完成专家审核或正式发布，旧的
`admission`/决定标签不得被解释为当前批准事实，也不是新 workflow 的输入前置条件。

该历史 52 项候选还包含 `scirel._composition` 与 `scirel._validation` 两个 LF SHA-256 绑定的 support modules。
它们只用于已选资产的内部导入闭包，会进入 admitted-only staging 与内容锁；它们不是资产、不会出现在
公共导出，也不会改变 52 条资产计数。构建器只复制账本选中的 callable 和 support modules，并拒绝
未绑定、越界或摘要不符的内部依赖。

旧批次的工程证据与确切摘要保存在 [历史组装记录](provenance/assembly-record.md)。历史样本和隔离增量演示
不定义后续正式主线的资产数量、构建输入或永久门禁；后续内容以接收的 D1 交付、D2 整合和发行选择为准。
历史实现如被保留，须明确复用、来源资格及验证依据；冻结记录与仍被引用的许可/来源证据保持可取得。

## 维护者 API 示例

```python
from scirel.field import compute_poloidal_field_magnitude

result = compute_poloidal_field_magnitude([[3.0]], [[4.0]])
assert result["B"][0, 0] == 5.0
```

组合能力也使用普通函数，例如 `scirel.field.solve_multi_coil_vacuum_field`。
调用不需要 CodeFusion、审核数据库、原始项目路径或网络。输入单位、shape、边界和数值约定仍须遵守
各函数的科学合同；测试通过不扩张模型的适用范围。

## 维护

- `src/scirel/<domain>/`：公共科学函数与组合模块，目录按科学领域组织。
- `src/scirel_workflow/`、`src/scirel_plugin/`、`src/scirel_adapter/`：开发工作流和可选宿主/消费适配；普通科学 wheel 不收集这些包，使用它们须另行准备源码工具环境。
- `_validation.py`：合同相同的共享参数检查；不同默认值语义分别保留。
- `_composition.py`：不修改调用方输入的组合调用；依赖由模块显式绑定，无全局资产目录。
- `tests/`：SciRel 科学函数、组合、准入和发行的维护测试；不重验 D1 冻结，也不要求当前实现与来源源码一致。审核 YAML 仅作历史合同测试证据，不进入运行包。
- `provenance/`：来源关系和审核状态，不参与运行时加载。
- `docs/architecture.md`：Operator、TaskGraph、公共接口、科学身份和目录投影的权威边界。
- `docs/catalog.md`：面向数万 Operator、数千 TaskGraph 的分片目录和渐进检索合同。
- `contracts/` 与 `catalog/examples/`：标准资产/catalog Schema，以及当前开发资产的正式文档集合。
- `docs/development-process.md`：首次/增量整合、验证分层和发行候选流程。
- `docs/design/project-and-distribution.md`：开发项目、用户科学包、历史样本和隔离分支/worktree 的构建边界。
- `docs/requirements/scirel-workflow.md` 与 `docs/design/scirel-workflow.md`：L1 到 release 的领域需求和设计。
- `docs/requirements/scientific-request-workflow.md` 与 `docs/design/scientific-request-workflow.md`：从用户需求到 SciRel 计算结果和审计解释的出库流程。
- `docs/design/l1-inventory.md`：可选 L1 结构探针的边界和历史压测样本。
- `docs/requirements/codefusion-plugin.md` 与 `docs/integration/codefusion-plugin-contract.md`：CodeFusion 中性 Agent 与专家审核插件边界。
- `docs/integration/extraction-skill-bundle-deployment.md`：五个 D1 extraction skills 的确定性 bundle 构建与运行副本部署流程。
- `skills/integration/scirel-integration/`：模型理解保存的 L1、对照当前 SciRel、判定复用/重复/变体/组合并形成专家可审查变更的方法。
- `skills/usage/scirel-solving/`：模型规范化用户科学请求、匹配发布能力、规划执行并给出证据有界解释的方法。

项目文档入口见 [`docs/README.md`](docs/README.md)，贡献与兼容要求见
[`CONTRIBUTING.md`](CONTRIBUTING.md)。

标准化资产文档是 framework-neutral catalog 与 HTML 手册的唯一科学输入。当前 133 条记录包含多个实现版本，先验证结构与依赖，再构建开发文档快照：

```powershell
python scripts/validate_asset_documents.py catalog/examples
python scripts/scirel_docs.py build --output .runtime/docs-snapshot-001
python scripts/scirel_docs.py serve --snapshot .runtime/docs-snapshot-001
```

L1 workflow 的小型 fixture 使用 `tests/fixtures/l1/pleiades-minimal.json`，只验证 candidate、draft、审核和 release artifact 的确定性关联。真实保存目录或 ZIP 使用 SciRel 自己的转换入口生成内容寻址的 UTF-8 bundle；它保留每个文件的路径、原始字节和摘要，随后由 `scirel.import_l1` 映射 Operator/TaskGraph，不代替模型完成真实科学整合：

```powershell
python scripts/build_l1_bundle.py <L1目录或ZIP> <新输出.json> --project-id <project-id>
```

转换器不执行 L1 代码，拒绝路径穿越、符号链接、重复/大小写冲突路径、加密或超界 ZIP，并排除 `__pycache__` 等生成缓存。旧 ZIP 的中文文件名编码不明确时，应从原始 L1 目录重新生成 bundle。结构检查只证明实际文件、直接测试映射和显式依赖闭包；它不声称 AI 标准化或科学正确性已完成。

加载 `scirel-integration` 的模型完成语义比较后，以
`scirel.standardization-submission.dev` 交付逐项候选三件套。下面的确定性入口校验 exact candidate、
当前 Git base、未发布候选池和 skill 摘要，有保留增量时生成 reviewer body 可消费的
`review_pending` workflow；纯复用批次完整记账后生成 `no_changes`，不创建新审核项；它不运行或替代模型：

```powershell
python scripts/submit_standardization.py <candidate.json> <submission.json> <candidate-pool.json> <new-workflow.json>
```

模型可选用 `scripts/build_l1_inventory.py` 为多项目 L1 建立结构索引。历史完整压测快照包含 6 个项目、928 个 Operator 和 487 个 TaskGraph；CodeFusion 压测目录重扫结果为 4 个项目、680 个资产、0 个 gap；2026-09-19 的 `材料/extracted_assets` 归档重扫结果为 8 个项目、920 个 Operator 和 355 个 TaskGraph（1275 个资产、0 个 gap）。三者是不同的历史输入快照，不能混合解读，也不代表当前合格 L1 交付。该索引不是标准输入协议，D2 可先集成到可运行开发包，可信发行仍绑定最终批准。

MCP、Codex、Claude Code、CodeFusion、CLI 与云 batch/service 都是 catalog/wheel 的消费者或薄适配器；
它们不能改变资产身份、单位、端口、适用域或失败语义。详细需求与适配合同见
[`docs/requirements/asset-documentation.md`](docs/requirements/asset-documentation.md) 和
[`docs/design/catalog-and-adapters.md`](docs/design/catalog-and-adapters.md)；CodeFusion 的独立消费边界见
[`docs/integration/codefusion-consumer-contract.md`](docs/integration/codefusion-consumer-contract.md)。

新增资产先比较科学合同与已有能力，再决定复用、变体、新增或替换。不要用重新运行一次导入覆盖
此项目的人工维护代码。提取共享函数前验证假设、默认值、边界和失败行为相同；科学算法的合并须有
独立依据。增量变更要保留旧 API 测试，并验证所有受影响组合函数。

## 本地验证与构建

在隔离 Python 环境中安装已有开发依赖（numpy、scipy、pytest、setuptools）。统一入口会设置源码测试所需
的 `PYTHONPATH`；开发 wheel 可先构建供 D3 验证；可信发行必须来自最终批准的冻结版本，不能直接发布未审核开发树。

```powershell
pwsh ./scripts/check.ps1 -Mode affected -ChangedPath src/scirel/<domain>/<asset>.py
pwsh ./scripts/check.ps1 -Mode focused
pwsh ./scripts/check.ps1 -Mode full
pwsh ./scripts/check.ps1 -Mode release -ReleaseIndex <candidate-index.json> -CandidateEntryId <candidate-entry-id> -ApprovedResults <completed-results.json> -ReviewArtifactsDir <exact-review-artifacts> -ReleaseId <release-id> -OutputRoot build/verification/<new-run>
```

`affected` 根据准入依赖、源码 import 关系和显式测试映射选择改变的 Operator、共享模块及其反向依赖
TaskGraph；不传 `-ChangedPath` 时读取当前 Git 工作区，也可用 `-BaseRef <ref>` 检查提交范围。无法可靠归属的
SciRel 源码或公共基线变更会 fail closed 到全套测试。`focused` 可用 `-TestPath` 手工指定精确测试。
上述库门禁不检查任何源项目的 D1 冻结状态。仓库中维护的 extraction skill/部署工具使用
`python -m pytest skills/extraction/tests skills/extraction/scientific-computation-asset-extraction/tests`
单独验证；历史 admitted-only 构建器测试保存在 `provenance/tests/`，不约束当前库源码。
`release` 要求 exact candidate index、审核宿主导出的 approved results 与 reviewer artifacts，以及不存在的输出目录。
当前首发入口从逐项审核投影准备只含所选科学模块的 wheel 和文档集，验证其依赖闭包、目录与包初始化导出，
在隔离环境运行所选资产的测试与文档示例，最后把实际摘要写入 reviewed release manifest 和 release index；
它不会覆盖或清理已有结果。已有可信基线的增量发行尚缺 exact baseline 文档/支持模块输入，当前准备器会拒绝。
更细的整合和验证规则见
[`docs/development-process.md`](docs/development-process.md)。

现有 admitted-only 构建器仍可逐项核对历史样本的源码摘要，用于复现早期开发 wheel；它不是新流程的
发布授权来源。新 release 必须绑定专家批准的 candidate/draft、实际固化后的资产文档、catalog 和 wheel。
构建失败不能替换上一运行版本；固定归档时间与 Python hash seed 只支持相同输入下的工程复现，不产生科学批准。

图合同测试使用 `tests/_review_bindings.py`；`scripts/check.ps1` 会把 `src` 与 `tests` 的绝对路径仅用于
源码测试，并在 wheel 验收前清空 `PYTHONPATH`。

发行验收另外使用不继承 system site-packages 的 venv，以 `--no-index --no-deps` 安装候选 wheel，不挂源码。
当前脚本通过 `.pth` 暴露开发解释器中 NumPy/SciPy 所在目录，因此证明的是无源码 wheel 执行，不是从
干净离线 wheelhouse 重装全部依赖，也不证明同目录的其他包不可见。正式发行门禁仍需固定依赖 wheelhouse。
安装后的测试不得依赖 editable 安装或把 src 放进 PYTHONPATH。上面的版本号随 pyproject.toml 更新，不是永久发行版本。

当前文档集合是多版本开发记录，不代表一个完整可安装发行包。单版本 catalog 仍须从确切同版本、依赖闭合的所选文档构建；其 `complete` 只指所选内容的文档覆盖，不表示专家批准。合成审核 fixture 的闭环测试不代表真实批准。正式首发前必须让可见发布基线获得
对应的批量/逐项专家批准并补齐 exact documents，同时把开发期 `.dev` workflow 合同统一冻结为 `v1`。

项目尚未声明独立分发许可证，保留来源对应关系；正式分发前需确认输入资产与项目许可证选择。
