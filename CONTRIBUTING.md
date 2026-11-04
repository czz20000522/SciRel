# Contributing to SciRel

SciRel 是一个自包含的科学计算库。贡献的核心单位是一个**功能**，它由三部分组成：

1. `src/scirel/<domain>/` 中的实现；
2. `tests/` 中的直接功能测试（数值对照为主）；
3. `catalog/examples/` 中的正式资产合同（模型、输入输出、单位、适用条件、失败行为、示例与验证边界）。

由合同生成的中英双语文档（HTML）是派生阅读层，不单独维护。

## 环境

可复现环境使用项目内的 Python 3.14.7 容器，包声明支持 `>=3.12`。本地容器跟随 Docker engine 架构；
Apple Silicon 应使用原生 arm64 engine 快速开发，GitHub CI 固定跑 Linux/amd64。宿主机只需要 Git、
Python 3 launcher 和 Docker-compatible engine：

```bash
python3 scripts/dev_container.py prepare   # Windows: py -3
python3 scripts/dev_container.py check
python3 scripts/dev_container.py shell
git config core.hooksPath .githooks
```

`prepare` 会在项目命名的容器卷中执行 `uv sync --locked --group test`，不会在宿主仓库里生成 `.venv`。
`check` 是完整本地 CI。只跑一个测试文件时使用：

```bash
python3 scripts/dev_container.py pytest tests/<domain>/test_<asset>.py
```

容器只挂载当前 checkout，不挂用户主目录。删除该 checkout 的容器卷使用
`python3 scripts/dev_container.py clean`。原生 `.venv` 只用于临时探索，不作为交付证据。

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
# 最接近的测试
python3 scripts/dev_container.py pytest tests/<domain>/test_<asset>.py

# 根据实际改动选择受影响域和通用层，再在容器内执行打印出的命令
python3 scripts/dev_container.py shell
python -B scripts/test_scope.py --changed src/scirel/<domain>/<module>.py

# 合并前完整验收：全量测试、门禁、合同示例、文档与 wheel 暴露检查
python3 scripts/dev_container.py check
```

`check` 必须在最终提交上通过并打印 `ALL GREEN`。GitHub Actions 使用同一个容器定义再次运行它。
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

## Issue 和 PR

任务用 `.github/ISSUE_TEMPLATE/agent-task.md` 写明方法、写入范围和验收标准，PR 用 `.github/pull_request_template.md`。评审按[评审清单](skills/development/scirel-code-style/references/review-checklist.md)判断。GitHub Actions 会运行完整容器检查；本地仍须在最终提交上贴出 `ALL GREEN` 的最后几行。
