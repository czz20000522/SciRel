# 结项对账（二期）

**这一页只做一件事**：把「`main` 上实际有什么」与「还差什么」分开，并且每一行给出可复现的坐标。
它不解释为什么、不写叙事——那是 [为什么与怎么做](why-and-how.md) 的事。

引用任何数字时请连同 revision 一起引用。本页的 revision 见 [状态快照](status.md) 的测量块。

## 1 已在 `main` 上成立

| 项 | 证据坐标（在仓库根执行） | 实测 |
| --- | --- | --- |
| 公开合同数 | `ls catalog/examples/scirel.*.json \| wc -l` | 见下方命令输出 |
| 合同 ID 域与规范模块域一致 | `python3 scripts/check_catalog_id_domain.py` | `0 mismatches, 0 errors` |
| 合同与中文字段/读本同步 | `skills/development/scirel-acceptance/scripts/check_contract_sync.py` | `0 problems`（assets 数由脚本打印） |
| 缩水下限已激活 | `skills/development/scirel-acceptance/anchors/release-*.json` 存在，发布档打印 `FLOOR at least …` | 锚点 **1** 份 |
| C4 独立消费者回执 | `examples/c4-usage-acceptance/round2/receipt.json` | 73/73 任务，**48 sufficient / 25 insufficient**，272 判据 `224 pass / 41 fail / 7 not-run` |
| C5 交付包收据 | `examples/c5-delivery-acceptance/receipt.json` | 存在；wheel sha256 与 `validate_installed_wheel` 记录在案 |
| C6 交接与回收计划 | `docs/maintainer/handoff-184.md`、`docs/maintainer/resource-recovery-plan.md` | 两份都在 |
| 能力边界单列 | `docs/maintainer/capability-boundaries.md` | 区分「选择不提供」/「包内根本没有」两类 |
| 观测三态规则 | `AGENTS.md` 第 7 条 + `docs/maintainer/observation-integrity.md` | 含判据写错的六种形态 |

## 2 **不在** `main` 上：kinetic 的证据工作

这是当前最大的一处偏差，必须写清楚：

```
$ python3 scripts/c1_evidence_coverage.py --format json
kinetic: 62 assets, basis 32, gap 22, either 22, neither 24
```

`main` 上 kinetic 仍有一批合同既没有记录证据、也没有记录缺口（数量由上面的命令给出）。而 B6 分支报的是一个明显更小的数。

**两者不矛盾，因为那份工作没合进来。** 它在这里：

```
$ git rev-list --count origin/main..rubicon/521e25b2-c3d7     # 75
$ git diff --name-only origin/main...rubicon/521e25b2-c3d7 | wc -l   # 35
$ git diff --name-only origin/main...rubicon/521e25b2-c3d7 | grep -c '^tests/kinetic'  # 10
```

75 个提交、35 个文件、其中 10 个在 `tests/kinetic/`。**在它合进 `main` 之前，C1 在 kinetic 上未完成**，
不能按分支报的那个数引用。

同理，`agent/c1-*` 那批分支（38 / 28 / 24 / 23 / 21 / 19 个文件）多数是**已 squash 合并后的残留指针**，
`git rev-list --count` 会把它们算成"领先"，但内容在 `main` 上。判断是否真的没合，看**内容**（例如
对应域的 `neither` 是否为 0），不要看领先提交数。

## 3 待人工裁决（无法由 agent 完成）

`python3 scripts/tickets.py list tickets --status open` 列出的每张单都需要物理审核人写 `decisions` /
`resolution`。**`main` 上 open 工单 12 张**，其中与结项直接相关的：

| 工单 | 要决定什么 | 不决定的后果（已执行的安全默认） |
| --- | --- | --- |
| `T-2026-1202` | `rational-solve-matrix` 声明 46 个输出、公开入口只返回 9 个 | 实现不动；合同不裁剪；消费者记 `cannot establish` |
| `T-2026-1200` | 族归属冲突（`outer_convergence` 是否为"方法专有容差"） | 不改族；审计记"该合族"但不动 |
| `T-2026-1201` | `helper_*` 出现在公开面的命名债 | 不改名；记为命名债 |
| `T-2026-0905` | （见工单正文） | 见工单 |

## 4 已知但**不打算在二期偿还**的（诚实边界）

见 [能力边界](capability-boundaries.md)。摘要：安全因子 `q` 与磁剪切、镜比与镜点、三维笛卡尔↔柱坐标、
平衡→镜域交接声明，四条包内根本没有；跨域组合另有单位/轴序/适配器三类系统性缺口
（C4 六条跨域任务全部不能只靠包完成）。

## 5 规格上的未完成项（不阻塞结项，但必须写出来）

| 项 | 现状 | 为什么不阻塞 |
| --- | --- | --- |
| 单输出合同的返回形状 | 已修 C4 点名的 23 条，**另有 115 份同类未修** | 已留痕（看板卡 `card-a65930d9`）并给出建议门禁；不影响已声明行为 |
| 合同 `dtype` 写法 | `float64 array` / `Python float` / `float64` / 类名四种混用 | 消费者用宽松匹配 + 逐项记录所见，不据此判红 |
| 变异账的 `not-exercised` | 若干资产仍有个别变异落在该档 | 按 `AGENTS.md` 第 7 条，它不被计入 `pass`；这是三态设计的目的 |

## 6 怎么用这一页

- **要判断某一项是否完成**：只看第 1 节的命令能不能跑出同样的结果。跑不出就不是完成。
- **要判断 C1**：看第 2 节，不看任何分支的自报数字。
- **要推进结项**：第 3 节需要人；第 5 节需要门禁决定；第 2 节需要一次大合并。
