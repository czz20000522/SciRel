# SciRel

SciRel 是独立维护的 Python 科学关系库。CodeFusion 负责来源整理、验证、审核和资产入库；
SciRel 负责公共函数、科学模块、共享实现、兼容性、测试和 wheel 发行。

SciRel 是 CodeFusion 平台内置的科学能力，包名与安装方式属于平台实现细节。
普通用户在工作台描述需求并获得计算结果、图表或文件，无需安装包、输入 import 或知道 SciRel 名称。
平台维护者在受控 Python runtime 镜像准备阶段预装经过验证的 wheel；运行任务时直接调用现有能力，
不临时下载或让用户配置依赖。独立源码项目服务于库维护和版本管理，不改变这一用户体验边界。

当前 `0.1.0.dev5` 为完整准入待发行候选，而非公开发行。
`provenance/admitted-assets.json` 绑定 CodeFusion ScientificAssetLibraryOwner 的精确准入导出：
52 条资产，其中 41 条 operator 和 11 条 TaskGraph。每一条都保留独立的 admission、最终人工决定、
版本树、内容摘要和 TaskGraph 依赖绑定；该账本是这些逐项治理事实的唯一来源，不能由本 README
或组装记录替代。

候选还包含 `scirel._composition` 与 `scirel._validation` 两个 LF SHA-256 绑定的 support modules。
它们只用于已选资产的内部导入闭包，会进入 admitted-only staging 与内容锁；它们不是资产、不会出现在
公共导出，也不会改变 52 条资产计数。构建器只复制账本选中的 callable 和 support modules，并拒绝
未绑定、越界或摘要不符的内部依赖。

本批次的单一工程证据记录在 `provenance/assembly-record.md`。正式 52 条候选 wheel 的 SHA-256 为
`9f2b37e34a23f4252b6cae3915a4c2444c1a4a08a32e163e83db24d068d3914f`，内置 manifest digest 为
`sha256:81a66405b369e179d38d1b71926e6101b264268b3cd2b41aab7adf14f4763cb9`，已执行证据为 337 项通过。
另有 52 到 53 条的隔离增量演示，用于验证增量输入不会改写最终 52 条主候选；它不是该主候选的
第 53 个资产，也不构成公开发布。

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

新增资产先比较科学合同与已有能力，再决定复用、变体、新增或替换。不要用重新运行一次导入覆盖
此项目的人工维护代码。提取共享函数前验证假设、默认值、边界和失败行为相同；科学算法的合并须有
独立依据。增量变更要保留旧 API 测试，并验证所有受影响组合函数。

## 本地验证与构建

在隔离 Python 环境中安装已有开发依赖（numpy、scipy、pytest、setuptools）。开发测试可以直接针对
源码树运行；平台候选 wheel 必须先由准入记录生成独立 staging，不能直接打包整个开发树。

```text
python -m pytest tests/test_admitted_distribution_builder.py tests/test_admitted_integrations.py
python scripts/build_admitted_distribution.py --staging-dir <new-staging-directory> --wheel-dir <new-wheel-directory>
```

构建器逐项核对 `provenance/admitted-assets.json` 中的源码摘要，拒绝未绑定的内部模块依赖，生成只含
已准入 callable 的公共导出、内置准入清单与文件内容锁。它拒绝覆盖已有 staging 目录；失败结果不能
替换上一运行版本。wheel 构建固定归档时间与 Python hash seed，同一源码和准入账本应产生相同摘要。

图合同测试使用 `tests/_review_bindings.py`；运行前将 `tests` 的绝对路径加入 PYTHONPATH
（PowerShell：`$env:PYTHONPATH = (Resolve-Path tests).Path`）。wheel 验证不要把 `src` 加入该路径。

发行验收另外使用断网环境，只安装 wheel 与声明依赖，不挂源码。安装后的测试不得依赖 editable
安装或把 src 放进 PYTHONPATH。上面的版本号随 pyproject.toml 更新，不是永久发行版本。

项目尚未声明独立分发许可证，保留来源对应关系；正式分发前需确认输入资产与项目许可证选择。
