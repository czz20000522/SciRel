# 接手说明

写给接手这个仓库的任何人或 agent。先读完这一页，这里不依赖聊天记录、私人笔记或某台机器的路径。

## 三层角色

SciRel 分三层，每层有自己的入口 skill 和验收标准，见 [skills/README.md](skills/README.md)：供给者提取候选，合并者把候选并入库，消费者用分发包解决问题。

## 这是什么

SciRel 是聚变和等离子体方向的 Python 科学计算库，每个公开函数都有一份正式合同，写明模型、单位、输入输出、适用范围和失败行为。

- **维护线：** 维护实现、测试和合同。
- **求解线：** 外部 agent 拿到分发包（catalog、wheel、`skills/development/usage/` 下的三个 skill），用它回答用户的物理问题，产物归用户。

要改进外部 agent 的回答，就改 skills、检索和合同，因为分发包里只有这些。`examples/` 不随包分发，只用来检验流程。改完用 `scripts/build_pure_delivery.py` 确认内容已进入分发包。

代码和测试之外的规则，按需要读：

| 要做的事 | 读这里 |
| --- | --- |
| 了解整体边界 | [ARCHITECTURE.md](ARCHITECTURE.md) |
| 快速理解当前代码地图 | [docs/maintainer/codebase-map.md](docs/maintainer/codebase-map.md) |
| 项目规则 | [RULES.md](RULES.md) |
| 改代码或加功能 | [CONTRIBUTING.md](CONTRIBUTING.md) |
| 改合同 | [catalog/README.md](catalog/README.md)、[catalog/AUDIT.md](catalog/AUDIT.md) |
| 代码风格和公开 API | [`scirel-code-style` skill](skills/development/scirel-code-style/SKILL.md)（标准）、[`api-design-method` skill](skills/development/api-design-method/SKILL.md)（通用方法） |
| 回答用户的物理问题 | [求解 skill](skills/development/usage/scirel-solving/SKILL.md)、[流程框架](skills/development/usage/scirel-solving/references/workflow.md) |

## 目录

```text
src/scirel/        科学实现，按领域组织
tests/             功能测试和架构、文档、交付、工具测试
catalog/examples/  已公开功能的合同（由代码派生的记录）
catalog/review/    评审期合同与候选代码（不进入安装包）
contracts/         合同 schema 和准入规则
scripts/           校验和构建工具
skills/            求解、开发和提取方法
tools/docs/        手册内容和构建器
examples/          求解样例和待整理案例
licenses/          许可和署名
```

## 环境和验收

可复现开发环境由项目内的 Python 3.14.7 容器定义。本地容器跟随 Docker engine 架构，并承担日常和合并前的
完整检查。GitHub Actions 只保留为手动触发的 Linux/amd64 跨设备抽查，不进入每个 PR 的等待链。宿主机只需要
Git、Python 3 启动器和 Docker-compatible engine；依赖、缓存和虚拟环境都留在项目自己的容器卷里。

每个 clone 必须先显式选择自己的 Docker context；禁止依赖全局默认 context：

```sh
python3 scripts/dev_container.py context <docker-context>  # Windows 可用 py -3
python3 scripts/dev_container.py prepare
python3 scripts/dev_container.py check
python3 scripts/dev_container.py pytest tests/<domain>/test_<asset>.py
```

选择保存在未提交的仓库 Git 元数据中，并被同一 clone 的所有 worktree 共享；临时覆盖使用
`SCIReL_DOCKER_CONTEXT`。未配置、空值或 `default` context 会 fail-closed。`doctor` 显示选中的 context 和实际 engine 名称。

本机原生 `.venv` 可以用于快速探索，但交付证据必须来自容器内同一条检查。检查入口是
[`scirel-acceptance` skill](skills/development/scirel-acceptance/SKILL.md)，改代码前先读它。
不再维护 WSL、Windows 或 macOS 专属的隐藏测试环境。

## 写入边界

- 一个 agent 只能修改分配给它自己的 worktree 和 issue 明确要求的仓库内路径。
- 不写用户主目录、`Projects` 的同级目录、`.codex`、全局 Git 配置、SSH、Docker 配置、包管理器配置或其他项目。
- 临时输出写到容器内临时目录，或仓库中已被忽略且能立即清理的运行目录；提交前必须清掉。
- 容器只挂载当前 checkout 和项目命名的依赖卷，不挂载用户主目录。需要改动宿主机 Docker 引擎或安装系统软件时，
  属于环境操作，先单独获得任务授权并报告，不把它伪装成项目改动。
- 仓库文件是唯一交付物；聊天记录、私人路径和某台机器的环境事实不能成为运行依赖。

## 并行开发与合并

- 一个 issue 对应一个临时分支和至少一个独立 worktree。分支名用 `agent/<issue>-<short-topic>`。
- 每个 agent 从最新的 `origin/main` 开始；不要多人共用一个可变 worktree。
- 功能或整理完成前先在独立 worktree 内做局部验证；PR 前 rebase 到最新 `origin/main`，再在最终提交上跑完整容器检查。
- `main` 只接收通过 PR 和本地完整检查的合并。涉及多个候选时，由集成者另开干净的 integration worktree 重新验证组合结果。
- 合并后删除临时分支和 worktree。只有确实会丢失历史指针时才保留 `refs/archive/*` 存档引用。

## 设备独立性

- 代码、脚本和文档只使用仓库相对路径；禁止盘符、WSL 内部路径、固定用户名和机器专属目录。
- Python 路径处理使用 `pathlib`；Git hook 只使用 POSIX `sh` 和 Python launcher，Windows 走 Git Bash。
- 本地容器跟随当前 Docker engine 的 CPU 架构，Apple Silicon 默认使用原生 arm64，避免模拟器拖慢开发。
- GitHub Actions 固定使用 Linux/amd64，但只作为手动跨设备抽查；PR 合并前以本地容器检查为最终门禁。
- 新增脚本必须能在容器中运行；如果必须依赖某个宿主系统能力，先说明原因、替代方案和删除条件。
## 必须遵守

这些规则多数由 `tests/architecture/test_repository_skeleton.py` 检查。

1. **代码即真值。** 合同是代码的衍生品，文档是合同的衍生品。实现和合同不一致时以代码为准、改合同，不留两个版本。
2. **不擅自改物理。** 公式、符号、单位、数值方法的取舍要先问维护者。不能为了通过测试放宽容差。
3. **公开仓库自给自足。** 代码、测试、门禁和文档构建只依赖仓库内跟踪的文件，不写本机路径，也不依赖私人笔记。
4. **公开与否由实现决定。** `src/` 里没有实现的资产不进公开 catalog，合同留在 `catalog/review/examples/`；门禁只检查结构，不判科学对错。
5. **报告先回答问题。** 方法写物理，结果配图，不越权判定可用或不可用。SciRel 只在恰好用到时顺带提及。
6. **如实写结果。** 失败和未运行的内容不能写成通过。

## 当前状态

待办都放在固定位置，不另写交接日志：

- 其余案例的整理计划：[examples/PLAN.md](examples/PLAN.md)

已知未完成：

- `skills/` 下的测试不在默认测试范围内，也没有整理到能全部通过。
- 公开 API 的迁移进度见 [API 规范](skills/development/scirel-code-style/references/api-spec.md)。
