# C4 使用验收任务清单

这是 #249 C4「公开使用一致」的冻结基线。一个**只看得到交付包**的消费者，用这里的任务逐条跑通分发包，产出一份可核对的逐项结果。它检验的是交付面的使用一致性：能不能按契约发现、选中、调用、读回和如实报告失败；不是逐项物理复核，那是 C1 的范围。

清单本身在 [tasklist.json](tasklist.json)，结构校验器是 [`scripts/check_c4_tasklist.py`](../../scripts/check_c4_tasklist.py)，默认测试入口会跑它（`tests/tooling/test_check_c4_tasklist.py`）。

## 为什么放在 `examples/`

`examples/` 是仓库里唯一「不随包分发、只用来检验流程」的目录。C4 任务必须对消费者不可见，否则「独立消费者只拿新包」这个前提就不成立：把答案和题面一起塞进 `catalog/`、`skills/` 或 `tools/docs/` 都会随 wheel 交付出去。放这里既不进包，也不会被 `scripts/build_pure_delivery.py` 收集。`negative-demo-*` 用的是同一套位置约定。

## 协议（沿用仓库既有约定，不另立一套）

沿用 `docs/maintainer/supply-pipeline.md` 的工单与评审分层、`skills/development/usage/scirel-solving/references/workflow.md` 的求解流程、`references/result-checks.md` 的「先定容差再看结果」，以及前两批 `.runtime` 消费者任务已验证过的字段：题面 + 冻结输入 + 逐次调用轨迹 + `returned/raised` 状态。区别只在于：那两批材料留在未跟踪的 `.runtime/` 里、且自述非盲评，这份清单进入跟踪文件并声明盲评前提。

### 消费者手上允许和禁止有什么

允许：交付包目录（`catalog/contracts`、`capability-index.json`、`wheel/`、`skills/`、`runtime.json`、两份 requirements），只用它们建出的 Python 环境，本清单，以及三个使用 skill。

禁止：本仓库的 `src/`、`tests/`、`catalog/review/`、`tools/`、任何 worktree；维护者的参照值、预算和比较脚本；另一次消费的验收期望；用联网检索替代包内合同。

### 输入怎么算「预先固定」

两种绑定，二选一，都写在任务里：

- `contract_example`：调用参数取该资产自己 `example` 块声明的数值。`catalog/examples` 随交付包分发并受 `snapshot_sha256` 绑定，所以这组参数在冻结时就已固定，且消费者无法从题面反推答案。当前 72 条任务全部用这一种。
- `literal`：数值直接写在本清单里。校验器逐键对照该资产合同的 `inputs[].name`，键名不在合同里直接判红；`TBD`、`TODO`、`<...>` 这类占位同样判红。

**拒绝类任务的刺激值也冻结在清单里。** `kind: failure` 的任务不是「把有效 example 随手改成无效」，而是 `input_binding` 给有效基线、`stimulus` 给**唯一**一次替换：

```json
"stimulus": [{"asset": "...", "field": "relax", "value": 1.5,
              "failure_key": "invalid_input",
              "declared_rejection": "relax outside [0,1]",
              "expected_exception": "ValueError"}]
```

校验器对每一条都作检查：`field` 必须是该合同 `inputs[].name`；`declared_rejection` 必须是该合同 `failure_semantics` 对应通道里**逐字存在**的片段；`expected_exception` 也必须出现在同一段原文里；异常判据的条数与 `(资产, 通道)` 必须和 stimulus 一一对应。所以「合同没声明的拒绝」和「不存在的参数名」都进不了清单——这正是独立评审退回的两类缺陷。

**绑定合同 example 的反规避要求**（维护者 2026-11-16 裁定，接受这种绑定方式的前提）：既然输入由合同 example 提供而不是抄在本清单里，就必须堵住下面三条绕过路径，任一条发生即该轮消费作废，不能挑选后重报。

1. **不得替换输入。** 正常路径任务不许改 example 的参数、单位、默认值或数组形状，不许先把 example 参数「修正」成能返回的形式再调用，不许用自造输入替换 example 而仍声称完成该任务。拒绝类任务允许且仅允许清单 `stimulus` 给定的那一次确定性替换：不许多换一个字段、不许换成清单外的值、不许把 stimulus 的替换再改回有效值后声称已完成。要补测别的点，另记一条自加用例，与清单任务分开报告。
2. **不得只跑通过的部分。** 72 条任务全部都要有结果；没跑、跑不动、判据不适用都要按其自身状态记录，不允许只提交通过子集，也不允许把整轮改写成「抽样通过」。
3. **不得在看过结果后改判据。** 看到结果之后不许修改 `criteria`、增删判据、放宽容差、把 `pass` 改判为 `not-run` 以求整齐；这类修改只能作为新的冻结修订提交，并写明理由，旧一轮结果原样保留。清单顶部的 `tasks_digest` 让这条成为机械事实，见下节。

判定容差同理：每条 `tolerance` 判据都带 `basis` 说明误差来自哪里（二进制舍入、离散截断、格式化位数），并标注 `declared_before_run: true`。清单顶部的 `freeze.tolerances_declared_before_any_candidate_run` 是这条纪律的断言，测试会拦住把它改掉或删掉的编辑。

### 改判据必须留下新版本

清单把任务段的规范化 JSON 摘要写在自己的 `tasks_digest` 字段里，校验器每次都重算并比对。因此：

- 改任何一个任务、输入、判据或容差，摘要必然变化；**不更新 `tasks_digest` 就判红**，改不进去也藏不住。
- 更新摘要必须与改动同一次提交出现，并在提交信息里写明哪几条判据变了、为什么；旧一轮消费结果与旧摘要一起保留，方便对账。
- 想「跑完发现红就把 rel 从 1e-12 放到 1e-3」的路径会同时留下新摘要和提交记录，评审看得到。

`--print-digest` 只打印重算结果，不改文件，供外部记录引用；`--json` 报告的 `digest` 与 `declared_digest` 并排给出。

### 判据种类

| 种类 | 含义 | 能不能被候选结果喂出来 |
| --- | --- | --- |
| `contract_fields` | 返回字段集合等于合同声明的输出 | 不能，只能对合同 |
| `parameters` | 只使用合同声明的参数名 | 不能 |
| `exception` | 异常类与该资产 `failure_semantics` 对应通道的原文一致 | 不能 |
| `tolerance` | 预先声明的量、单位、容差与依据 | 容差不能；被比的量可以在运行时取 |
| `invariant` | 必须成立的关系（标度不变、叠加、往返、极限、守恒、单调） | 不能，关系先于运行 |
| `readback` | 跑完重新打开产物核对 | 不能 |

`exception` 判据必须写明 `asset`，校验器只查**那一份**资产的 `failure_semantics` 对应通道原文：一条判据说 `ValueError`，该资产的 `invalid_input` 里就必须真写着 `ValueError`。多资产任务不能靠另一份资产的文本来满足。io 域的合同声明的是自定义格式错误与 `OSError` 传播，对应任务就按声明写，不硬套通用异常。

### 一条任务长什么样

`kind` 分四档：`nominal`（正常路径）、`failure`（必须真实抛错且不许替换方法或修补输入）、`inapplicable`（合同声明不覆盖，交付物是引用被排除条款，不是算一个替代结果）、`cross`（跨域，必须声明至少两个域并给出交接关系）。

每个任务的强制字段与校验规则：

| 字段 | 规则 |
| --- | --- |
| `assets` | 必须存在于 `catalog/examples`，不得是包外资产；单域任务的资产必须同域 |
| `question`、`subdomain` | 非空；`question` 至少一句完整描述 |
| `input_binding` | `contract_example` 或 `literal`；literal 的键必须逐个是合同 `inputs[].name` |
| `stimulus` | 仅 `failure` 有，条目逐项对上合同参数名与合同原文，且与异常判据一一对应 |
| `min_calls` | 不少于任务里的资产数，也不少于 stimulus 条数 |
| `criteria` | 非空、id 不重复；`nominal` 要带 `readback`，`failure` 不得带 `tolerance` |
| `inapplicable_reason` + `excluded_quote` | 后者必须逐字出现在该资产 `applicability.excluded` 里 |

### 配额怎么来的

配额从 `catalog/examples/` 的当前分布派生，不手写规模：每个域 `max(min_per_domain, ceil(该域资产数 / tasks_per_domain_divisor))` 条正常路径任务，每个域至少一条失败或「不适用」任务（领域覆盖不漏），至少六条跨域任务，且每个域的任务点名到的不同资产数不少于该域的任务配额。领域不是挑出来的，是当前合同分布决定的；资产增删时配额自动跟着变，校验器会把缺口直接判红。

**模型族口径的已知限制。** #249 C4 要求覆盖「实际整理过的全部模型族/子领域」。当前合同里只有三份带 `family` 字段，无法把族当作覆盖维度核对，所以这一版只用「领域配额 + 每域点名资产数」两级，并把跨域组合与失败路径单列。这是如实标注限制，不是缩小范围：待 #154 补齐 `family` 字段后再加一层族级配额，届时应把方法分支（如有限谐波、固定极点和两路径入口）各自单独计数，且补齐动作属 C2，不在本目录内改合同。

运行校验器（输出配额表与清单摘要，非零退出即不达标）：

```sh
python3 scripts/dev.py run python -B scripts/check_c4_tasklist.py --repo .
```

`--json` 给机器读的报告，`--print-digest` 只打印任务段摘要，供冻结记录引用。

## 一轮消费怎么走

1. 从某一干净提交构建交付包，记下 wheel、`snapshot_sha256`、索引摘要。
2. 消费者在自己的工作目录里按包内 requirements 建环境、装 wheel，**不读本仓库**。
3. 逐条跑清单，产出 `solve.py`、`results.json`、`calls.jsonl`、`REPORT.md`。
4. 维护者只拿原清单和产物比对：逐条判 `pass`/`fail`/`not-run`，未评估的判据不能记成通过。
5. 结果回到 #249 与对应工单，不新建平行真值表。

清单变更规则见 `freeze.edit_rule`：一旦已有候选结果，改任务、改输入或放宽容差都要新的冻结修订并写明理由，绝不为把红判绿而改。新增覆盖可以随时加。

## 这份清单不证明什么

它不证明任何物理结论正确，也不把逐项通过当作全库科学认证。C4 的有界验收结论只能写成「该交付包在清单声明的任务与判据下通过」，未覆盖的族、方法分支和失败路径要照样列出来。

**没有数值 oracle，这是有意的。** 本清单的 `tolerance` 判据只比较「同一关系两次求值」的结果（标度不变、叠加、往返、自残差、和式闭合），全部是定义或代数上的恒等关系，没有一条挂预冻的物理参照值。物理正确性归 C1，C4 只判「能不能按合同正确使用」。因此：

- C4 全绿**不能**被引用为科学通过、精度达标或适用范围证明，报告里必须与 C1 结论分栏写。
- 反过来，C4 红也不能当作物理错误，它说明的是交付面的使用缺陷（发现不到、参数不符、字段不符、失败语义不符、跨域交接不一致）。
- 要引入数值参照，必须带独立来源并单列一节；在那之前不新增此类判据。

22 条 failure 任务的 stimulus 依据合同原文而非实际调用；首轮消费若发现某条 stimulus 并未触发合同声明的拒绝，按**任务缺陷**登记并修正任务，不得据此判定库有缺陷。
