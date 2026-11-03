# Contributing to SciRel

SciRel 是一个自包含的科学计算库。贡献的核心单位是一个**功能**，它由三部分组成：

1. `src/scirel/<domain>/` 中的实现；
2. `tests/` 中的直接功能测试（数值对照为主）；
3. `catalog/examples/` 中的正式资产合同（模型、输入输出、单位、适用条件、失败行为、示例与验证边界）。

由合同生成的中英双语文档（HTML）是派生阅读层，不单独维护。

## 环境

- 开发和验收使用 Python 3.14（见 `.python-version`）；包声明支持 `>=3.12`；
- 使用仓库内 `.venv` 或重建环境：

```bash
python3.14 -m venv .venv
.venv/bin/python -m pip install -e . --group test
# 或
uv sync --locked --group test
```

## 修改前

1. 读相关实现、直接测试和 `catalog/examples/` 中的合同；确认修改属于哪个科学合同。
2. 科学行为变化（公式、单位/轴序、默认值、边界、失败语义、数值方法、依赖绑定）先写失败回归，
   保留原断言与容差；不得为让实现通过而放宽容差。
3. 未公开发布前公共 API 可以重构（改域名、函数名、签名），不保留兼容别名；同时更新合同、
   测试与双语阅读层。

## 实现与性能

- 实现可以复刻来源行为，但必须改写成适配本项目的设计与代码，不得直接复制来源实现；
- 先保证正确性，再考虑性能；
- 默认使用 NumPy 向量化的 Python；只有 profiling 证明是瓶颈、且维护成本可接受时才引入 C 扩展；
- C 扩展会改变 wheel 平台边界，引入前需说明构建、ABI 与分发影响。

## 验证

```bash
# 受影响的功能测试（推荐先跑最贴近的测试文件）
.venv/bin/python -B -m pytest tests/<domain>/test_<asset>.py -q

# 根据实际改动选择受影响域和通用层，再执行输出的命令
.venv/bin/python -B scripts/test_scope.py --changed src/scirel/<domain>/<module>.py

# 合并前的完整验收：全量测试、门禁、合同示例、文档构建、样例报告
.venv/bin/python -B skills/development/scirel-acceptance/scripts/check_all.py

# 合同与文档
.venv/bin/python scripts/validate_asset_documents.py catalog/examples
.venv/bin/python scripts/scirel_docs.py build --output dist/docs-check
```

文档检查使用本次任务独占且不存在的输出目录；核对页面与实际输出后按
[`catalog/RECORDS.md`](catalog/RECORDS.md) 清理。不能覆盖仍在使用的快照。

发布轮子/安装包目前不在日常流程内；首次公开发布基线确定后统一冻结并补充对应发布检查。

## 文档

- 正式合同是唯一科学真值；中英文档都必须从同一份合同生成并保持一致；
- 中文与英文阅读层必须同步更新；HTML 仅是派生显示；
- 手册目标形态是「教科书式」：从领域问题出发，给出模型、调用、实际结果与解释；
- 每个函数都要有可运行的说明示例。

## 许可与来源

自行实现不等于免除许可义务。来源项目的许可与署名义务保留在 `licenses/`；新增或改写一个功能时
确认其许可与署名材料仍然正确。未声明独立分发许可证前，不要假定可以再分发。

## 提交

- 一次提交一个连贯的功能/修复批次；
- 提交说明写清改了什么、为什么、可观察行为、验证命令与未验证边界；
- 不提交生成物（HTML 快照、wheel、缓存）与本机配置；
- 不要在未经授权时改写冻结的来源、审核或准入记录。
