# 资源回收计划（worktree / 分支 / rubicon）

**状态：已部分执行。** 第 1–6 节的判据与第 3 节的表是 2026-11-17T09:52 的**执行前快照**（写作时一条 ref 都没删，一棵 worktree 都没动）。维护者随后批准了三项目标，执行记录见第 0 节；其余仍未执行。

## 0. 执行记录（2026-11-17T10:02，维护者批准的范围内）

批准范围只有三项：worktree `.worktrees/c1-kinetic-b`、本地分支 `agent/c1-kinetic-b`、本地分支 `agent/c1-field`。逐条执行，**执行前按第 7 节流程整表重跑并单条复核**：

| 目标 | 执行前复核 | 动作 | 结果 |
| --- | --- | --- | --- |
| worktree `.worktrees/c1-kinetic-b` | 检出 `rubicon/d0a5aef9-b55c`、HEAD `7f1eef8c`、工作区 0 改动、20 分钟内无文件变动（目录 mtime 停在 09:42） | `git worktree remove` | 成功；它检出的分支引用不受影响 |
| 分支 `agent/c1-kinetic-b`（`f3bdbfb6`） | 第 1 条 `--is-ancestor` 为真；第 2 条未被任何 worktree 检出；第 3 条无未提交；第 4 条建立于 05:57，远超 60 分钟门槛 | `git branch -d` | 删除 |
| 分支 `agent/c1-field`（`7d8e9264`） | 同上；建立于 02:37 | `git branch -d` | 删除 |

两处刻意的选择：删分支一律用 `git branch -d`（安全删除）而不用 `-D`，这样 git 自己会在"未合并"时拒绝，等于多一道闸门；全程逐条执行，没有通配符。

**执行后读回：** `git worktree list` 21 行（20 棵链接树 + 主 checkout），本地分支 25 条，`main` 与 `origin/main` 仍是 `7f1eef8c`。两条被删 ref 的 tip（`f3bdbfb6`、`7d8e9264`）对 `origin/main` 的 `--is-ancestor` 仍为真——**提交对象活在 `main` 里，删掉的只是指针**。`rubicon/d0a5aef9-b55c`、`integration/reland` 及后者远端同名分支均完好，三条 `rubicon/*` 一条没动。

**未执行（等批准）：** `agent/c1-kinetic-c`（被第 4 条新鲜度门槛挡住，建立于 09:25）、`agent/c3-receipt`（工作区脏）、`agent/ref-audit`、`rubicon/521e25b2-c3d7`、`rubicon/d0a5aef9-b55c`、`integration/reland` 与其远端同名分支。

配套文档：[#184 交接文档](handoff-184.md)。

## 1. 判据

### 1.1 可删判据：四条并列，缺一条即不可删

一条 ref 可以被删除，当且仅当下面四条**同时**成立。**四条是并列的，不是“第 1 条加三个注意事项”。** 只照第 1 条执行就会删错——实例见 1.2。

1. **tip 已包含在 `origin/main` 里**：`git merge-base --is-ancestor <ref> origin/main` 退出码为 0。硬判据，不接受“看起来合并了”，也不接受“内容相同”：`git diff origin/main...<ref>` 为空不等于历史相同（见 `integration/reland`）。
2. **不被任何活跃 worktree 检出**：`git worktree list --porcelain` 里没有 `branch refs/heads/<name>` 的条目。
3. **无未提交改动**：若被检出，该 worktree 的 `git status --porcelain` 为空；不干净就说明里面是没提交的活。
4. **不是新落的落脚分支，且不在受保护清单里。** 两个子条件都要过：
   - **新鲜度门槛（可判定）**：`git reflog show --date=iso <ref>` 里最新一条是 `branch: Created from …`，且距今**不足 60 分钟** → 判“待确认”，不论前三条如何。60 分钟是约定值，量级取“一次完整检查”；要改就改这条判据，不要在执行时口头放宽。
   - **受保护清单**：命中第 5 节清单（`origin/agent/hygiene-gate`、`origin/agent/140-integration-and-cleanup-spec`）即不可删。

**不满足第 1 条的，一律默认保留**，并写明它那些未进 `main` 的提交是什么。

### 1.2 第 4 条门槛是踩出来的，不是想出来的

第 4 条是踩出来的，不是想出来的。`agent/c1-kinetic-c` 于 `2026-11-17 09:45:27` 由 `branch: Created from origin/main` 建成，tip 就等于 `origin/main`，前三条全部通过——但它是一个活跃代理的落脚分支，删掉等于把人家的工作台抽掉。**只有“tip 在 main 里”这一条是不够的。**

同一类假阳性还有一次更极端的观测：这棵分支在 09:48 还有 worktree 检出，到 09:52 已经没有了。四分钟内“在用”和“不在用”翻转一次。

## 2. 快照

| 项 | 值 |
| --- | --- |
| 采集时间 | 2026-11-17T09:52:00+08:00 |
| `main` | `7f1eef8c`（与 `origin/main` 同） |
| ref 总数 | 33（本地分支 26 + 远端跟踪引用 7） |
| 链接 worktree | 20（另有主 checkout） |
| `refs/archive/*` | 78 条 |

**这张表有保鲜期。** 09:41→09:52 这十一分钟里，仓库自己变了三轮：新建 `agent/c1-kinetic-c`（09:45:27）、新建 `rubicon/521e25b2-c3d7`（09:45:40）、新建 `agent/ref-audit`、`agent/c2-catalog-align` 从 `7f1eef8c` 前进两次、`agent/observation-integrity` 从 0 提交变成 2 提交。**执行删除前必须整表重跑，不能拿任何一次快照直接批。**

## 3. 逐项盘点（33 条）

`未合并文件` = `git diff --name-only origin/main...<ref>` 的文件数；`未提交` = 该 worktree 里 `git status --porcelain` 的行数。

| ref | 类型 | tip | 在 main | 未合并提交 | 未合并文件 | 活跃 worktree | 未提交 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `agent/c1-batch8-small-kinetic` | 本地 | `97c22ccc` | 否 | 5 | 38 | 有 | 0 |
| `agent/c1-collisions` | 本地 | `0b11a6f3` | 否 | 1 | 12 | 有 | 0 |
| `agent/c1-collisions-b` | 本地 | `dd8612e3` | 否 | 3 | 23 | 有 | 0 |
| `agent/c1-em` | 本地 | `ec0f2ada` | 否 | 1 | 28 | 有 | 0 |
| `agent/c1-eq2` | 本地 | `f64d0eb2` | 否 | 3 | 19 | 有 | 0 |
| `agent/c1-equilibrium` | 本地 | `6aee90bf` | 否 | 2 | 24 | 有 | 0 |
| `agent/c1-field` | 本地 | `7d8e9264` | 是 | 0 | – | 无 | – |
| `agent/c1-geom` | 本地 | `1825bc64` | 否 | 1 | 21 | 有 | 0 |
| `agent/c1-geometry` | 本地 | `5107a32c` | 否 | 6 | 23 | 有 | 0 |
| `agent/c1-kinetic` | 本地 | `429904fc` | 否 | 5 | 4 | 有 | 0 |
| `agent/c1-kinetic-b` | 本地 | `f3bdbfb6` | 是 | 0 | – | 无 | – |
| `agent/c1-kinetic-c` | 本地 | `7f1eef8c` | 是 | 0 | – | 无 | – |
| `agent/c1-neutrals` | 本地 | `f62de76a` | 否 | 4 | 12 | 有 | 0 |
| `agent/c1-sampling` | 本地 | `98fe293f` | 否 | 1 | 19 | 有 | 0 |
| `agent/c2-catalog-align` | 本地 | `459506e8` | 否 | 2 | 39 | 有 | 3 |
| `agent/c3-receipt` | 本地 | `7f1eef8c` | 是 | 0 | – | 有 | 9 |
| `agent/c5-package` | 本地 | `aa1c175e` | 否 | 1 | 11 | 无 | – |
| `agent/observation-integrity` | 本地 | `9871ae64` | 否 | 2 | 17 | 有 | 0 |
| `agent/ref-audit` | 本地 | `7f1eef8c` | 是 | 0 | – | 有 | 0 |
| `agent/rules-inrepo` | 本地 | `cded64c2` | 否 | 1 | 1 | 有 | 0 |
| `integration/batch4` | 本地 | `9d87786f` | 否 | 11 | 25 | 无 | – |
| `integration/reland` | 本地 | `a2980a84` | 否 | 68 | 0 | 有 | 0 |
| `main` | 基线 | `7f1eef8c` | 是 | 0 | – | 有 | 0 |
| `origin/main` | 基线 | `7f1eef8c` | 是 | 0 | – | 无 | – |
| `rubicon/35cd7646-012f` | rubicon | `6a3068d8` | 否 | 52 | 30 | 有 | 0 |
| `rubicon/521e25b2-c3d7` | rubicon | `7f1eef8c` | 是 | 0 | – | 有 | 0 |
| `rubicon/d0a5aef9-b55c` | rubicon | `7f1eef8c` | 是 | 0 | – | 有 | 0 |
| `origin/agent/140-integration-and-cleanup-spec` | 远端 | `a5b24202` | 否 | 3 | 4 | 无 | – |
| `origin/agent/c1-batch8-small-kinetic` | 远端 | `97c22ccc` | 否 | 5 | 38 | 无 | – |
| `origin/agent/c1-coverage` | 远端 | `1ede90d2` | 否 | 2 | 2 | 无 | – |
| `origin/agent/hygiene-gate` | 远端 | `401c1b12` | 否 | 1 | 3 | 无 | – |
| `origin/agent/rules-inrepo` | 远端 | `cded64c2` | 否 | 1 | 1 | 无 | – |
| `origin/integration/reland` | 远端 | `a2980a84` | 否 | 68 | 0 | 无 | – |

## 4. 判定

### 4.1 可删（2）

| ref | 依据 |
| --- | --- |
| `agent/c1-field` | `--is-ancestor` 为真；无 worktree 检出；未提交 0；reflog 显示 02:37 建立，不是新建空壳。它原本是 C1 的工作分支，工作树后来切到 `rubicon/35cd7646-012f`，于是留下一个指向 `main` 的空指针。 |
| `agent/c1-kinetic-b` | 同上，05:57 建立；工作树后来切到 `rubicon/d0a5aef9-b55c`。 |

两者都只删**本地分支引用**，不涉及任何 worktree 目录、不涉及远端。

### 4.2 待确认（6）

| ref | 为什么要问 |
| --- | --- |
| `agent/c1-kinetic-c` | 满足前三条判据，但 09:45:27 才建立，是活跃代理的落脚分支（第 4 条闸门）。**默认不删。** |
| `agent/c3-receipt` | tip 在 main 里，但工作区有 9 处未提交改动。 |
| `agent/ref-audit` | tip 在 main 里，工作树干净，但它是这一轮新出现的分支，所有权未确认。 |
| `rubicon/521e25b2-c3d7` | tip 在 main 里，但它是本会话创建的 Rubicon checkpoint 分支且正被检出。 |
| `rubicon/d0a5aef9-b55c` | 同上。 |
| `integration/reland` / `origin/integration/reland` | 68 个提交、**零文件差异**（内容已全部在 `main` 里）。删它不丢内容、只丢 68 条 merge/checkpoint 历史。历史要不要留由维护者在结项最后决定，本轮保留。 |

### 4.3 保留（未合并，21）

全部按第 1 条默认保留。未进 `main` 的内容摘要：

- `agent/c1-collisions`（1）`test(collisions): audit A/D evidence with precision budgets and channel mapping`
- `agent/c1-collisions-b`（3）B/C 资产结构证据、六个 `Raises` 段声明 `ApplicabilityWarning`、验收读 `Warns`
- `agent/c1-em`（1）十七份电磁与场线合同的证据
- `agent/c1-eq2`（3）平衡四份解析恒等式、余下四份证据 + 变异插件盲区工单、`free-boundary` 的 scope 措辞
- `agent/c1-equilibrium`（2）平衡+镜域两批、十一份精确算术证据
- `agent/c1-geom`（1）几何/中性粒子剩余十三份证据
- `agent/c1-geometry`（6）轴对称映射与支撑链、七条坐标约定判决、体积/剖面交接/线平均
- `agent/c1-kinetic`（5）`integration_mesh` 语义与 hilbert 合同、逐变异判定与阳性对照、近奇异分支不可达 + 工单改名、撤回不可达断言
- `agent/c1-neutrals`（4）B5 跨网格/网格/停能证据、六份合同与本篇 reader、撤回错误的种子阈值论证并钉住反例、两张 scope 工单
- `agent/c1-sampling`（1）十四份采样合同证据
- `agent/c1-batch8-small-kinetic`（5，两端同头）小域九份 + 碰撞四份 + 三份推断 + pairing 重建
- `agent/c2-catalog-align`（2）C2 ID 域对齐（非均匀导数等），工作区另有 3 处未提交
- `agent/c5-package`（1）真实交付包的打包回执 + 三个消费者任务 + 分级缺口清单。**其 `examples/c5-delivery-acceptance` 子树与 `main` 逐字节相同**（tree `83cf5e57…`），属“内容已进 main、只有提交历史在外”的历史候选；按判据仍保留。
- `agent/rules-inrepo`（1，两端同头）把变异与单文件合并规则写进仓库
- `agent/observation-integrity`（2）让“失败丢掉 stderr”可被机械拦下、ratchet 从 14 处清到 2 处。**`AGENTS.md` 第 7 条的载体，未合并，故第 7 条尚未生效。**
- `integration/batch4`（11）kinetic + geometry 批次的集成分支，含 pairing 重建
- `rubicon/35cd7646-012f`（52）51 条是 `checkpoint: N file(s)`，唯一实质内容已被 `integration/reland` 的 merge 收下；`Rubicon-Status: active`，在途轮次不动
- `origin/agent/c1-coverage`（2）覆盖报告工具与显式测试范围

## 5. 受保护项

### 5.1 四个受保护 issue

| issue | 是什么 | 保护对象 |
| --- | --- | --- |
| #140 | 两份规格稿（CodeFusion 接入方案 + 清理门禁规格） | 父单，产物落在 #144 |
| #141 | 最小切片验收对照表（六种失败情形 × 状态词） | 只有对照表，无代码、无分支 |
| #142 | `hygiene`/`prune` 清理门禁实现 | **`origin/agent/hygiene-gate`**（`401c1b12`） |
| #144 | `Closes #140`，两份文档 + 最小切片参考程序 | **`origin/agent/140-integration-and-cleanup-spec`**（`a5b24202`） |

两条远端分支**永久保留**：它们承载着他人未合并的 PR，删远端分支等于替别人关 PR。这条在仓库内已有独立记载（运行产物账本 `.runtime/RETIREMENT.md`），本计划只是把它写进被跟踪文件。

### 5.2 两个被排除的 worktree：已经从“目录”退化成“分支身份”

**来历。** 排除名单不在 #140–#144 的正文里——`gh issue view` 四张单的正文一次都没提 worktree。它记在 **#121（资源账本）的评论**里，并反复出现：

- `.worktrees/hygiene-gate`（分支 `agent/hygiene-gate`，HEAD `2ac20abf` → `401c1b12`），**owner：项目总控，冻结不合不扩不删**；
- `.worktrees/spec-integration`（分支 `agent/140-integration-and-cleanup-spec`），PR 合并后随合并一并清理；
- 之后的评论反复写「另两棵 hygiene-gate、spec-integration 及 #140/#141/#142/#144 按明确排除范围保持原状」「当前只留主 checkout 和明示排除的 hygiene-gate/spec-integration」。

**当前状态。** 这两棵目录**已经不在盘上**：`git worktree list --porcelain` 与 `.worktrees/` 目录列表都不含它们，且两者的差集为空（`.worktrees/` 下没有未登记目录）。所以排除范围**从“目录”退化为“分支身份”**：

> 排除规则改写为：`origin/agent/hygiene-gate` 与 `origin/agent/140-integration-and-cleanup-spec` 两条远端分支永久保留，无论本地是否存在同名目录或分支。

**下次再查别走弯路。** 找这两个名字时，`git grep` 在全部被跟踪文件里对「排除树」「两棵」零命中；#249 的评论里有 12 次「两棵指定排除工作树」，但一次都没写出名字。名字只在 #121 的评论里。

## 6. `refs/archive/*` 建议

**本轮不新增任何 `refs/archive/*`。**

理由：可删的两条 ref 的 tip 已完整存在于 `origin/main`，删掉不丢任何提交对象；真正会丢历史的两个（`rubicon/35cd7646-012f` 的 52 条 checkpoint、`integration/reland` 的 68 条 merge）都在保留列。现有 78 条 archive 引用在运行产物账本里已有各自的消费者与退役条件，与本轮无关。

只有一种情况会改变这个结论：未来决定删掉 `integration/reland` 而那 68 条历史仍有人要引用。届时存档建议按 `.runtime/RETIREMENT.md` 既有格式写清**消费者**与**退役条件**，两者缺一不存档。

## 7. 执行流程

分两段，中间必须人工过目：

1. **重跑判定。** 按第 3 节的命令重新生成整表；任何一行与本节快照不一致，以新表为准并重写判定。
2. **逐条核对解析后的绝对路径。** 对每个待删 ref，先解析出它对应的本地路径，确认落在本仓库内、且不是主 checkout。
3. **单条删除。** 一条一条删，不用通配符、不批量。
4. **读回。** 删后重跑 `git worktree list`、`git branch -vv`、`git merge-base --is-ancestor` 与 `git rev-parse origin/main`，确认 `main` 未变、两条受保护远端分支仍在、其余 ref 未受影响。

复测命令（都在仓库根运行）：

```sh
git fetch --all --prune
git worktree list
git branch -vv
git merge-base --is-ancestor <ref> origin/main && echo in-main
git rev-list --count origin/main..<ref>
git diff --name-only origin/main...<ref>
git --no-optional-locks -C <worktree> status --porcelain
git reflog show --date=iso <ref>
```

## 8. 本计划不覆盖的范围

- **不动远端分支。** 除第 5 节两条受保护分支（也不动）外，其余远端分支各有未合并提交，删它们要先决定那些提交的去向。
- **不动 `rubicon/*`。** 只要 `Rubicon-Status: active`，就是别人的在途轮次。
- **不动任何 worktree 目录。** 本轮"可删"结果里没有一棵 worktree。
- **不动容器卷、receipt、stash。** 那些在 #121 的资源账本里有独立处置线。
- **不推 `main`、不合并、不 rebase 他人分支。**
