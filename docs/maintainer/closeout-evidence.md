# 结项证据（#249 二期基础结项）

**状态页，不是规范页。** 这里每条都是「命令 → 当时的输出」，用来核对某一时点的主张是否成立。
它会随 `main` 漂移，所以**不要引用本文的数字**——要引用就重跑命令，数字以重跑为准。

- 测量时点：`main` @ `96a9c6ab3f69ee9df1fef566392827a319d6c9f3`
- **同一提交上**的发布档：`steps 10/10 passed`、`tests collected 9546 / passed 9533 / failed 0`、
  `RESULT SHA256 ec962bb45d1161263056f4663c0254d568603d4efeaeef70bfb4680c2cca6bbc`、
  `FLOOR  at least 9541 tests required by …/anchors/release-14aa664d4268.json`、
  `EXCLUSIVE  no other test run or check holds the clone lock`、`ALL GREEN`
- 该次回执导出为 `release-96a9c6ab3f69.json`；`verify` 与回执对账为 `agree`

> 页首的 revision 与回执 SHA 会过时，但**不会悄悄错**：`tests/tooling/test_closeout_evidence_citations.py`
> 要求正文提到的每个锚点文件真实存在、且当前提供 release 下限的锚点必须被正文提到。

## 0 能力边界

```sh
sed -n '1,40p' docs/maintainer/capability-boundaries.md
```
**输出要点**：把「我们选择不提供」与「包内根本没有」分开。前者找不到入口就知道了；后者经常不报错，
你手上有一个看起来正确的数。这一步没有可机读的判据，它是文档，判据在第 1~5 节。

## 1 全量能力科学与数值核验（C1）

```sh
PYTHONPATH=src python -B scripts/c1_evidence_coverage.py --format json
```
```json
{"basis": 206, "gap": 116, "either": 249, "neither": 0}
```

读法，三点都不能省：
- **`neither 0` 是这份脚本的结论**：249 份合同**每一份**都在文本里交代了依据或缺口。
- **`either 249`** 是 `basis + gap` 的并集标识，不是「249 份都验过」。
- **`gap 116` 是已记录的缺口**，不是未观测，也不是通过。缺口内容在各合同 `known_limitations` /
  `evidence_ceiling` 与工单里。

## 2 已批准架构/API 整理（C2）

```sh
python -B scripts/check_catalog_id_domain.py
python -B scripts/check_output_channel_declaration.py
```

两条都必须以 `0 mismatches` / `0 errors` 与 `all state their channel` 结尾；**把资产数抄进文档是不允许的**
（`test_catalog_size_is_not_hand_written_into_documents` 会拦，规模会漂），所以这里只写判据不写数字。

合同总数同理，用命令查，不要抄：

```sh
git ls-files 'catalog/examples/scirel.*.json' | wc -l
git ls-files 'catalog/review/examples/*.json' | wc -l
```

**基线内条目数 是尚未偿还的债**，`tools/docs/output-channel-baseline.json` 里逐条带 `reason`，
只减不增（新出现的沉默合同判红；条目已修好但没删也判红）。

## 3 逐项测试身份（C3）

```sh
PYTHONPATH=src python -B -c "
import sys; sys.path.insert(0,'skills/development/scirel-acceptance/scripts')
from check_all import selection_floor; f=selection_floor('release'); print(f.selected, f.anchor)"
```
```
<selected> skills/development/scirel-acceptance/anchors/<floor-anchor>.json
```

**不要照抄这两个占位符**：`<selected>` 与 `<floor-anchor>` 都会随新锚点变化。判据是"输出里那三个阶段
必须与命令一致"，不是"数字等于本文写的"。本文早先在这里写死过一份锚点名，新锚点落地后就变成了
**数对、出处错**——所以现在留占位符，并有一条测试盯着正文提到的每个锚点文件必须真实存在。

锚点与回执对账（必须 `agree`）：
```sh
python3 scripts/dev.py run python -B \
  skills/development/scirel-acceptance/scripts/acceptance_anchor.py verify \
  skills/development/scirel-acceptance/anchors/release-da4c039f44eb.json \
  .runtime/logs/check-<id>/result.json
```
```
AGREEMENT  agree  (25 fields; 9541 tests); provenance verified_v2
```

同一命令对**另一个 revision 的回执**必须 `disagree`——否则它没有分辨力。实测旧锚点对本次回执
`MISMATCH (8 of 25 fields)`，符合预期。

## 4 独立消费者完成任务（C4）

```sh
python3 -c "import json;d=json.load(open('examples/c4-usage-acceptance/closeout/receipt.json'));
print(d['summary']);print(d['diff_vs_round2']['criteria_changed'])"
```
```
{'tasks': 73, 'package_sufficient': 48, 'package_insufficient': 25,
 'criteria_total': 272, 'criteria_pass': 225, 'criteria_fail': 40, 'criteria_not_run': 7}
[{'task': 'physics-coulomb-logarithms', 'criterion': 'fields', 'round2': 'fail', 'closeout': 'pass'}]
```

**这个 diff 有因果解释力**，因为 `closeout/checks/` 与 `round2/checks/` 是逐字节副本：
判据状态若变化，不可能来自装置，只能来自库/合同。实测 1 条改善、**0 条反向变差、0 处数值变化**。

`25 package_insufficient` 是**消费侧的未完成项**，不是库的缺陷——其中 119 份合同不声明返回通道
（见第 2 节基线）是最主要的一条。

## 5 交付包一致（C5）

**先分清两个「包」，它们的覆盖面不同：**

| 包 | 装什么 | 谁验 |
| --- | --- | --- |
| **wheel** | **只有** `scirel` 包（`pyproject.toml` 的 `include = ["scirel", "scirel.*"]`）。**不含 catalog、不含 skill** | 发布档的 `wheel build` 与 `wheel exposure` 两个步骤 |
| **交付包（delivery bundle）** | wheel + 合同 + `skills/development/usage/` 三个 skill + 检索运行时 | `scripts/build_pure_delivery.py`，产物见 `examples/c5-delivery-acceptance/receipt.json` |

**"三个 skill 在实际新包里"说的是后者。** 说 wheel 里含 skill 是错的——wheel 只装 Python。

交付包这条路的保障是**失败即中止**，不是"跑完再说"：

```sh
grep -n "missing delivery skill" scripts/build_pure_delivery.py
# 161: raise ValueError("missing delivery skill: " + str(skill_root))
```

任何一个 `SKILL_NAMES` 目录不存在，构建直接抛错，不会产出一个少一个 skill 的包。

### 一处必须写明的覆盖缺口

**发布档不重建交付包。** 它构建 wheel、检查 wheel 暴露、构建文档站、跑合同与示例，但不跑
`build_pure_delivery.py`。所以：

- 改 `skills/development/usage/` 会按 `AGENTS.md` 的分档规则触发发布档（因为它们进交付包），
- 但发布档本身**不验证**交付包内容与仓库一致；
- 那条一致性只在 `examples/c5-delivery-acceptance/receipt.json` 里验过一次，**不会随每次改动重跑**。

这不影响"这批改动没破坏别处"，但它意味着**交付包一致性是一个按需验证的结论，不是一个每次门禁都重新成立的结论**。
把它读成后者，就是又一次"看起来存在"。

## 6 拆解与交接、资源回收（C6）

```sh
git worktree list | wc -l          # 1
git for-each-ref --format='%(refname:short)' refs/heads    # integration/reland  main
git for-each-ref --format='%(refname)' refs/archive | wc -l # 110
```

回收规则与执行记录见 `resource-recovery-plan.md` 第 7、8 节。**一条限度**：`refs/archive/*` 只有本地
意义，不随 `git push` 传播——它保护的是这个 clone。

## 未完成项（必须与上面的绿并列阅读）

| 项 | 状态 |
| --- | --- |
| 人工裁决工单 | **13 张 `status: open`**，各自已按安全默认处理（行为不动、缺口入合同） |
| 单输出合同返回通道 | **92 份仍在基线内**，未修 |
| C4 消费侧 | **25/73 任务 `package_insufficient`** |
| C1 缺口 | **116 份合同记录了缺口**而非证据 |
| `refs/archive/*` 远端化 | 未做（共享状态变更，留维护者决定） |

## 复跑全部证据

```sh
python3 scripts/dev.py check          # 发布档，持独占锁，约 12 分钟
PYTHONPATH=src python -B scripts/c1_evidence_coverage.py
python -B scripts/check_catalog_id_domain.py
python -B scripts/check_output_channel_declaration.py
python -B scripts/check_observation_integrity.py
python3 scripts/tickets.py list tickets --status open
```

## 2026-11-18 复验（`main` @ `e041e66a`）

补记，不改上面的历史测量：那一节记录的是 `96a9c6ab` 上的读数，改写它等于伪造一次没做过的运行。

**本文不抄写规模数字。** 合同份数、基线剩余、工单张数都会随提交变化，抄进文档就必然过期——
仓库为此有 `test_catalog_size_is_not_hand_written_into_documents`。要数字就跑下面的命令。

```sh
python -B scripts/check_observation_integrity.py
# observation integrity: no silent failure anywhere; the ratchet is empty
#   -> C6 观测完整性仍成立

git worktree list | wc -l          # 1  （只剩主 checkout）
git branch --list | wc -l          # 1  （只剩 main）
git for-each-ref refs/archive | wc -l   # 110
# 每个归档 ref 都能解析到存在的 commit（`git rev-parse --verify <ref>^{commit}`，0 个失败）

python -B scripts/check_output_channel_declaration.py
# 剩余基线条目数见输出；本轮的类别构成：映射型等 T-2026-1203，另有两份被章节证据绑定

python -B scripts/check_evidence_basis.py
# 每份公开合同都已声明 verification.basis，基线为空

python -B scripts/objective_status.py
# pass / pass / pass / not-observed（第四条是 PR 回执，树里看不见，脚本拒绝自评）

python scripts/tickets.py ledger tickets
# 每张 open 工单都有 decision_owner 与「不决定的后果」；缺即非零退出
```

与前一次的差异，按类别说而不是按数量说：

| 项 | `96a9c6ab` | `e041e66a` |
|---|---|---|
| 单输出合同返回通道 | 全部留在基线内，未分类 | 绝大多数已写明来源（探测实测或读示例判定）；**只剩两类**：映射型等 `T-2026-1203`，以及被章节执行证据绑定的两份 |
| 工单归属 | 无字段，靠人记 | 全部有 `decision_owner`，`tickets.py ledger` 可查且缺即非零退出 |
| 工作树 / 本地分支 | 6 / 7 | 1 / 1（已合入的分支按 patch-id 确认后删除，tip 未被归档 ref 覆盖前不删） |
| 规则盘点 | 无 `catalog-evidence-1` | 含该条，且每条判据都被计划接线 |

剩下两类通道债务为什么不能顺手做完：映射型要先定「合同是否必须枚举映射键集」（`T-2026-1203`）；
被绑定的那两份，改一个字节就让磁静力学章节「真的跑过」的证据失效，刷新它必须重跑章节示例
（需要构建 wheel）。

### 这一版的发布档：**已补跑**（`main` @ `4515d8ed`）

过程中按维护者指示用 dev 档作合并门槛省时间，因此有一段时间改动没经发布档验证。
结项前在干净提交上补跑了一次，回执：

```
EXCLUSIVE  no other test run or check holds the clone lock
FLOOR  at least 9546 tests required by skills/development/scirel-acceptance/anchors/release-96a9c6ab3f69.json
steps 10/10 passed; tests collected 9678, selected 9678, deselected 0, passed 9636, failed 0, error 0
RESULT SHA256 4d3e06003fd3792bc7e1c431581006a856a623c07e1fd469d98f87a3971f2b94
ALL GREEN
```

`deselected 0` 是关键：发布档把 `release_only_tests.txt` 里的测试全跑了，包括交付包与 wheel 那几条
（构建 wheel、装进独立环境、消费导出目录与三个 skill）。这补齐了本页 5 节里"发布档不重建交付包"
留下的空白——**制品侧这次是真的验过，不是按需推断**。

四条 `NOT_RUN: set SCIREL_MCP_PYTHON to an isolated official MCP SDK interpreter` 仍然存在，
是环境缺隔离解释器的已知跳过，不是通过。同理三条 `platform longdouble` 与一条 Windows 遍历是平台限制。

**这一条提交之后的改动只有本页文档**（`docs/maintainer/` 不进文档站），因此该回执对代码与合同仍然有效；
下次改动代码或合同后，回执需重跑，不能沿用。
