# SciRel

SciRel 是一个自包含的 Python 科学计算库：把聚变、等离子体与相关数值方法整理为可复用的科学函数，以标准 Python 包交付。
库本身只依赖代码、测试与正式资产合同；来源项目、拆解过程与历史工作记录不属于本仓库。

## 安装与使用

尚未发布到 PyPI，目前从源码安装（需要 Python 3.12 或更高版本）：

```bash
pip install .            # NumPy + SciPy + mpmath
```

```python
from scirel.field import compute_poloidal_field_magnitude

result = compute_poloidal_field_magnitude([[3.0]], [[4.0]])
assert result["B"][0, 0] == 5.0
```

公共 API 按科学领域放在 `scirel.<domain>` 下；每个函数都在正式资产合同中声明模型、输入输出、
单位、轴序、适用条件与失败行为。调用不需要来源 checkout、数据库或网络。

## 文档

手册分为两层：用户指南是手写教程，从科学问题出发讲模型、代码、实际输出与解释；API 参考从正式资产合同生成，逐函数给出签名、参数、返回值、失败行为、适用范围与示例。没有手写教程的章节保持空白，不会用合同摘要填充。

```bash
pip install . --group docs
python scripts/validate_asset_documents.py catalog/examples
python scripts/scirel_docs.py build --output .runtime/docs-snapshot
python scripts/scirel_docs.py serve --snapshot .runtime/docs-snapshot
```

## 仓库结构

```
src/scirel/            # 科学实现，按领域组织
tests/                 # 功能测试（占绝大多数）与少量发布测试
catalog/examples/      # 每个功能的正式资产合同（machine-readable）
catalog/review/        # 审查状态和被 hold 的合同与代码（不进入安装包）
skills/                # 求解、开发和提取方法
tools/docs/            # 手写用户指南、API 参考构建器与中文阅读层
scripts/               # 构建、catalog、文档与安装校验工具
contracts/             # 资产合同 schema、准入与接收规则
licenses/              # 许可与来源署名
```

## 项目规则

接手请先读 [`AGENTS.md`](AGENTS.md)。三条线边界和检索策略见 [`ARCHITECTURE.md`](ARCHITECTURE.md)，
项目规则见 [`RULES.md`](RULES.md)。

## 开发

一个功能 = 实现 + 直接测试 + 正式合同（以及由合同生成的中英双语文档）。
测试以数值对照为准，修改实现必须保持既有断言与容差。开发环境、验证命令和贡献规则见
[`CONTRIBUTING.md`](CONTRIBUTING.md)。

可复现环境使用项目内的 Python 3.14.7 容器；本地使用宿主 Docker engine 的 CPU 架构，
GitHub CI 固定跑 Linux/amd64：

```bash
python3 scripts/dev_container.py prepare   # Windows: py -3
python3 scripts/dev_container.py check
```

当前处于首次公开发布前的开发阶段；wheel 仅用于本地 development 验收，发布基线确定后再统一冻结。

## English

SciRel is a self-contained Python library for scientific computing. It packages reusable scientific functions behind plain Python callables, with NumPy, SciPy and mpmath as core dependencies; plotting and file-format adapters are not part of the library. Each public function carries a formal asset contract that defines its model, inputs/outputs, units, applicability and failure behavior.
The bilingual manual is generated from those contracts. The repository keeps only the
implementation, its tests, the contracts and the documentation pipeline; the project is
pre-release and does not publish wheels yet.
