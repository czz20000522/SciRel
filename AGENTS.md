# 接手说明

写给接手这个仓库的任何人或 agent。先读完这一页，这里不依赖聊天记录、私人笔记或某台机器的路径。

## 三层角色

SciRel 分三层，每层有自己的入口 skill 和验收标准，见 [skills/README.md](skills/README.md)：供给者提取候选，合并者把候选并入库，消费者用分发包解决问题。

## 这是什么

SciRel 是聚变和等离子体方向的 Python 科学计算库，每个公开函数都有一份正式合同，写明模型、单位、输入输出、适用范围和失败行为。

- **维护线：** 维护实现、测试和合同。
- **求解线：** 外部 agent 拿到分发包（catalog、wheel、`skills/development/usage/` 下的三个 skill），用它回答用户的物理问题，产物归用户。

要改进外部 agent 的回答，就改 skills、检索和合同，因为分发包里只有这些。`examples/` 不随包分发，只用来检验流程。改完用 `scripts/build_pure_delivery.py` 确认内容已进入分发包。

**开工第一步：查工单。** 运行 `python3 scripts/tickets.py list tickets --status decided`，列出的工单已有人工裁决，先执行它们，做法见 [tickets/README.md](tickets/README.md)。

代码和测试之外的规则，按需要读：

| 要做的事 | 读这里 |
| --- | --- |
| 了解整体边界 | [ARCHITECTURE.md](ARCHITECTURE.md) |
| 快速理解当前代码地图 | [docs/maintainer/codebase-map.md](docs/maintainer/codebase-map.md) |
| 项目规则 | [RULES.md](RULES.md) |
| 改代码或加功能 | [CONTRIBUTING.md](CONTRIBUTING.md) |
| 改合同 | [catalog/README.md](catalog/README.md)、[catalog/AUDIT.md](catalog/AUDIT.md) |
| 代码风格和公开 API | [`scirel-code-style` skill](skills/development/scirel-code-style/SKILL.md)（标准）、[`api-design-method` skill](skills/development/api-design-method/SKILL.md)（通用方法） |
| 遇到证据定不下来的物理问题 | [tickets/README.md](tickets/README.md)、[分级与工单格式](docs/maintainer/supply-pipeline.md) 第 7 节 |
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
tickets/           需要人工裁决的工单（按 kind 分目录）
licenses/          许可和署名
```

## 环境和验收

开发环境由宿主机上的 uv 管理（维护者决定，不使用容器）。解释器版本由 `.python-version` 固定，解释器和依赖都由 uv 安装到项目目录内；依赖版本由 `uv.lock` 固定。宿主机只需要 Git、Python 3 启动器和 uv。GitHub Actions
只保留为手动触发的 Linux/amd64 跨设备抽查，不进入每个 PR 的等待链。

```sh
python3 scripts/dev.py prepare  # Windows 可用 py -3
python3 scripts/dev.py check
python3 scripts/dev.py pytest tests/<domain>/test_<asset>.py
python3 scripts/dev.py run python -B scripts/test_scope.py --changed <path>
python3 scripts/dev.py run --exclusive python -B scripts/validate_extraction_package.py <package> --repo .
```

解释器、运行产物一律留在项目内已被忽略的 `.runtime/` 下，不写到项目目录之外：主 checkout 的
`.runtime/` 放同一 clone 共用的解释器、uv 缓存和检查锁，每个 worktree 自己的 `.runtime/` 放 venv、字节码、ruff 缓存和
临时目录。这些位置由 `dev.py` 设置，所以命令都经它运行，不直接调用宿主机的 `python` 或 `uv run`。

交付证据必须来自 `python3 scripts/dev.py check`，它是发布档（默认 stage）。检查入口是
[`scirel-acceptance` skill](skills/development/scirel-acceptance/SKILL.md)，改代码前先读它。

`python3 scripts/dev.py check --stage dev` 是同一张计划表的开发档：跳过文档构建、wheel 构建、wheel 暴露和
示例执行，并 deselect `skills/development/scirel-acceptance/release_only_tests.txt` 里列出的发布级测试。
它证明"这批改动没破坏别处"，**不**证明打包产物可安装、文档站可构建、示例可执行。

- 合并进 `main` 的批次、以及任何对外交付声明，只能用发布档回执。
- **开发档回执不得当作发布证据引用。** `validate_extraction_package` 会拒绝 `stage=dev` 的回执，并要求
  在同一个候选上重跑发布档。
- 实现者自己跑的定向 `pytest`（域级、秒级）**不是任何一档的证据**，不进 PR 回执。
- 开发档快是因为它不证明打包、文档站和示例，**不是因为门禁更松**：它保留的每一步都是同一份检查、
  同一套失败判据。它持共享锁（与普通 `pytest` 同级），所以不挡别人、也不被别人挡；发布档持独占锁。
  共享持有仍会挡住独占，跑发布档前先停掉开发档。

提交前的门禁按风险分层，防的是自己和 agent 的失误，不是攻击者：所有防线都绕得过，拦的是无心之失在
不可逆之前被喊停。`pre-commit` 在宿主机上用 `python3 -I` 运行
`skills/development/scirel-acceptance/scripts/precommit_check.py`，只扫描暂存文本里的凭据和私有路径：
这类东西一旦进了公开历史，就要轮换凭据、改写历史，代价不可逆，值得堵在每一次提交上。lint、format 和
lockfile 属于质量问题，改一次提交就能修，放在合并前的完整检查里跑即可，不值得绑死提交路径。hook 是绊网，
绕得过，所以不能替代自己跑检查；反过来说，本该执行却静默跳过的检查等于防线失效——缺 `uv` 时完整检查必须
显式判红，不能悄悄判绿。

作放行依据的那次完整检查必须独占本仓库的测试（含所有 worktree）：`check` 和显式 `run --exclusive <command>` 持有同一 clone 的排他锁，`prepare`、`pytest`、普通 `run` 持有共享锁，有别的
测试或检查在跑时 `check` 直接拒绝启动，开始时打印 `EXCLUSIVE` 行，PR 证据里贴上这一行。绕过 `dev.py` 直接跑的
测试不受锁约束，所以跑检查期间不要另起测试。并行测试只用于开发期局部验证，结果不写进 PR 证据，也不据此判红
判绿。`tests/docs` 的 Sphinx 夹具在并发内存压力下会在 setup 阶段失败，那是假红，不是代码缺陷；遇到这种红先
确认是否有别的测试在跑。

提取包完整校验用上面的显式独占命令，`--repo` 与候选必须属于被锁住的同一 clone。校验器在完整检查和变异前后核对本次短期凭据与真实内核锁；普通共享运行不继承独占标记。直接调用 `check_all.py` 不等于独占，不要在 `run` 中嵌套 `dev.py check`。

POSIX 主机上，入口收到 `SIGINT`、`SIGTERM` 或 `SIGHUP` 时会停止本次启动的命令进程组，并等整组退出后才释放锁；独占命令正常返回时也先收尾残留子进程。短期凭据在整组退出后、原锁释放前退役。
5 秒内未退出的进程组会被强制停止。中断结果不是通过，不得沿用中断前的绿灯。

## 写入边界

- 一个 agent 只能修改分配给它自己的 worktree 和 issue 明确要求的仓库内路径。
- 不写用户主目录、`Projects` 的同级目录、`.codex`、全局 Git 配置、SSH、包管理器配置或其他项目。
- 临时输出写到 `.runtime/` 或仓库中其他已被忽略且能立即清理的运行目录；提交前必须清掉。
- 需要安装或升级宿主机软件（包括 uv 本身）时，属于环境操作，先单独获得任务授权并报告，不把它伪装成项目改动。
- 仓库文件是唯一交付物；聊天记录、私人路径和某台机器的环境事实不能成为运行依赖。

## 并行开发与合并

- 一个 issue 对应一个临时分支和至少一个独立 worktree。分支名用 `agent/<issue>-<short-topic>`。
- 每个 agent 从最新的 `origin/main` 开始；不要多人共用一个可变 worktree。
- 功能或整理完成前先在独立 worktree 内做局部验证；PR 前 rebase 到最新 `origin/main`，再在最终提交上跑完整检查。
- `main` 只接收通过 PR 和本地完整检查的合并。涉及多个候选时，由集成者另开干净的 integration worktree 重新验证组合结果。
- 合并后删除临时分支和 worktree。只有确实会丢失历史指针时才保留 `refs/archive/*` 存档引用。

## 设备独立性

- 代码、脚本和文档只使用仓库相对路径；禁止盘符、WSL 内部路径、固定用户名和机器专属目录。
- Python 路径处理使用 `pathlib`；Git hook 只使用 POSIX `sh` 和 Python launcher，Windows 走 Git Bash。
- GitHub Actions 固定使用 Linux/amd64，但只作为手动跨设备抽查；PR 合并前以本地完整检查为最终门禁。
- 新增脚本必须能经 `dev.py run` 在项目环境中运行；如果必须依赖某个宿主系统能力，先说明原因、替代方案和删除条件。
## 必须遵守

这些规则多数由 `tests/architecture/test_repository_skeleton.py` 检查。

1. **真值链：证据 → 代码 → 合同 → 文档。** 代码之所以是对的，只因为**证据**支持它——已发表文献、被拆解项目的实际行为、物理正确性、解析恒等式。合同是代码的衍生品，文档是合同的衍生品。三条箭头各有各的失败模式，不要混：
   - **合同与代码不符 → 合同错了。** 以代码的**实际行为**改写合同，不留两个版本。这一步只解决"合同没写对"，**不构成"代码是对的"的证据**。
   - **代码与证据不符 → 代码错了。** 开工单、按安全默认处理（行为不动、`known_limitations` 记录、等人工裁决），**不得**把错误行为写进合同让它变成"已声明"。
   - **证据拿不到 → 如实记 `cannot establish`** 并写清卡点。缺失的证据不能当证据；"测试钉住了当前行为"或"与另一实现一致"都不等于正确性证据。
   自查一句话：*这条合同说法背后，是证据，还是只是代码现在的样子？*
2. **改物理必须带证据、走分级评审。** 改公式、符号、单位或数值方法，必须附上独立依据、测试矩阵和前后对比，再按 [分级评审](docs/maintainer/supply-pipeline.md) 第 7 节处理（A 级交叉预审、B 级两个独立评审、C 级人工裁决）。证据不足以定论时开工单、先执行安全默认，不先改实现。不能为了通过测试放宽容差。
3. **公开仓库自给自足。** 代码、测试、门禁和文档构建只依赖仓库内跟踪的文件，不写本机路径，也不依赖私人笔记。
4. **公开与否由实现决定。** `src/` 里没有实现的资产不进公开 catalog，合同留在 `catalog/review/examples/`；门禁只检查结构，不判科学对错。
5. **报告先回答问题。** 方法写物理，结果配图，不越权判定可用或不可用。SciRel 只在恰好用到时顺带提及。
6. **如实写结果。** 失败和未运行的内容不能写成通过。

7. **观测必须可判别：通过 / 失败 / 未观测是三态。** 这是本仓库代价最高的一类缺陷的总规则，起因见 [观测完整性](docs/maintainer/observation-integrity.md)。

   一个检查最容易犯的错不是算错，而是**它的输出对"通过形状"与"失败形状"没有分辨力**：变异账为空既可能是"全存活"也可能是"根本没跑"；`not_exercised` 既可能是"测试没走到"也可能是"装置改不动返回值"；`exit 128` 既可能是超时也可能是别的，而 `capture_output` 把原因丢了。损失信息的观测**不会报错**，它会邀请读者用先验补那一位——补出来的总是往"还好"方向的故事。这份仓库里已有四次这样的补位：把变异的空账读成"全存活"、把 `not_exercised` 读成"无缺口"、把克隆失败读成"超时"、用落后 5 个提交的工作树读成"改动丢了"。

   因此：

   - **三态必须显式**。检查输出的每个判定只能落在 `pass` / `fail` / `not-observed` 三者之一，"未观测"要单独命名（本仓库已有的落法：`dev.py` 的退出码 75 表示没拿到锁、变异的 `UNKNOWN` 档、包内 `runtime_status=NOT_RUN`、`retrieval.completeness=unknown`），**并且永不被聚合进 `pass`**。
   - **失败必须携带原因**。任何用 `capture_output=True` 起的子进程，其失败要把 `stderr` 带进抛出的错误里；丢掉 stderr 等于把诊断成本转嫁给下一个读者。由 `scripts/check_observation_integrity.py` 机械检查。
   - **数字必须带出处**。引用任何测量时写明它测的是哪棵树、哪个 revision。同一个脚本读的是工作树，读到落后提交的树就等于测了另一个对象。
   - **证据必须在交付物里**。落在被忽略目录（如 `.runtime/`）的"证据"在结项时不存在；回执要么进被跟踪的位置，要么附可复跑的指纹。
   - **判据不可由被判定方书写**。文档测试的 oracle（`zh-pairing.json`）不由改写合同的同一方重建；交付包消费者不读 `src/`。
   - **有损容器按记录合并**。单文件多记录（`zh_*.json`、`tasklist.json`）整份取一侧会静默丢弃另一侧；必须逐条按合同条款数裁决。

## 当前状态

待办都放在固定位置，不另写交接日志：

- 其余案例的整理计划：[examples/PLAN.md](examples/PLAN.md)
- 等待人工裁决的问题：`tickets/` 下 `status: open` 的工单

已知未完成：

- skills 相关测试已移至 `tests/`，由默认测试入口运行；`skills/` 内脚本仍分别由验收、交付或各自 skill 的人工入口负责调用。
- 公开 API 的迁移进度见 [API 规范](skills/development/scirel-code-style/references/api-spec.md)。

**能力边界冻结（维护者决定）：** 暂停接收新资产，供给线的准入随之中止，先还债、先清理。解除条件由维护者另行决定。
