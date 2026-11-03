# 接手说明

写给接手这个仓库的任何人或 agent。先读完这一页，这里不依赖聊天记录、私人笔记或某台机器的路径。

## 这是什么

SciRel 是聚变和等离子体方向的 Python 科学计算库，每个公开函数都有一份正式合同，写明模型、单位、输入输出、适用范围和失败行为。

- **维护线：** 维护实现、测试和合同。
- **求解线：** 外部 agent 拿到分发包（catalog、wheel、`skills/development/usage/` 下的三个 skill），用它回答用户的物理问题，产物归用户。

要改进外部 agent 的回答，就改 skills、检索和合同，因为分发包里只有这些。`examples/` 不随包分发，只用来检验流程。改完用 `scripts/build_pure_delivery.py` 确认内容已进入分发包。

代码和测试之外的规则，按需要读：

| 要做的事 | 读这里 |
| --- | --- |
| 了解整体边界 | [ARCHITECTURE.md](ARCHITECTURE.md) |
| 项目规则 | [RULES.md](RULES.md) |
| 改代码或加功能 | [CONTRIBUTING.md](CONTRIBUTING.md) |
| 改合同 | [catalog/README.md](catalog/README.md)、[catalog/AUDIT.md](catalog/AUDIT.md) |
| 回答用户的物理问题 | [求解 skill](skills/development/usage/scirel-solving/SKILL.md)、[流程框架](skills/development/usage/scirel-solving/references/workflow.md) |
| 看完整求解样例 | [examples/coil-offset/REPORT.md](examples/coil-offset/REPORT.md) |

## 目录

```text
src/scirel/        科学实现，按领域组织
tests/             功能测试和架构、文档、交付、工具测试
catalog/examples/  已公开功能的合同（科学真值）
catalog/review/    审查状态、被 hold 的合同和代码（不进入安装包）
contracts/         合同 schema 和准入规则
scripts/           校验和构建工具，统一入口 scripts/check_all.py
skills/            求解、开发和提取方法
tools/docs/        手册内容和构建器
examples/          求解样例和待整理案例
licenses/          许可和署名
```

## 环境和验收

```sh
uv sync --locked --group test      # 需要 Python 3.14，见 .python-version
.venv/bin/python -B scripts/check_all.py
```

`check_all.py` 全部通过才算全绿。改动较小时可以先跑 `scripts/test_scope.py --changed <路径>` 给出的范围，合并前跑全量。

## 必须遵守

这些规则多数由 `tests/architecture/test_repository_skeleton.py` 和 `scripts/review_gate.py` 检查。

1. **合同是科学真值。** 实现和合同不一致时明确选一个并记录原因，不留两个版本。
2. **不擅自改物理。** 公式、符号、单位、数值方法的取舍要先问维护者。不能为了通过测试放宽容差。
3. **公开仓库自给自足。** 代码、测试、门禁和文档构建只依赖仓库内跟踪的文件，不写本机路径，也不依赖私人笔记。
4. **状态由人工审查决定。** 没审过的功能放进 hold，不直接标为通过。门禁只检查结构。
5. **报告先回答问题。** 方法写物理，结果配图，不越权判定可用或不可用。SciRel 只在恰好用到时顺带提及。
6. **如实写结果。** 失败和未运行的内容不能写成通过。

## 当前状态

待办都放在固定位置，不另写交接日志：

- 待人工决定：[catalog/review/HUMAN_REVIEW_TODO.md](catalog/review/HUMAN_REVIEW_TODO.md)
- 其余案例的整理计划：[examples/PLAN.md](examples/PLAN.md)

已知未完成：

- `skills/` 下的测试不在默认测试范围内，也没有整理到能全部通过。
- `scripts/review_harness.py --check` 会因被 hold 的合同示例而失败，这是预期行为。
- 公开 API 和 `kinetic` 领域的结构还需要重构，见 [CONTRIBUTING.md](CONTRIBUTING.md) 关于发布前重构的说明。
