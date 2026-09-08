# SciRel

SciRel 是独立维护的 Python 科学关系库。CodeFusion 负责来源整理、验证、审核和资产入库；
SciRel 负责公共函数、科学模块、共享实现、兼容性、测试和 wheel 发行。

SciRel 是 CodeFusion 平台内置的科学能力，包名与安装方式属于平台实现细节。
普通用户在工作台描述需求并获得计算结果、图表或文件，无需安装包、输入 import 或知道 SciRel 名称。
平台维护者在受控 Python runtime 镜像准备阶段预装经过验证的 wheel；运行任务时直接调用现有能力，
不临时下载或让用户配置依赖。独立源码项目服务于库维护和版本管理，不改变这一用户体验边界。

当前为 `0.1.0.dev1` 开发迁移，包含 Pleiades 的 40 个算子函数和 10 个组合函数。
`provenance/pleiades-import.json` 记录输入来源与迁移对应关系，**不代表资产已经正式入库或发布**。
入库连接和科学审查仍在推进；该开发包不应标成已批准发行。

开发中的 `update_anisotropic_picard_flux` 已将面积积分边界收紧为均匀、非零间距的张量网格
（相邻间距相对容差 1e-10，可递增或递减），并要求掩码是同形布尔数组。非均匀、局部重复
坐标及隐式广播掩码会明确失败。这是需要新候选复审的科学行为修正，尚未写入正式准入版本。

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

在隔离 Python 环境中安装已有开发依赖（numpy、scipy、pytest、setuptools）。

```text
python -m pip wheel . --no-deps --no-build-isolation --wheel-dir dist
python -m pip install --no-deps --force-reinstall dist/scirel-0.1.0.dev1-py3-none-any.whl
python -m pytest tests
```

图合同测试使用 `tests/_review_bindings.py`；运行前将 `tests` 的绝对路径加入 PYTHONPATH
（PowerShell：`$env:PYTHONPATH = (Resolve-Path tests).Path`）。wheel 验证不要把 `src` 加入该路径。

发行验收另外使用断网环境，只安装 wheel 与声明依赖，不挂源码。安装后的测试不得依赖 editable
安装或把 src 放进 PYTHONPATH。上面的版本号随 pyproject.toml 更新，不是永久发行版本。

项目尚未声明独立分发许可证，保留来源对应关系；正式分发前需确认输入资产与项目许可证选择。
