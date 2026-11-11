# Contributing to SciRel

SciRel 是一个自包含的科学计算库。贡献的核心单位是一个**功能**，它由三部分组成：

1. `src/scirel/<domain>/` 中的实现；
2. `tests/` 中的直接功能测试（数值对照为主）；
3. `catalog/examples/` 中的正式资产合同（模型、输入输出、单位、适用条件、失败行为、示例与验证边界）。

由合同生成的中英双语文档（HTML）是派生阅读层，不单独维护。

## 环境

开发环境由宿主机上的 uv 管理，包声明支持 `>=3.12`。宿主机需要 Git、Python 3 launcher 和
[uv](https://docs.astral.sh/uv/)；开发用的解释器版本由 `.python-version` 固定（3.14.7），安装在项目 `.runtime/python/` 中，依赖由 `uv.lock` 固定。GitHub Actions 只保留为手动 Linux/amd64 抽查。

```bash
python3 scripts/dev.py prepare  # Windows: py -3
python3 scripts/dev.py check
python3 scripts/dev.py run python -B scripts/test_scope.py --changed <path>
git config core.hooksPath .githooks
```

`prepare` 安装固定版本的解释器，再执行 `uv sync --locked --group test`。解释器和所有运行产物都留在项目内
已被忽略的 `.runtime/` 下，不写到项目目录之外：

- 主 checkout 的 `.runtime/`：同一 clone 的所有 worktree 共用的解释器、uv 缓存和检查锁；
- 每个 worktree 自己的 `.runtime/`：venv、字节码、ruff 缓存和临时目录。

`dev.py` 设置这些位置，所以要通过它运行命令（`run`、`pytest`、`check`），不要直接调用宿主机的 `python` 或
`uv run`。`doctor` 列出解释器、uv 和每个运行目录；`clean` 删除本 worktree 的环境和缓存，保留日志；`clean --shared`
还会清理共用的 uv 缓存。解释器保留，供其他 worktree 使用。

`core.hooksPath` 指向 `.githooks` 后，`git commit` 在宿主机运行 `precommit_check.py`：只扫描暂存文本里的私有路径
和密钥，只用标准库和 Git，不需要项目环境。lint、format 和 lockfile 检查只在 `check` 里运行。push 不触发任何
检查，合并前自己跑一次完整检查。

只跑一个测试文件时使用：

```bash
python3 scripts/dev.py pytest tests/<domain>/test_<asset>.py
```

## 修改前

1. 读相关实现、直接测试和 `catalog/examples/` 中的合同；确认修改属于哪个科学合同。
2. 科学行为变化（公式、单位/轴序、默认值、边界、失败语义、数值方法、依赖绑定）先写失败回归，
   保留原断言与容差；不得为让实现通过而放宽容差。
3. 未公开发布前公共 API 可以重构（改域名、函数名、签名），不保留兼容别名；同时更新合同、
   测试与双语阅读层。
4. 公共 API 的命名与数值语义对标 SciPy（参数名、默认值、结果字段、成功判定），不自造约定；
   SciPy 没有覆盖的部分（合同机制、三层角色、catalog 准入）保留项目自有规范。细则见
   [`RULES.md`](RULES.md) 第 15 节。

## 实现与性能

- 实现可以复刻来源行为，但必须改写成适配本项目的设计与代码，不得直接复制来源实现；
- 先保证正确性，再考虑性能；
- 默认使用 NumPy 向量化的 Python；只有 profiling 证明是瓶颈、且维护成本可接受时才引入 C 扩展；
- C 扩展会改变 wheel 平台边界，引入前需说明构建、ABI 与分发影响。

## 验证

```bash
# 最接近的测试
python3 scripts/dev.py pytest tests/<domain>/test_<asset>.py

# 根据实际改动选择受影响域和通用层，再执行打印出的命令
python3 scripts/dev.py run python -B scripts/test_scope.py --changed src/scirel/<domain>/<module>.py

# 合并前完整验收：全量测试、门禁、合同示例、文档与 wheel 暴露检查
python3 scripts/dev.py check
```

`check` 必须在最终提交上通过并打印 `ALL GREEN`；这个本地结果是合并门禁。GitHub Actions 不自动运行，只在需要跨设备抽查时手动触发。
文档检查使用本次任务独占且不存在的输出目录；核对页面与实际输出后按
[`catalog/RECORDS.md`](catalog/RECORDS.md) 清理。不能覆盖仍在使用的快照。

发布轮子/安装包目前不在日常流程内；首次公开发布基线确定后统一冻结并补充对应发布检查。

## 文档

- 代码即真值，正式合同是代码的衍生品，文档由合同派生；中英文档都必须从同一份合同生成并保持一致；
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

任务用 `.github/ISSUE_TEMPLATE/agent-task.md` 写明方法、写入范围和验收标准，PR 用 `.github/pull_request_template.md`。评审按[评审清单](skills/development/scirel-code-style/references/review-checklist.md)判断。PR 必须贴出最终提交上的本地 `ALL GREEN` 最后几行；GitHub Actions 是可选的手动跨设备抽查。
