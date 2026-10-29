# Project meta-rules

The cross-project version of these rules lives in the global `agentic-development`
skill: `references/durable-rules-and-handoff.md` (durable placement, single truth,
generated-is-not-reviewed, information boundaries, handoff). This file is the
SciRel-specific overlay; project paths and schemas stay here.

This file records how SciRel work is **governed**, not just what one feature does.
It exists so a later human or agent can understand our preferences and continue
without replaying chat history. If a rule matters, it must live in a canonical
file or Notion decision record; chat-only knowledge is not durable.

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
| Contract truth, asset rules, conflict policy | `catalog/README.md`, `catalog/examples/` |
| Docs/API/bilingual/review/publish rules | `tools/docs/manual/README.md`, `tools/docs/` |
| Agent working conventions and required reading | `AGENTS.md` |
| Decomposition methodology, candidate/info/delivery boundaries | `skills/extraction/scientific-computation-asset-extraction/references/` |
| Decisions, rationale, history, ownership | Notion project/knowledge records |
| Generated publish artifacts | `dist/` (gitignored); never a source of truth |
| Runtime work, probes, intermediate containers | execution environment; disposable |

Do not create a second copy of the same rule in several places. Use one canonical
entry and link to it.

## 3. One truth, explicit choice

Every capability has one public contract truth. Implementation, tests, API pages,
user-guide links and the capability matrix are projections of that truth.

When contract and implementation disagree, choose one truth explicitly and record
the reason:

- scientific convention, fail-closed behavior or public promise -> fix implementation
  and add a regression test;
- stale/template-copied/incorrect contract -> fix contract and all derived text;
- never keep both truths alive, add compatibility aliases, or only patch a
  translation.

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

- Correctness is the product. An unverified capability has no reason to exist;
  users can use the mature source project instead.
- Coverage never justifies invented behavior, silent fallbacks or hidden failures.
- Prefer the longest available evidence chain: source parity, independent oracle,
  analytic invariant, boundary probe, or an explicit evidence gap.

## 7. Capability thinking, not LOC thinking

- Decompose and organize by scientific capability, operator/function or
  composition/task graph, never by lines of code, file count or directory shape.
- Decomposition is a proactive supply line; it does not wait for a demand map.
  Produce a complete candidate inventory, preserve uncertain candidates, and let
  the receiver choose.
- 10-20% is a receiver-side expectation, not an extraction quota or a LOC target.

## 8. Information boundaries

- Decomposition workers know the source, methodology, capability definitions and
  delivery format; not the receiver catalog/roadmap/acceptance decisions.
- Receiver workers know the self-contained package, contracts/tests/evidence and
  local acceptance rules; not source identity or decomposition history.
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

## 9b. Source provenance

- Public contract bodies describe the scientific relation and its validation, not
  the source project, checkout path or commit hash.
- Source identity is retained in `catalog/review/SOURCE_PROVENANCE.md` and
  `catalog/review/evidence/` so a future owner can compare a capability with its
  exact source if a problem appears.
- Source identity is evidence, not a public capability name; do not use it as a
  discovery label or a public API promise.
- A source-parity record is not a physical-correctness claim.

## 10. Storage and publication

- Mac checkout is the only source of truth. External project sources, runtime
  workspaces and generated release artifacts do not belong in Git.
- Generated HTML/API/matrix sites go to `dist/` (gitignored). E drive is not a
  required deployment location; deployment is a separate action.
- No secrets in the repository; credentials stay outside the source tree.
- Delivery may be a cloud Git repo, archive or object store; SciRel evaluates the
  self-contained result and correctness evidence.

## 11. Change process for meta-rules

When a new durable preference appears:

1. classify it using section 2;
2. write or update the canonical file/page;
3. link it from `AGENTS.md` required reading and the Notion handoff index;
4. commit tracked changes and move the baseline tag when appropriate;
5. tell the owner what changed and why, without turning the chat into the only copy.

This file is itself the meta-rule: **if it is valuable, it is written down where
the next owner will find it.**

## 12. Baseline and outbound batch gate

Use this short gate for each bounded maintenance or outbound batch. `RULES.md`
is the canonical checklist; `HANDOFF.md` records the current revision and
Notion records the decision/history.

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
6. **Record:** update `HANDOFF.md` and the existing Notion record with scope,
   evidence, unresolved status, next authorized action, and the exact first
   candidate workflow when outbound work is next. Never treat chat as the sole
   handoff.

For outbound work the worker receives only the user request and public
contracts/docs. The executable path is **discover → select contract → explicit
glue → execute → readback → independent acceptance**. Source identity, hidden
oracle, receiver roadmap, and private acceptance material stay with the owner.

## 13. 编程题式能力测试与对抗性覆盖

SciRel 的能力建设采用编程题式合同。题面必须定义完整的问题、类型化输入、单位、边界、输出、失败语义和参考观察；SciRel 提供可复用的科学核心能力，agent 通过公开语言和依赖编写 glue、控制流程与任务组合。

单个正常样例通过不构成功能正确性或通用性证据。每个能力和题目至少建立三类测试：正常范围、下界、上界；适用时还要加入空值、退化、奇异、分支切换、失败和组合输入。测试应攻击输入形状、单位、边界、状态变化、异常类型、输出结构和数值不变量，逼出只针对示例的实现。

合并者不需要一次性猜出全部通用设计。测试先暴露缺口，再把重复出现且具有独立科学语义的关系提升为 SciRel 公共能力；题目专属编排、格式转换和流程控制保留为显式可测试 glue。通用性由跨边界测试矩阵和多个独立题目共同证明，不由单个演示结果或代码规模证明。

外部 agent 评测必须使用不含参考答案、隐藏 oracle、既有 glue 和历史运行结果的干净题包。评测 agent 只得到用户需求/题面、公开输入输出合同和当前 SciRel 公共包；参考答案只作为独立的内部 benchmark oracle，在评测完成后用于回归比较。真实用户任务没有预置 oracle，agent 必须依靠需求、公共能力、普通编程逻辑、约束、不变量、诊断和自己生成的测试完成工作。评测记录实际 API 调用、生成的 glue、SciRel 包测试与 agent 测试、结果、失败路径和未覆盖关系，防止答案泄漏或把样例转写冒充能力提取。

未执行的题目不能标成公开能力缺失。`UNATTEMPTED`、`RUNTIME_GAP`、`CONTRACT_CLARIFICATION` 和 `PUBLIC_CAPABILITY_GAP` 必须分开；只有在真实 discovery 和 case run 已经到达某个命名的公开关系边界后，才能把该关系送入合并 intake。脚本只覆盖部分题目时，摘要必须列出实际执行分母，不能把剩余题目继承为 `HOLD_UNSUPPORTED_PUBLIC_API`。

用户可见的完成标准是：需求完整、三类边界测试通过、失败语义可观测、独立 agent 能从公开包生成解答、重复组合仍可运行。SciRel 包测试保护公共能力，agent 测试保护本次用户任务。benchmark oracle 只服务内部回归，不能替代真实用户的约束和诊断；科学正确性、适用性、权利和发布仍由人工审查决定。

出库 skill 统一处理两种模式：内部 SciRel 运行和外部分发用户运行。内部发现公开能力缺口时，必须记录搜索过的合同、近似能力为何不兼容、缺口是否可归入公共能力，并把受影响任务路由到合并/接收线；不能用一次性题目 glue 静默替代缺失科学核心。外部运行发现缺口时，SciRel 是可选增强，agent 可以用普通编程逻辑和公开数值依赖自行补全，在用户环境允许时继续完成任务，并将补全记录为任务 glue；不能把外部用户阻塞在 SciRel intake 上。两种模式共享测试和证据格式，区别只在缺口的所有权和下一步。
