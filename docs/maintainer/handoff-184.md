# 交接文档（#184）

写给接手这个仓库的维护者。**这份文档不依赖聊天记录、私人笔记或某台机器的路径。** 读完它，你应该知道仓库现在是什么状态、哪些规则一碰就付代价、哪些事情被明确冻结、以及下一步从哪儿接。

配套文档：[资源回收计划](resource-recovery-plan.md)。项目规则见 [AGENTS.md](../../AGENTS.md)、[RULES.md](../../RULES.md)、[ARCHITECTURE.md](../../ARCHITECTURE.md)。

## 1. 仓库现在是什么状态

**易漂移的数字不复制到这里。** 当前合同数、`main` revision、选中与通过的测试计数，统一记在 `docs/maintainer/status.md`（该文件由独立维护线建立；本仓库的口径是"同一事实只写一处"）。本节只保留读下面几节所必需的语境，并且标明是写作时的快照——**要数字就去 status.md，不要引用本节**。

| 项 | 值 |
| --- | --- |
| 数字真源 | `docs/maintainer/status.md`（合同数、`main` revision、测试计数） |
| 写作时快照 | `main` = `7f1eef8c`，`catalog/examples/*.json` 249 份（**快照，见 status.md**） |
| 解释器 | 由 `.python-version` 固定，依赖由 `uv.lock` 固定，装进项目目录内由 uv 管理 |

### 验收怎么跑

```sh
python3 scripts/dev.py prepare   # 首次
python3 scripts/dev.py check     # 验收；默认就是发布档
```

**发布档 vs 开发档，区别必须记住：**

- `python3 scripts/dev.py check` 是**发布档**（默认 stage），全部步骤都跑：tests、contracts and examples、contract sync、hazard 扫描、文档构建、lint、format、lockfile、wheel 构建、wheel 暴露（步骤清单以 `scripts/check_all.py` 为准，不在本文件复述）。
- `python3 scripts/dev.py check --stage dev` 是同一张计划表的**开发档**：跳过文档构建、wheel 构建、wheel 暴露和示例执行，并按 `skills/development/scirel-acceptance/release_only_tests.txt` deselect 发布级测试。它证明"这批改动没破坏别处"，**不**证明打包产物可安装、文档站可构建、示例可执行。

**开发档回执不得当作发布证据引用。** `validate_extraction_package` 会拒绝 `stage=dev` 的回执，并要求在同一个候选上重跑发布档。合并进 `main` 的批次、任何对外交付声明，只能用发布档回执。

另外两条常被违反：

- 实现者自己跑的定向 `pytest`（域级、秒级）**不是任何一档的证据**，不进 PR 回执。
- 作放行依据的完整检查必须**独占**本仓库（含所有 worktree）的测试；PR 证据里要贴 `EXCLUSIVE` 那行。跑检查期间不要另起测试。

入口 skill：[scirel-acceptance](../../skills/development/scirel-acceptance/SKILL.md)。

## 2. 两条最容易违反、代价最大的规则

### 2.1 真值链：证据 → 代码 → 合同 → 文档

[AGENTS.md](../../AGENTS.md)「必须遵守」第 1 条。代码之所以是对的，只因为**证据**支持它——已发表文献、被拆解项目的实际行为、物理正确性、解析恒等式。合同是代码的衍生品，文档是合同的衍生品。三条箭头各有各的失败模式，**不要混**：

- **合同与代码不符 → 合同错了。** 以代码的**实际行为**改写合同，不留两个版本。这一步只解决"合同没写对"，**不构成"代码是对的"的证据**。
- **代码与证据不符 → 代码错了。** 开工单、按安全默认处理（行为不动、`known_limitations` 记录、等人工裁决），**不得**把错误行为写进合同让它变成"已声明"。
- **证据拿不到 → 如实记 `cannot establish`** 并写清卡点。缺失的证据不能当证据；"测试钉住了当前行为"或"与另一实现一致"都不等于正确性证据。

自查一句话：*这条合同说法背后，是证据，还是只是代码现在的样子？*

### 2.2 观测必须可判别：现在成立的部分，和合并后才成立的部分

**现在成立（已合并进 `main`）**：变异验证里"变异存活"有四种互不相同的判定，混用会得出方向相反的结论，修法也相反——见 [scirel-acceptance](../../skills/development/scirel-acceptance/SKILL.md) 的「变异验证：先说清"走没走到"，再说"红不红"」一节：

| 判定 | 含义 | 修法 |
| --- | --- | --- |
| `covered` | 已证明执行、测试仍全绿 | 加强断言 |
| `not-exercised` | 现有测试没覆盖该分支 | 补覆盖 |
| `equivalent` | 改动语义等价，任何测试都杀不死 | 用代码阅读证明两条路径等价，并指出可删的重复守卫 |
| `UNKNOWN` | 插桩失败、副本崩溃、标记不可读 | 不作任何结论 |

其中 `not-exercised` **不得**升级为"该分支不可达"——连续参数空间上的不可达性无法用采样证明。本仓库曾因此误判，差点按"死代码"删掉一段正确的可去奇点极限实现。

**合并后才成立（尚未进 `main`）**：`AGENTS.md` 将新增第 7 条「观测必须可判别：通过 / 失败 / 未观测是三态」，配套审计见 `docs/maintainer/observation-integrity.md`（**合并后生效**）。它的载体是分支 `agent/observation-integrity`（当前 2 个提交、17 个文件、未合并）：让"失败丢掉 stderr"成为可被机械拦下的缺陷，并把 ratchet 从 14 处清到 2 处。**在看到那条分支合进 `main` 之前，不要按第 7 条验收任何东西**——引用一条不存在的规则，和引用一份开发档回执当发布证据是同一种错误。

## 3. 能力边界：明确不做什么

这一节不重复罗列——边界已单列成持久页 [能力边界](capability-boundaries.md)，那里的四条带可复现命令与合同事实，并区分「我们选择不提供」与「包内根本没有」两类。


## 4. 未决事项：全部 open 工单

`python3 scripts/tickets.py list tickets --status open` 实测 **9 张**（**快照，见 status.md**；数量会变，判定以命令输出为准），全部 `open`，`decisions` 均为空。**它们没有被裁决。** 每张单的 `reviewers_required` 与安全默认写在工单头，不要凭印象。

| id | 类别 | 卡什么 | 需要谁裁决 |
| --- | --- | --- | --- |
| [T-2026-0001](../../tickets/convention/T-2026-0001.md) | convention | 中性氢 p–H 动量交换该怎么组合两个碰撞项，才不重复计入共振电荷交换的动量 | 物理专业审核人 |
| [T-2026-0002](../../tickets/convention/T-2026-0002.md) | convention | `build_basis`/`BasisMatrix` 的失败通道与 api-spec 不一致：改实现去对齐，还是把合同口径定为当前实现 | 评审方（2 名） |
| [T-2026-0005](../../tickets/convention/T-2026-0005.md) | convention | `scirel.geometry` 同一点族存在两套角度单位（属性弧度、构造器度），相差 180/π 且不告警 | 维护者 |
| [T-2026-0600](../../tickets/physics-dispute/T-2026-0600.md) | physics-dispute | `vp_distribution` 把 Lorentzian 平衡态的返回称作 "the exact root"，该措辞应撤回；按实现自己的线性化约定根不是这一对值 | 物理专业审核人 |
| [T-2026-0003](../../tickets/scope/T-2026-0003.md) | scope | 合同点名的两个异常类型不在公开命名空间里：纳入导出面，还是把承诺降为"只承诺 `ValueError`" | 维护者 |
| [T-2026-0004](../../tickets/scope/T-2026-0004.md) | scope | 初版不可达论证已被反例推翻，本单为说明性记录；两份中性粒子合同已撤回错误说法 | 2 名评审 |
| [T-2026-0100](../../tickets/scope/T-2026-0100.md) | scope | 广义 Hilbert 近奇异替换的覆盖已补、变异已由存活转杀死，只剩行内标注问题待裁决 | 2 名评审 |
| [T-2026-0800](../../tickets/scope/T-2026-0800.md) | scope | 电荷交换速率系数在高能支把 `energy_ev` 当束速度，但合同与 docstring 从未写明；语义要不要显式化 | 2 名评审 |
| [T-2026-0905](../../tickets/scope/T-2026-0905.md) | scope | 变异插件改不动返回 frozen dataclass 的公开函数，这类资产的"变异存活"结论无效，此后怎么取得判定 | 维护者 |

工单协议见 [tickets/README.md](../../tickets/README.md) 与 [supply-pipeline.md](supply-pipeline.md) 第 7 节。

## 5. 能力冻结

**暂停接收新资产，供给线的准入随之中止，先还债、先清理。解除条件由维护者另行决定。**（[AGENTS.md](../../AGENTS.md)「当前状态」末段）

冻结期内：

- 不新增资产、不增加新科学 method、不在结项过程中顺手解冻；
- 拆解线（#184 所属的 M4）只检验方法与交接是否有效，**不新增能力**；
- 新公开名字、改符号、改单位这类动作都要人工批准。

## 6. 常见陷阱（都有代价记录）

### 6.1 单文件多记录必须逐条并集，不许整份取一侧

`tools/docs/zh/*.json` 一个文件里有几十条资产记录，代码与合同的并行改动都落在同一个文件上，冲突几乎必然发生。解决这类冲突**不许 `git checkout --theirs <file>`**：那会把对方在这批里新增的记录整段退回旧文本，而差异不会出现在任何代码里——只有 `check_contract_sync.py` 的"条款条数不符"能看出来。本仓库已因此静默退回两次（一次 45 条 reader 记录，一次 3 条）。

正确做法：按 `asset_id` 合并两侧记录，只让本批真正改过的资产采用本侧版本；合并后跑 `check_contract_sync.py`，并逐条比对与 `origin/main` 的差异，确认差集恰好是本批改过的那几条。

### 6.2 各 `zh_*.json` 的缩进不同，别顺手格式化

这些文件并非统一缩进：`zh_axisymmetric_models.json` 用两空格，其余多数用一空格。用统一缩进重写前者会产生两千多行与内容无关的假 diff，审查时分不清真实改动。**改写前先看该文件自己的格式。**

### 6.3 检查脚本读工作树，测量前先对齐

`scripts/c1_evidence_coverage.py`、`scripts/validate_asset_documents.py`、`scripts/check_contract_sync.py` 读的是**当前工作树里的文件**，不是 `origin/main` 的树。所以"对着 ref 树验证"这条规则在**读检查器输出时**要前移一步：先 `git reset --hard origin/main`（或在刚从 `origin/main` 开出的 worktree 里）再测。

代价实例：主 checkout 落后 5 个提交时跑覆盖工具，得到 `neither` 从 69 回到 85 的"回归"，一度被当成合并丢失内容——同一错误在同一会话里犯了三次。判据：**当测量结果与预期方向相反时，先怀疑测量起点，再怀疑改动。**

反过来，判断某份改动是否真进了 `main`，只能用 `main` 的树：`git ls-tree -r --name-only origin/main -- <path>`、`git show origin/main:<path>`，**不能**用工作树里的 `ls`／`grep`／`pytest`。

### 6.4 交付包用 `validate_installed_wheel`，extraction kit 才用 `validate_extraction_package.py`

两者校验对象不同，用错会把一个通过的报告当成另一个对象的证据。装好后的 wheel 用 `scripts/validate_installed_wheel.py`；拆解包（extraction kit）用 `scripts/validate_extraction_package.py <package> --repo .`，且必须经 `python3 scripts/dev.py run --exclusive` 运行——`--repo` 与候选必须属于被锁住的同一 clone。

### 6.5 文档测试的 oracle 不由改写合同的同一方重建

`tools/docs/zh-pairing.json` 是中英配对测试的 oracle。让改合同的同一方顺手重建它，等于让被告自己写判决书：哈希永远是"最新"的，配对门永远是绿的，而它本来要抓的错就在同一批改动里。由集成侧统一跑 `scripts/zh_pairs.py --write`，代理一律不跑、不提交 sidecar。

### 6.6 判据本身会给出假阳性：新建的空分支看起来"可删"

按"tip 已在 `origin/main` 里 + 无未提交"判断可删，会把别人刚建好的落脚分支算进去。实例：`agent/c1-kinetic-c` 于 `2026-11-17 09:45:27` 由 `branch: Created from origin/main` 建成，tip 就等于 `origin/main`，判据为真——但它是活跃代理的工作台。同一棵分支在 09:48 还有 worktree 检出，09:52 就没有了：**四分钟内"在用"和"不在用"翻转一次**。

所以判据必须多一条闸门"**且不属于任何活跃 worktree，且不是刚建的落脚分支**"。完整的判定表与执行流程见[资源回收计划](resource-recovery-plan.md)。

### 6.7 任何一次快照都有保鲜期

`2026-11-17 09:41 → 09:52` 这十一分钟里，仓库自己变了三轮：新建 `agent/c1-kinetic-c`、新建 `rubicon/521e25b2-c3d7`、新建 `agent/ref-audit`，`agent/c2-catalog-align` 前进两次且工作区有 3 处未提交，`agent/observation-integrity` 从 0 提交变成 2 提交。

这正是 6.6 与"观测三态"要治的同一类病：**表是某一刻的观测值，不是事实的常驻形态。** 执行任何删除或清理前必须整表重跑，不能拿任何一次快照直接批。

## 7. 怎么继续 C1 剩余的 kinetic 部分

C1 的目标是给公开合同补承重证据。kinetic 域还没做完，剩两批：**B5**（fluid 谱求解器与特征值，矩阵恒等式与残差）与 **B6**（spectral / dielectric / kinetic-wavevector / 其余）。**剩余份数见 status.md**（写作时快照：B5 11 份、B6 13 份，合计 24 份）。

做法：

1. 先读 [scirel-acceptance](../../skills/development/scirel-acceptance/SKILL.md)，特别是「变异验证」与「证据测试自身的三个陷阱」两节。证据测试通过并不表示它检验了它声称要检验的东西。
2. B5 的参考装置在 [`tests/kinetic/_fluid_pencil_reference.py`](../../tests/kinetic/_fluid_pencil_reference.py)：流体谱的铅笔矩阵参考实现，供矩阵恒等式与残差对照使用。先读它，再决定每份资产的判别式。
3. 每份资产的证据要能回答三件事：一般情形、上下界、适用的退化/失败/组合情形；求解器类补残差、收敛与制造解。只验证单点或"能返回结果"不算证据。
4. 覆盖读数 `neither` 是**合同文本缺口**，不是"这份资产没证据"；`basis` 是**下界**。两者都不能当科学工作完成度来报。
5. 合同同步（`tools/docs/zh/*.json` 与 `zh-pairing.json`）按 6.1/6.5 处理：逐条并集，sidecar 由集成侧统一重建。

## 8. 接手第一周建议顺序

1. 跑一次 `python3 scripts/dev.py check`，确认真实基线是绿的（记下 `EXCLUSIVE` 行与 pytest 计数，别只记 `ALL GREEN`）。
2. 读 [资源回收计划](resource-recovery-plan.md)，把那份快照重跑一遍——它一定已经过期。
3. 跑一次 `python3 scripts/tickets.py list tickets --status open`，挑出需要物理裁决的那几张排队，**不要**自己代填专家意见。
4. 再读 [codebase-map.md](codebase-map.md) 建立代码地图，然后接 C1 剩余批次（份数以 status.md 为准）。
