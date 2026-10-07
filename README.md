# SciRel

SciRel 是独立维护的 Python 科学关系库。它将已有科研代码中的科学计算能力拆解、整合为可复用的
算子（Operator）和任务图（TaskGraph），供 Agent 按用户需求选择和组合，并通过胶水代码形成可执行的
自定义程序。科学能力以 Python 包交付，可由 CodeFusion、Codex、Claude Code 或其他 Agent 平台使用。

SciRel 开发项目负责生产和维护这个库；用户的核心交付是确切版本的 `scirel` 包及声明的运行依赖。
skill、来源工件、审核状态、测试、构建工具和平台适配属于项目开发/集成层，不是科学函数的运行依赖。
按版本提供必要使用文档；Agent catalog 是同一科学合同的发现投影。项目、包与多版本工作树的边界见
[开发项目与科学包交付](docs/design/project-and-distribution.md)。

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

## 开发主线与当前状态

主线只维护科学包骨架、拆解/整合/应用方法，以及必要的合同、验证和构建工具。
当前包版本为 `0.2.0.dev0`，没有科学 callable、获批资产或公开发行；运行依赖为空。
`catalog/assets/` 尚无 exact documents，`provenance/mainline-release-index.dev.json` 是这条新主线的空索引。
后续科学实现来自 D1 项目交付，经 D2 比较、去重、科学判断和整合进入库；D3 使用确切安装包验证任务。
历史科学实现及其回归、132 项 pilot、旧来源/审核/联调记录已从本基线迁出，完整保存在
[历史开发测试线](docs/history.md)。历史线可继续实验，但不作为主线的默认构建输入或测试门禁。

开发分支允许先修改代码、运行相关验证和构建开发 wheel；代码稳定后维护唯一资产文档并形成待审版本。
专家认可与正式发行分别绑定确切内容，开发成功不能产生批准。默认按来源项目交付 D1，阶段可由新 owner
异步接续；局部试点须明确范围，不能当作项目完成。见 [开发流程](docs/development-process.md)。

用户核心交付为 `scirel` wheel 及声明运行依赖，必要使用文档绑定同一版本。
平台可另外部署 skill、catalog 与适配工具；这些属于项目开发/集成层，不打入科学 wheel。
普通用户由平台取得计算结果，维护者或直接 Python 调用方可以安装包；当前空骨架不提供科学计算示例。

## 目录与工作路线

- `src/scirel/`：当前为空科学包骨架，未来按科学领域维护 Operator、TaskGraph 和必要运行实现。
- `src/scirel_workflow/`、`src/scirel_plugin/`、`src/scirel_adapter/`：通用开发/审核/消费工具，不进入科学 wheel。
- `skills/`、`docs/`、`contracts/`、`scripts/`：方法、设计、合同和项目工具。
- `tests/`：当前包骨架与通用工具测试；`tests/fixtures/` 是明确标注的合成夹具，不是科学资产或批准记录。
- `catalog/assets/`：后续实际整合资产的唯一 exact documents；测试夹具不进入这里。
- `provenance/mainline-release-index.dev.json`：新主线的版本与候选入口，不继承历史候选或回执。

主线、D2 整合、发行候选和旧版本维护使用隔离分支/worktree、环境及新输出目录。
分支名不定义科学批准；每次构建固定确切提交、依赖/工具链和实际 wheel 摘要。
详细规则见 [开发项目与科学包交付](docs/design/project-and-distribution.md)，文档入口见
[项目文档](docs/README.md)，贡献要求见 [贡献指南](CONTRIBUTING.md)。

## 本地验证与构建

在本工作树的独立 Python 环境安装开发依赖，依赖下载使用开发机本地代理。

```powershell
python -m pip install -e ".[test]"
pwsh ./scripts/check.ps1 -Mode affected
pwsh ./scripts/check.ps1 -Mode full
```

没有 `pwsh` 时，先执行相同的影响选择器，再按其返回范围运行 Python 测试；不能自行缩小影响闭包：

```text
python scripts/select_affected_tests.py --format json --changed-path pyproject.toml
python -m pytest tests
```

当前完整主线测试只覆盖骨架与通用工具。需要 PowerShell 的平台工具测试在缺少 `pwsh` 时明确跳过，
不算已执行；extract skills 的工具检查先安装 `.[test,extraction-test]`，再运行 `python -m pytest skills/extraction/tests
skills/extraction/scientific-computation-asset-extraction/tests`。历史科学回归在历史分支运行，不能把它们的
通过/失败统计当作本基线的科学验收。后续科学源码引入时按其实际合同补回相关测试和运行依赖。

普通 wheel 只收集 `scirel` 和其子包；当前只能构建开发骨架包，不能称为科学库已交付。
开发 workflow/plugin/adapter 通过 checkout 的脚本/测试入口或显式 `PYTHONPATH=src` 使用。
正式发行另选择获批内容与依赖闭包，从冻结提交准备独立源码树，构建 wheel，再在没有源码的环境验证。
现有发布工具仍为开发期协议；真实宿主认证、许可与公开发行授权须按流程核实。

未来 `catalog/assets/` 有实际资产后，使用 `scripts/validate_asset_documents.py` 校验 exact documents，
并用 `scripts/build_catalog.py` 从明确所选文档构建发行投影；空目录不能被宣称为已发布 catalog。
