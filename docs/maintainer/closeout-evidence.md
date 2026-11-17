# 结项证据（#249 二期基础结项）

**状态页，不是规范页。** 这里每条都是「命令 → 当时的输出」，用来核对某一时点的主张是否成立。
它会随 `main` 漂移，所以**不要引用本文的数字**——要引用就重跑命令，数字以重跑为准。

- 测量时点：`main` @ `8b6c92c6d40e8a09acf3002c18a49d46f0cac269`
- 该点上的发布档：`steps 10/10 passed`、`tests collected 9541 / passed 9528 / failed 0`、
  `RESULT SHA256 42b45835557d09f2cb5b4bd058ff5fcada22a53c5a236bd669ea75562f4638a7`、
  `EXCLUSIVE  no other test run or check holds the clone lock`、`ALL GREEN`

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
9541 skills/development/scirel-acceptance/anchors/release-da4c039f44eb.json
```

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

```sh
python -B scripts/build_pure_delivery.py --help
```
发布档里覆盖这一步的是 `wheel build`、`wheel exposure`、`documentation build`、
`contracts and examples` 四个步骤；`8b6c92c6` 上全部 PASS。安装后自检另见
`examples/c5-delivery-acceptance/receipt.json`（`validate_installed_wheel` PASS、
`in_source_tree:false`、`external_site_paths:[]`）。

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
