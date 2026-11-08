# 清理门禁规格（prune + hygiene）

**这是规格，不是实现。** 实现等 CodeFusion 把 `dev_container.sh prune` / `check_workspace_hygiene` 的形态做出来再抄，不各写一套。

基线：SciReL `origin/main` = `e7fa1bba`，实测数据取自本机 context `colima-scirel-local`。

## 一、现状：已有能力与缺口

### 已经有的

| 能力 | 位置 | 作用范围 |
| --- | --- | --- |
| `dev_container.py clean` | `scripts/dev_container.py:922` 起 | 只清**当前 checkout** 的 venv，可选 `--image` / `--cache` |
| `cleanup_compose_project()` | `:763` | `compose down --remove-orphans` + 删本项目的 `<project>_default` 网络 |
| `clean_generated_caches()` | `:840` | `.pytest_cache`、`.ruff_cache`、`.mypy_cache` |
| 检查末尾清理 | `skills/development/scirel-acceptance/scripts/check_all.py:118` | 删 `build/`、`src/scirel.egg-info` |

### 缺的

**只清"当前 checkout"，不清"已经消失的 checkout 留下的东西"。** 实测：

| 指标 | 实测值 |
| --- | --- |
| 活 checkout（`git worktree list`） | 3 |
| `scirel-venv-*` 卷 | 29，其中**孤儿 27 个** |
| `scirel-dev-*_default` 网络 | 3（对应 3 个已不存在的 checkout） |
| `Exited` 的容器 | 1 个（`suspicious_wiles`，`Exited (100)` 两天，且不在 `scirel-dev-` 命名空间内） |

孤儿卷名单（27 个，判据见下）：`0194fc742d`、`0c9f159704`、`1199f833b5`、`34b2eeac16`、`3f0ac854bc`、`413bb57de9`、`46694446bb`、`473d5a353e`、`5596a05b85`、`57346a6090`、`68e7bd0eea`、`6c7bc57e79`、`76b30d0f00`、`864a9aff90`、`97e354c664`、`9b78a8f2ca`、`9c5f13dba2`、`a8866edd7b`、`bf3823755d`、`dbda5af4ac`、`e09a20d322`、`ebd466b283`、`ef72ec032f`、`f9e7596a32`、`faae905747`、`issue108-evidence`、`local`。

这个数量说明问题不在"人忘了清"，在于**没有任何机制把"checkout 没了"和"它的卷还在"联系起来**。

## 二、prune 扫什么

判活的办法只有一个：**用现存 checkout 的绝对路径重算 hash，和资源名里的 hash 比**。不需要任何持久记录。

`project_name()`（`scripts/dev_container.py:44-47`）就是 `sha256(normcase(ROOT))[:10]`，`venv_volume()`（`:54-56`）取它的后缀。所以判据可以完全现场算出。

### 1. 卷

- 目标：`scirel-venv-<10位hash>`
- 活集合：`git worktree list --porcelain` 里每个 `worktree <path>` 的路径，各自 `sha256(normcase(path))[:10]`
- 不在活集合里的判孤儿
- **例外一**：`scirel-uv-cache-<pyver>` 是跨 checkout 共享缓存，**永不 prune**
- **例外二**：`scirel-venv-local`（compose 默认名）和 `scirel-venv-issue108-evidence` 这类手工命名，名字里没有 checkout hash，无法自动判活。两种处理：要么显式列进白名单并要求人工确认，要么规定"手工覆盖名必须带可识别前缀（如 `scirel-venv-manual-*`）"，prune 对 `manual-` 前缀一律只报告不删

### 2. 网络

- 目标：`scirel-dev-<10位hash>_default`
- 判据同卷
- 现有 `cleanup_compose_project()` 已能删单个，缺的是批量扫

### 3. 容器

- 目标：`scirel-dev-<10位hash>-dev-run-*`
- **只清 `Exited` 且对应 checkout 已不存在的**
- **绝不碰 `Up` 的**——那可能是别人正在跑的检查，今天已经因为并行出过两次事故
- **绝不碰不在 `scirel-dev-` 命名空间下的**：`suspicious_wiles` 这种手工容器，prune 只列出来，要人判断

### 4. 宿主临时目录

- `/tmp/scirel-*`、`/tmp/issue*-check.log` 这类
- 按 mtime 超过 24 小时才报
- 注意：仓库规则要求临时输出写容器内或已忽略的运行目录；`/tmp` 下的残留属于"没遵守"，prune 报出来正好提醒

### 5. 仓库内运行产物

`build/`、`src/scirel.egg-info`、`.pytest_cache`、`.ruff_cache`、`.mypy_cache` —— 已有删除逻辑，prune 直接复用，不重写。

## 三、hygiene 断言放在 check 的哪一步

**放在最后一步**，在 `wheel exposure` 之后、打印 `ALL GREEN` 之前，作为一条**报告型**步骤：

- 打印当前孤儿卷数、孤儿网络数、退出容器数、活 checkout 数、本地 `agent/*` 分支数
- **只有超过阈值才判 FAIL**
- 输出格式跟现有步骤一致：`PASS  workspace hygiene  (0 s)` / `FAIL  workspace hygiene`

理由：孤儿资源不影响代码正确性。把"磁盘上有个旧卷"判成代码红，会逼人为了过门禁去删资源，而删资源是人工动作、要核身份。门禁只该负责**让问题可见**，不该把清理变成通过条件。

如果将来要更严，加一个 `--strict-hygiene`，只在集成或发布流程里用。

## 四、阈值（按实测现值定）

| 指标 | 实测现值 | 建议阈值 | 超阈值时 |
| --- | --- | --- | --- |
| 活 checkout | 3 | ≤ 4（主 checkout + 3 个 worker） | FAIL |
| 孤儿 `scirel-venv-*` | 27 | ≤ 活 checkout 数（现 3） | FAIL |
| 孤儿 `scirel-dev-*_default` 网络 | 3 | ≤ 1 | FAIL |
| `Exited` 的 `scirel-dev-*-dev-run-*` | 0 | 0 | FAIL |
| 本地 `agent/*` 分支 | 2 | 只报数，不设阈值 | — |
| 已合并未删的 `agent/*` 分支 | 0 | 0 | 报数 + 提示 |

阈值取"活 checkout 数"而不是固定值，是因为它会随并行度变。固定值迟早要改，改的时候没人记得为什么。

## 五、三条硬约束

### 1. 不许借清理门禁复活 receipt

`#133` 把 receipt 的写入/prune/reuse 整层删掉了，那是我们自己的决定。**prune 只做"扫孤儿资源"，不引入任何新的状态记录。** 判据全部现场可算（现存资源 × 现存 checkout），不需要持久化，也不需要"上次扫过什么"。

如果将来有人想给 prune 加"清理历史"，那是在重建判定层，按 `RULES.md` 第 4 条直接否掉。

### 2. prune 默认只报告，`--apply` 才删

删之前逐项打印：要删的名字、判据（哪个 hash 不对应任何活 checkout）、以及它的创建时间。`--apply` 之前必须有这份清单，不接受"直接扫直接删"。

### 3. 删 worktree 前核三项

今晚新踩出来的规矩，写进规格：

- 有 owner 账本条目（#121 里能查到谁建的、干什么用）
- 有未提交内容（`git status --porcelain` 非空）
- 有 worker 在跑（对应容器 `Up`，或 worktree 里进程活跃）

**任一为真，不得删。**

注意"无主"的定义：**指没有 owner 登记，不是 HEAD 追不到 origin**。今天有过一次误判——某个 worktree 的 HEAD 因为 rebase 对不上远端，被当成"无主"处理，实际它背后有活人。

## 六、与 CodeFusion 的对齐

CodeFusion 正在做同一件事：合并即清 + `dev_container.sh prune` + `check_workspace_hygiene`。本规格只定 SciReL 侧的**扫描点**和**阈值**，接口形态等它落地后抄。

预留对齐项（等那边定了再写死）：

- prune 的动词与 `--apply` 语义
- hygiene 报告的字段名（孤儿数、阈值、判据）
- 是否共用一份"资源命名规则"文档

## 七、不在本规格范围

- **不实现。** 本文件是规格，代码等 CodeFusion 形态定了再写。
- 不动 receipt 机制（已删）。
- 不碰仓库外目录（`~/Projects/SciRel-ghost` 等）。
- 不做"自动清理定时任务"——清理必须是有人看着的显式动作。

## 八、已知的既有实现，冻结但要留出复用

`.worktrees/hygiene-gate`（分支 `agent/hygiene-gate`，`2ac20abf`）上已经有一份实现：`AGENTS.md` +16、`dev_container.py` +300、`test_dev_container.py` +128，含 `prune()` / `hygiene()` / `worktree_entries()` 等。

它是在"等 CodeFusion 形态"这条决定之前写的。**按当前决定冻结，不合、不扩、不删**，等 CodeFusion 的接口定下来后作为参照吸收或丢弃。

### 冻结前先记下：哪几块值得复用

别让它在冻结里烂掉。这三块将来大概率直接用：

| 复用什么 | 位置（该分支） | 为什么值得留 |
| --- | --- | --- |
| `project_name_for(root)` / `venv_volume_for(root)` | `dev_container.py` | 把"按任意路径算 hash"从"只算当前 checkout"里拆出来。prune 必须能对**不在场的** checkout 算 hash，这两个函数就是那个能力 |
| `worktree_entries()` / `checked_out_branches()` / `local_branch_names()` | 同上 | 把"活 checkout 集合"和"分支集合"变成可复用的只读查询，判活只依赖它，不依赖任何持久记录 |
| 卷 / 网络 / 容器三类分开扫的结构 | `container_records()` + `hygiene_report()` | 三类资源的判据不同（卷按 hash、网络按 hash、容器还要看 `Up`/`Exited`），混在一个循环里迟早出错。分开扫的结构是对的 |

**不复用的部分**：`HYGIENE_WORKTREE_THRESHOLD = 3` 这种固定阈值。本规格第四节已经说明阈值应取"活 checkout 数"而不是常量，固定值迟早要改且改的人不知道为什么。

### owner 与期限

- **owner**：SciReL 项目总控（本规格作者）。
- **期限**：CodeFusion 的 `dev_container.sh prune` / `check_workspace_hygiene` 形态落地后一周内，决定吸收哪几块、然后删掉这个 worktree 和分支。超期未决则在 #121 账本里重新登记并说明为什么还挂着。
- 冻结期间**不许往这个 worktree 里提交**；要改规格就改本文件，不动那份实现。
