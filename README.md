# SciRel

SciRel 是独立维护的 Python 科学关系库，并拥有从保存的 L1 产物到 release 的科学领域流程。
`scirel-integration` skill 指导模型理解 L1，并同时对照冻结基线和当前未发布候选池，在基线之外形成专家可审查的
候选文档、候选代码和候选测试；尚未被专家打开的排队候选可以先合并、替换或撤回，项目代码只实现
稳定的确定性门禁、审核状态、catalog/wheel 构建和 release 绑定。CodeFusion 与 Claude Code、
Codex 一样是中性 Agent harness，也可提供 artifact、身份和审核 UI；它不拥有 SciRel 的科学语义。
候选入队后 Agent run 即可结束；专家首次打开完整候选时才冻结三件套。专家批准只使候选有资格进入独立固化任务，固化任务还必须对照
最新 SciRel 基线处理堆积候选之间的冲突，成功后才可更新维护基线并进入 release。

SciRel 以独立插件和发布 wheel 交付；CodeFusion 可以预装或加载它，但 SciRel 不属于 CodeFusion kernel。
包名与安装方式属于平台实现细节。
普通用户在工作台描述需求并获得计算结果、图表或文件，无需安装包、输入 import 或知道 SciRel 名称。
平台维护者在受控 Python runtime 镜像准备阶段预装经过验证的 wheel；运行任务时直接调用现有能力，
不临时下载或让用户配置依赖。独立源码项目服务于库维护和版本管理，不改变这一用户体验边界。

当前 `0.1.0.dev5` 为开发期候选，而非公开发行。保存的 L1 产物是新 workflow 的重跑输入；
旧的 `provenance/admitted-assets.json` 仅作为历史开发样本和来源证据，不再定义新的准入流程。

当前 `provenance/admitted-assets.json` 是旧流程留下的 52 条完整迁移样本，其中包含 41 条 operator
和 11 条 TaskGraph，并保存当时导出的来源、决定标签、版本树、内容摘要和依赖绑定。这些字段只用于
复现和核对早期开发实验；Pleiades 及该账本没有在新生命周期下完成专家审核或正式发布，旧的
`admission`/决定标签不得被解释为当前批准事实，也不是新 workflow 的输入前置条件。

候选还包含 `scirel._composition` 与 `scirel._validation` 两个 LF SHA-256 绑定的 support modules。
它们只用于已选资产的内部导入闭包，会进入 admitted-only staging 与内容锁；它们不是资产、不会出现在
公共导出，也不会改变 52 条资产计数。构建器只复制账本选中的 callable 和 support modules，并拒绝
未绑定、越界或摘要不符的内部依赖。

旧批次的工程证据记录在 `provenance/assembly-record.md`。其 52 条开发候选 wheel 的 SHA-256 为
`9f2b37e34a23f4252b6cae3915a4c2444c1a4a08a32e163e83db24d068d3914f`，内置 manifest digest 为
`sha256:81a66405b369e179d38d1b71926e6101b264268b3cd2b41aab7adf14f4763cb9`，已执行证据为 337 项通过。
另有 52 到 53 条的隔离增量演示，用于验证增量输入不会改写 52 条开发样本；它不是该样本的
第 53 个资产，也不构成专家批准或公开发布。

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
- `_validation.py`：合同相同的共享参数检查；不同默认值语义分别保留。
- `_composition.py`：不修改调用方输入的组合调用；依赖由模块显式绑定，无全局资产目录。
- `tests/`：迁移保留的科学回归与新增库工程测试。审核 YAML 仅作历史合同测试证据，不进入运行包。
- `provenance/`：来源关系和审核状态，不参与运行时加载。
- `docs/architecture.md`：Operator、TaskGraph、公共接口、科学身份和目录投影的权威边界。
- `docs/catalog.md`：面向数万 Operator、数千 TaskGraph 的分片目录和渐进检索合同。
- `contracts/` 与 `catalog/examples/`：标准资产/catalog Schema，以及依赖闭合的 59/106 开发 pilot。
- `docs/development-process.md`：首次/增量整合、验证分层和发行候选流程。
- `docs/requirements/scirel-workflow.md` 与 `docs/design/scirel-workflow.md`：L1 到 release 的领域需求和设计。
- `docs/requirements/scientific-request-workflow.md` 与 `docs/design/scientific-request-workflow.md`：从用户需求到 SciRel 计算结果和审计解释的出库流程。
- `docs/design/l1-inventory.md`：可选 L1 结构探针的边界和当前压测结果。
- `docs/requirements/codefusion-plugin.md` 与 `docs/integration/codefusion-plugin-contract.md`：CodeFusion 中性 Agent 与专家审核插件边界。
- `skills/integration/scirel-integration/`：模型理解保存的 L1、对照当前 SciRel、判定复用/重复/变体/组合并形成专家可审查变更的方法。
- `skills/usage/scirel-solving/`：模型规范化用户科学请求、匹配发布能力、规划执行并给出证据有界解释的方法。

项目文档入口见 [`docs/README.md`](docs/README.md)，贡献与兼容要求见
[`CONTRIBUTING.md`](CONTRIBUTING.md)。

标准化资产文档是 framework-neutral catalog 的唯一科学输入。当前 pilot 可执行验证与构建：

```powershell
python scripts/validate_asset_documents.py catalog/examples --check-runtime --execute-examples
python scripts/build_catalog.py catalog/examples --output-dir build/catalog/<new-run> --catalog-id scirel-development-pilot --release-version 0.1.0.dev5 --coverage-status partial --declared-total 106
```

L1 workflow 的本地 fixture 使用 `tests/fixtures/l1/pleiades-minimal.json`，不读取源项目 checkout、数据库或网络；它只验证 candidate、draft、审核和 release artifact 的确定性关联，不代替模型完成真实科学整合。

模型可选用 `scripts/build_l1_inventory.py` 为多项目 L1 建立结构索引。历史完整压测快照包含 6 个项目、928 个 Operator 和 487 个 TaskGraph；CodeFusion 压测目录重扫结果为 4 个项目、680 个资产、0 个 gap；当前 `材料/extracted_assets` 归档重扫结果为 8 个项目、920 个 Operator 和 355 个 TaskGraph（1275 个资产、0 个 gap）。三者是不同的输入快照，不能混合解读。该索引不是标准输入协议，只有后续标准化和专家审核通过的变更才会进入公共 SciRel 资产。

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
的 `PYTHONPATH`；正式候选 wheel 必须由专家批准后固化的 SciRel 基线生成，不能把未审核候选或整个开发树直接发布。

```powershell
pwsh ./scripts/check.ps1 -Mode affected -ChangedPath src/scirel/<domain>/<asset>.py
pwsh ./scripts/check.ps1 -Mode focused
pwsh ./scripts/check.ps1 -Mode full
pwsh ./scripts/check.ps1 -Mode release -WorkflowSnapshot <approved-workflow.json> -ReleaseId <release-id> -OutputRoot build/verification/<new-run>
```

`affected` 根据准入依赖、源码 import 关系和显式测试映射选择改变的 Operator、共享模块及其反向依赖
TaskGraph；不传 `-ChangedPath` 时读取当前 Git 工作区，也可用 `-BaseRef <ref>` 检查提交范围。无法可靠归属的
SciRel 源码或公共基线变更会 fail closed 到全套测试。`focused` 可用 `-TestPath` 手工指定精确测试。
`release` 要求一个已获专家批准的 workflow 快照和不存在的输出目录。它从当前维护基线构建普通 wheel，
验证 exact documents，生成 catalog，在隔离环境运行已安装 wheel 的科学合同与用户验收，最后把实际摘要
写入 release manifest 和 released workflow 快照；它不会覆盖或清理已有结果。更细的整合和验证规则见
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

当前 catalog 仍是 `partial: 59/106` 开发 pilot，因此这条 release 链证明的是已批准资产、catalog 与普通 wheel
可以被精确绑定，不代表一个候选的批准自动批准 wheel 中其余维护代码。正式首发前必须让可见发布基线获得
对应的批量/逐项专家批准并补齐 exact documents，同时把开发期 `.dev` workflow 合同统一冻结为 `v1`。

项目尚未声明独立分发许可证，保留来源对应关系；正式分发前需确认输入资产与项目许可证选择。
