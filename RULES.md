# Project meta-rules

This file records how SciRel work is **governed**, not just what one feature does.
It exists so a later human or agent can understand our preferences and continue
without replaying chat history. If a rule matters, it must live in a canonical
file in this repository; chat-only knowledge is not durable.

## 1. Record first, then execute

- Durable decisions, boundaries, preferences, and handoff state must be written in
  the same task that created them.
- A later agent must be able to start from these files, not from a previous
  conversation.
- A change is not "done" until its rule/decision is recorded where the next owner
  will look.

## 2. Canonical placement

| Kind of knowledge | Canonical location |
| --- | --- |
| Code truth, asset rules, conflict policy | `src/scirel/`, `catalog/README.md`, `catalog/examples/` |
| Docs/API/bilingual/review/publish rules | `tools/docs/manual/README.md`, `tools/docs/` |
| Agent working conventions, required reading, current state | `AGENTS.md` |
| Solving workflow, physical method, report format | `skills/development/usage/scirel-solving/references/` |
| Extraction method and package format | `skills/extraction/scientific-computation-asset-extraction/`, rationale in `docs/maintainer/supply-pipeline.md` |
| Decisions and rationale | the commit that makes the change, plus the canonical file it changes |
| Generated publish artifacts | `dist/` (gitignored); never a source of truth |
| Runtime work, probes, intermediate containers | execution environment; disposable |

Do not create a second copy of the same rule in several places. Use one canonical
entry and link to it.

## 3. Code is the truth

The implementation is the truth. The contract records it, and tests, API pages,
user-guide links and the capability matrix derive from the contract.

When contract and implementation disagree, the code wins and the contract changes
in the same commit:

- scientific convention, fail-closed behavior or public promise -> fix implementation
  and add a regression test;
- stale/template-copied/incorrect contract -> fix contract and all derived text;
- never keep both truths alive, add compatibility aliases, or only patch a
  translation.

### No manual verdict tables

The judgement layer was deleted (`catalog/review/VERDICTS.json`,
`catalog/review/HOLD.json`, `catalog/review/HUMAN_REVIEW_TODO.md`,
`catalog/review/MERGE_CHAIN.md`, `scripts/review_gate.py`,
`scripts/review_harness.py`): it used derived records to judge the implementation
they were derived from, so the direction of the dependency was inverted.

**Do not rebuild it under another name.** An accepted list, a whitelist or a
review-conclusion table has the same shape as the deleted verdict table, and
"same shape, new name" was the most repeated defect of that period.

Three interfaces carry what the judgement layer was previously used for, and
none of them decides whether the science is right:

| Question | Owner |
| --- | --- |
| Is the input well formed and self-consistent? | `scripts/validate_extraction_package.py` |
| Which assets stay out of the installed package? | `catalog/review/excluded_from_package.json` (scope only, with a revisit condition) |
| Is a contract claim backed by an executable test? | the contract's `verification.tests` |

Anything else that would need a recorded human verdict belongs in an issue, not
in a table next to the contracts.

## 4. Review every delivered line

- Generated output is not reviewed output. Every API page, tutorial, contract
  fragment and published page is manually reviewed before release.
- "The validator passed" means structure is valid, not that the science or the
  language is correct.
- Check the chain: implementation -> contract -> direct tests -> example ->
  API page/user guide -> capability matrix.
- Prefer an explicit `NOT_RUN` / missing-evidence declaration over a fabricated
  result.

## 5. Bilingual is human work

- English contract fields are English; Chinese lives in the Chinese reader layer.
- Do not publish a Chinese page containing large English contract passages, or an
  English page retaining Chinese prose. Symbols, formulas and identifiers are the
  only acceptable shared tokens.
- Machine translation is a draft, not a deliverable; a human/agent review pass is
  required for both languages.

## 6. Correctness and competitive value

- 正确性是产品本身。没有证据的能力没有存在的理由；用户可以改用成熟的上游项目。
- 覆盖面永远不能成为编造行为、静默兜底或隐藏失败的借口。
- **物理正确优先于与来源一致。** 与来源一致只证明“和来源一样”，不证明“物理正确”。
  能修成物理上正确的版本，就必须修。
- 判定“来源错了”必须先拿出依据：文献、解析推导或独立数值对照，并说明为什么它不是
  来源有意采用的物理近似或约定。有依据就改，不因为“与来源不同”而保留错误。
- 拿不出依据的，不改实现：把疑点写进合同的局限性，并在 issue 里记录，等证据出现。
- **物理争议靠证据裁决。** 意见不一致时，谁能拿出证据说服对方，就按谁的来；双方都拿
  不出证据的，标为未定，不改代码。讨论留在 GitHub 的 issue 或 PR 评论里。
- 优先选择最长的证据链：独立 oracle、解析不变量、边界探针、来源一致，或明确声明证据
  缺口。来源一致只是其中一环，不能单独证明物理正确性。

## 7. Capability thinking, not LOC thinking

- Decompose and organize by scientific capability, operator/function or
  composition/task graph, never by lines of code, file count or directory shape.
- Extraction takes the skeleton, not everything: the core physical relations on
  the source's main computational path, plus side relations that are reusable on
  their own. Every part not taken gets one disposition line with a reason, so a
  deliberate omission can be told apart from a miss.
- Extraction compares each relation with the frozen SciReL contracts and
  implements only the complement.

## 8. Information boundaries

- Extraction workers know the source, the method, and a frozen SciReL commit
  with its contracts, API rules and checks.
- Receiver workers know the extraction package, contracts, tests, evidence and
  local acceptance rules; not source identity, which stays in the package's
  `private/` part.
- The source, maintenance and outbound lines are independent. A general outbound
  agent consumes the static package without sending its private program, task
  graph or gap list back to the maintainer. An optional coordinator may track
  public handoff state, but must not leak receiver context to source workers or
  source identity to the outbound consumer.
- Deliveries are self-contained; source checkout, private paths or receiver
  expectations must not become runtime dependencies.

The canonical distinction between a source behavior task graph, an extraction
procedure graph, a public SciRel composition graph and a user task graph is in
[`ARCHITECTURE.md`](ARCHITECTURE.md). A source behavior graph is part of the
source evidence when ordering, state, branch, feedback or failure semantics
affect the observable result; it is not the procedure used to extract the
candidate.

## 9. Outbound delivery

- The single outbound entrypoint is `scirel-solving`; it has no version suffix and is overwritten in place, never forked into a parallel outbound skill.
- An old examination/sample is a source of physical requirements, not a package-version or acceptance baseline. The reference answer uses the current SciRel capability set plus explicit glue.
- Outbound workers see only public capability contracts/docs and the user request; not decomposition history, source identity, receiver roadmap or hidden oracle.
- Capability discovery metadata lives in the contract `discovery` block and is maintained by the SciRel intake owner. No schema version labels; iterate directly.
- Gaps are ordinary glue: explicit, testable, disclosed; final scientific acceptance belongs to the requester or a designated expert, not to the worker.

## 9b. Source identity

- Public contract bodies describe the scientific relation and its validation, not
  the source project, checkout path or commit hash.
- Source identity is not part of the published repository. Do not add a provenance
  ledger, source audit, or checkout path to the public tree.
- Source identity is not a discovery label or a public API promise.
- A source-parity note is not a physical-correctness claim (see §6).

## 10. Storage and publication

- The Git repository is the only source of truth. External project sources, runtime
  workspaces and generated release artifacts do not belong in Git.
- Generated HTML/API/matrix sites go to `dist/` (gitignored); deployment is a
  separate action.
- No secrets in the repository; credentials stay outside the source tree.
- Delivery may be a cloud Git repo, archive or object store; SciRel evaluates the
  self-contained result and correctness evidence.

## 11. Change process for meta-rules

When a new durable preference appears:

1. classify it using section 2;
2. write or update the canonical file/page;
3. link it from `AGENTS.md` required reading when a new agent needs it;
4. commit tracked changes and move the baseline tag when appropriate;
5. tell the owner what changed and why, without turning the chat into the only copy.

This file is itself the meta-rule: **if it is valuable, it is written down where
the next owner will find it.**

## 12. Baseline and outbound batch gate

Use this short gate for each bounded maintenance or outbound batch. `RULES.md`
is the canonical checklist. The current revision is the Git commit. Decisions
are recorded in commits and canonical files, not in a handoff log.

1. **Preflight:** record owner, scope, non-goals, current `HEAD`, clean/dirty
   state, input/runtime identity, and lifecycle/cleanup condition. Keep
   `PASS`, `NOT_RUN`, `HOLD`, `BLOCKED`, and `UNKNOWN` distinct.
2. **Red → green:** reproduce the requested failure or missing evidence with
   the smallest affected check, then make the minimal change. Do not refresh a
   historical result or use file existence as run evidence. Select checks with
   `scripts/test_scope.py --changed` and expand local → affected domain/cross
   domain → docs/tooling/delivery as the change requires.
3. **Independent review:** reread the diff and evidence from a separate review
   pass. Confirm contract → implementation → direct test → example → bilingual
   projection bindings; generated output is not approval. Scientific correctness,
   rights, and human acceptance remain separate decisions.
4. **Current binding:** bind only current source/material digests and actual
   commands. Preserve old failures and `UNKNOWN`/`NOT_RUN`; do not rewrite
   history or release a new wheel/package unless explicitly authorized.
5. **Commit and clean:** commit the bounded tracked change, then remove expired
   staging, caches, temporary packages, branches/worktrees/sessions and
   environments whose owner and exit condition are satisfied. Read back the
   cleanup; retain only final artifacts and minimum evidence. For every named
   generated artifact, record its process/result/temporary/frozen class and an
   exact `RETAIN`/`RETIRE`/`HOLD` disposition before mutation; no age, name, or
   broad glob is a deletion rule.
6. **Record:** put scope, unresolved status and the next authorized action in the
   commit message or the canonical file they belong to. Do not add a handoff log
   to the repository, and never treat chat as the sole handoff.

For outbound work the worker receives only the user request and public
contracts/docs. The executable path is **clarify → physical method → confirm →
compute and check → report → independent acceptance**; discovery serves the
compute step where an operator helps. Source identity, hidden
oracle, receiver roadmap, and private acceptance material stay with the owner.

## 12b. Public repository boundary

The published code, tests, gates and documentation build depend only on files
tracked in this repository. They must not read, name or require review material
kept elsewhere. The public surface follows the code: a capability becomes public
when its implementation and contract land together; see `catalog/AUDIT.md`.

## 13. 编程题式能力测试与对抗性覆盖

SciRel 的能力建设采用编程题式合同。题面必须定义完整的问题、类型化输入、单位、边界、输出、失败语义和参考观察；SciRel 提供可复用的科学核心能力，agent 通过公开语言和依赖编写 glue、控制流程与任务组合。

单个正常样例通过不构成功能正确性或通用性证据。每个能力和题目至少建立三类测试：正常范围、下界、上界；适用时还要加入空值、退化、奇异、分支切换、失败和组合输入。测试应攻击输入形状、单位、边界、状态变化、异常类型、输出结构和数值不变量，逼出只针对示例的实现。

合并者不需要一次性猜出全部通用设计。测试先暴露缺口，再把重复出现且具有独立科学语义的关系提升为 SciRel 公共能力；有具体用户题目时，题目专属编排、格式转换和流程控制通常保留为显式可测试 glue。没有用户题目时，拆解线只提交来源行为、候选科学关系、算子/任务图边界和证据，不得臆测一个尚不存在的用户 glue。通用性由跨边界测试矩阵和多个独立消费场景共同证明，不由单个演示结果或代码规模证明。

外部 agent 评测必须使用不含参考答案、隐藏 oracle、既有 glue 和历史运行结果的干净题包。评测 agent 只得到用户需求/题面、公开输入输出合同和当前 SciRel 公共包；参考答案只作为独立的内部 benchmark oracle，在评测完成后用于回归比较。真实用户任务没有预置 oracle，agent 必须依靠需求、公共能力、普通编程逻辑、约束、不变量、诊断和自己生成的测试完成工作。评测记录实际 API 调用、生成的 glue、SciRel 包测试与 agent 测试、结果、失败路径和未覆盖关系，防止答案泄漏或把样例转写冒充能力提取。

未执行的题目不能标成公开能力缺失。`UNATTEMPTED`、`RUNTIME_GAP`、`CONTRACT_CLARIFICATION` 和 `PUBLIC_CAPABILITY_GAP` 必须分开；只有在真实 discovery 和 case run 已经到达某个命名的公开关系边界后，才能把该关系送入合并 intake。脚本只覆盖部分题目时，摘要必须列出实际执行分母，不能把剩余题目继承为 `HOLD_UNSUPPORTED_PUBLIC_API`。

用户可见的完成标准是：需求完整、三类边界测试通过、失败语义可观测、独立 agent 能从公开包生成解答、重复组合仍可运行。SciRel 包测试保护公共能力，agent 测试保护本次用户任务。benchmark oracle 只服务内部回归，不能替代真实用户的约束和诊断；科学正确性、适用性、权利和发布仍由人工审查决定。

出库 skill 统一处理两种模式：内部 SciRel 运行和外部分发用户运行。内部发现公开能力缺口时，必须记录搜索过的合同、近似能力为何不兼容、缺口是否可归入公共能力，并把受影响任务路由到合并/接收线；不能用一次性题目 glue 静默替代缺失科学核心。外部运行发现缺口时，SciRel 是可选增强，agent 可以用普通编程逻辑和公开数值依赖自行补全，在用户环境允许时继续完成任务，并将补全记录为任务 glue；不能把外部用户阻塞在 SciRel intake 上。两种模式共享测试和证据格式，区别只在缺口的所有权和下一步。

## 14. 多项目推广与闭环分层

十题演示只是一个能力切片。后续数十个来源项目和上千条需求必须按五本账推进，不能把任何一本账的完成误当成全链路完成：

1. **来源账**：冻结来源的能力分母、关系、分支、状态和失败语义；允许声明范围的 partial，但不能把未执行范围倒推成“无能力”。
2. **候选账**：保存自包含 source-free packet、候选关系/算子/任务图边界、边界矩阵、失败链和重开条件；没有消费题目时保留“来源行为/候选公共关系/待判定投影”三种状态，不把 task glue 当作拆解事实。候选交付后，只有该拆解 session 的 owner 才决定是否归档；拆解者只能按授权归档自己创建的子 session，具体 successor 才恢复。
3. **公共能力账**：记录已进入 SciRel 的叶能力、公共组合、变体和仍保留为 task glue 的部分；只有跨独立需求重复出现，或已经有稳定公共合同的科学关系，才提升为公共能力。
4. **出库账**：记录干净 agent 是否真实发现、实际调用了哪些公开能力、生成了哪些 glue 和测试，以及结果、失败和未覆盖关系；没有实际尝试的题目不得写成公开能力缺口。
5. **科学审查账**：记录题面、单位、边界、输入输出和适用性的人工意见。源码行为一致、出库可运行和科学接受分别标记，不能互相替代。

统一使用具体状态，避免一个笼统的 `HOLD`：`UNATTEMPTED`（尚未实际发现或运行）、`RUNTIME_GAP`（环境未就绪）、`CONTRACT_MISMATCH`（公开合同与需求语义不匹配）、`PUBLIC_CAPABILITY_GAP`（已到达命名的公共科学关系但包中没有）、`GLUE_PENDING`（公共核心足够，任务 glue 尚未完成）、`SOURCE_PARITY_PASS_SCIENCE_PENDING`、`OUTBOUND_PASS_SCIENCE_PENDING` 和 `SCIENCE_ACCEPTANCE_PENDING`。每个非完成状态必须写明下一次最小行动和重开条件。

每一轮推广采用“先小波、后扩展”的节奏：来源拆解可以在没有用户题目的情况下先建立候选关系、算子和任务图，并以来源行为和边界证据封包；有题目时再用干净出库挑战检验公开发现、glue 和端到端结果。合并线从候选包、重复关系和实际出库缺口共同建立提升队列，合并后只重跑受影响的题目和反向依赖。成功的运行结果保留为 benchmark 回归材料，但不把题目专属 glue、源码答案或单次解析成功塞进 SciRel 公共层。

推广规模的主要指标是：声明分母的闭合率、公开能力发现成功率、干净 agent 的真实完成率、跨需求重复关系的提升率、边界/失败/组合测试覆盖率以及各类未完成状态的可解释性。文件数、代码行数和单次 demo 成功数只能作为辅助信息。

## 15. 对标 SciPy，不自造数值规范

SciPy 是本项目公开数值 API 的参考实现。SciPy 已经覆盖的能力，命名、参数含义和结果语义都对标它，不另立项目自有约定。

- 参数与结果字段用 SciPy 的名字（如 `xtol`、`maxfev`、`success`、`status`、`message`），不用其他来源运行时的别名（如 MATLAB 的 `TolFun`、`TolX`、`MaxIter`、`MaxFunEvals`）。
- 按 SciPy 的含义解读结果标志：`success`（本项目的 `converged` 同义）表示求解器是否收敛，不表示返回值是否有限。
- 不为旧名保留兼容别名；改名时实现、测试、合同和两层阅读记录在同一次改动里一起完成（见第 3 节「One truth」）。
- SciPy 没有对应物的部分保留项目自有规范：合同机制、三层角色、catalog 准入、证据与评审门禁。
- 以 SciPy 行为作为依据时，在合同 `evidence` 里点名对应的 SciPy 函数，不用散文复述约定。
- SciPy 是命名与语义基线，不是代码来源：[`CONTRIBUTING.md`](CONTRIBUTING.md) 仍要求改写成适配本项目的实现，不复制来源代码。
