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

- `contract_example`：调用参数取该资产自己 `example` 块声明的数值。`catalog/examples` 随交付包分发并受 `snapshot_sha256` 绑定，所以这组参数在冻结时就已固定，且消费者无法从题面反推答案。
- `literal`：数值直接写在本清单里，校验器会拒绝 `TBD`、`TODO`、`<...>` 这类占位。

判定容差同理：每条 `tolerance` 判据都带 `basis` 说明误差来自哪里（二进制舍入、离散截断、格式化位数），并标注 `declared_before_run: true`。清单顶部的 `freeze.tolerances_declared_before_any_candidate_run` 是这条纪律的断言，测试会拦住把它改掉或删掉的编辑。

### 判据种类

| 种类 | 含义 | 能不能被候选结果喂出来 |
| --- | --- | --- |
| `contract_fields` | 返回字段集合等于合同声明的输出 | 不能，只能对合同 |
| `parameters` | 只使用合同声明的参数名 | 不能 |
| `exception` | 异常类与该资产 `failure_semantics` 对应通道的原文一致 | 不能 |
| `tolerance` | 预先声明的量、单位、容差与依据 | 容差不能；被比的量可以在运行时取 |
| `invariant` | 必须成立的关系（标度不变、叠加、往返、极限、守恒、单调） | 不能，关系先于运行 |
| `readback` | 跑完重新打开产物核对 | 不能 |

`exception` 判据由校验器对着合同原文核验：一条判据说 `ValueError`，那这份资产的 `failure_semantics.invalid_input` 里就必须真写着 `ValueError`。所以这里不存在「我以为是 ValueError」的猜测——写错就跑不过校验器。io 域的合同声明的是自定义格式错误与 `OSError` 传播，对应任务就按声明写，不硬套通用异常。

### 一条任务长什么样

`kind` 分四档：`nominal`（正常路径）、`failure`（必须真实抛错且不许替换方法或修补输入）、`inapplicable`（合同声明不覆盖，交付物是引用被排除条款，不是算一个替代结果）、`cross`（跨域，必须声明至少两个域并给出交接关系）。每个任务还要有 `min_calls`、`question`、`subdomain`，`nominal` 必须带 `readback`，`failure` 不得带数值容差——拒绝没有容差，这条由校验器强制。

### 配额怎么来的

配额从 `catalog/examples/` 的当前分布派生，不手写规模：每个域 `max(min_per_domain, ceil(该域资产数 / tasks_per_domain_divisor))` 条正常路径任务，每个域至少一条失败或「不适用」任务（领域覆盖不漏），至少三条跨域任务，且每个域的任务点名到的不同资产数不少于该域的任务配额。领域不是挑出来的，是当前合同分布决定的；资产增删时配额自动跟着变，校验器会把缺口直接判红。

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
