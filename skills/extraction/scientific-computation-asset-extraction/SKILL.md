---
name: scientific-computation-asset-extraction
description: Use when extracting one source project into a complete frozen bundle of source-shaped scientific operators, local task graphs, project coverage, and source-free provenance, or when diagnosing that extraction's current progress without changing it.
---

# Scientific Computation Asset Extraction

## Select one primary mode

- **Production extraction:** use the production line below when the task creates, continues, repairs, or reopens an
  extraction bundle.
- **Read-only progress diagnosis:** when the request asks what is complete, blocked, at risk, or next, read
  [progress diagnosis](references/progress_diagnosis.md) first. Inspect one exact snapshot and do not run production
  steps, edit artifacts, retry work, approve candidates, or publish a bundle.

Do not combine diagnosis and mutation merely because the diagnosis identifies a repair. A later implementation task
must receive its own scope and write authority. The remainder of this entry defines production extraction; diagnostic
mode uses its contracts only to interpret observed evidence.

## Mission and completion boundary

This skill owns one complete extraction of one source project. It discovers source-shaped scientific relations,
makes their required state explicit, extracts source-free callables, builds local TaskGraphs, accounts for the
declared source scope, and stops only when one internally consistent project bundle reaches `full_freeze`.

Preserve the source-backed model, geometry, boundary, discretization, branch, and state-lifecycle characteristics.
Keep the result source-shaped: do not perform cross-project generalization, deduplication, public namespace
design, speculative API unification, or library refactoring.

One operator may freeze into the project's staging area as soon as its own contract, implementation, dependencies,
and evidence close. It does not wait for sibling candidates or future TaskGraphs before becoming immutable. A
TaskGraph freezes only after every node and nested graph it actually binds has an exact ready version and the local
composition contract passes. These independent internal freezes prevent sibling work from reopening completed
assets, but the extraction itself is complete only when the entire declared project bundle reaches `full_freeze`.

The output is a complete extraction bundle, not a source clone, tutorial, generalized library, or claim of
cross-project generality. Preserve the bundle shape from
[the artifact template pack](references/artifact_template_pack.md).

For a new project, the first delivery may intentionally stop at `bounded_delivery`. In that mode, extract and
reassemble only the selected source-backed target paths, and record other source capabilities in the root
`extraction_report.md` section `Deferred Source Capability Register`. A deferred row is a source locator and
reopen hint only; it is not an operator, TaskGraph, callable asset, or expert-review item. Do not create a fake
package or machine-readable `asset_ref` for a deferred capability. Promote a deferred row to extraction only when
SciRel assembly shows that the capability is missing or a project-level `full_freeze` claim is required.

`bounded_delivery` is a finite delivery gate, not a cheaper completion claim. Before setting it, the coordinator must
request an independent bounded-delivery review from a separate read-only subagent. The reviewer reads the exact source
snapshot, source-derived census/index, selected bundle assets, progress snapshot, reassembly evidence, and deferred
register; it returns a digest-bound receipt listing the reviewed target ids, source and bundle digests, findings, claim
ceiling, and `verdict=pass|fail`. The coordinator may set `bounded_delivery` only with `verdict=pass`. The reviewed
targets must be traced and runnable source-backed paths with canonical and sealed-holdout evidence; a report-only
capability or a deferred row cannot be approved. Deterministic validation remains limited to schema, digest, reference,
and receipt-shape checks when such validation is available; the subagent owns the semantic exit decision. The minimum receipt fields are `review_id`,
`reviewer_role=independent_subagent`, `source_scope_digest`, `bundle_digest`, `reviewed_target_ids`,
`reviewed_evidence_refs`, `claim_ceiling`, `reopen_condition`, `findings`, and `verdict`. A bounded batch must state
its claim ceiling and reopen condition and must not imply that unlisted source capabilities were extracted.
The receipt's ceiling and reopen condition must match the closure signal; its reviewed refs must include the
signal evidence and each delivered case's source, bundle, comparison, and tolerance evidence.

Read [stage_boundary_contract.md](references/stage_boundary_contract.md) before coordinating
a project. D1 owns source-backed identification, source-free candidate extraction, and the
project freeze; it does not perform correctness disposition, cross-source normalization,
expert approval, or SciRel assembly. `closure_signal.kind` is the single current
state authority; derive `full_freeze` only from the deterministic gate and create a new
snapshot with `reopened_from_digest` when a prior freeze is invalidated.

D1 must finish the declared source-wide scientific census, source-shaped implementation, and numerical
comparison with the source before claiming `full_freeze`; D2/D3 may not retain a runnable source. Keep a
scientific gap or unproved comparison `active`/`reopened`, with its exact claim ceiling. If a script path,
assertion, format, or digest binding fails, first determine whether the saved computation's scientific code,
inputs, environment, and actual outputs still correspond. Correct only the mapping, checker, or evidence
binding when they do, retain the original failed attempt, and rerun the inexpensive affected comparison or
gate. A corrected assertion must follow source semantics and independent results, never a convenient
candidate value or relaxed tolerance. Recompute affected science only when correspondence cannot be proved
or a material scientific input, implementation, or environment changed; never invent a historical seal.
See [stage boundary contract](references/stage_boundary_contract.md).

Before a project freeze, run the complete-bundle dependency closure gate in
`validate_import_intake_package.py`. It must resolve every machine-readable
`task_graphs/...` and `operators/...` `asset_ref` and reject every nested TaskGraph
cycle. A package-local test can pass while a sibling reference is dangling; that is a
project self-consistency failure and keeps the snapshot `active` or `reopened`.
The frozen bundle must also expose the discovery-only root `asset_entry.py` contract
from the artifact pack and pass `validate_asset_entry.py` inside the fixed asset
sandbox. Bind that exit-0 sandbox run to the exact entry and bundle digests in
`closure_signal.asset_entry_validation`; working snapshots may omit the entry.

## Two work planes

Maintain two linked planes against the same frozen source/evidence universe:

1. **Project discovery plane.** A living scientific map records target outputs, governing equations,
   closures, boundaries, numerical transforms, diagnostics, state transitions, material branches, source
   anchors, candidate identities, dispositions, and the unresolved frontier. It answers what remains.
2. **Candidate production plane.** A queue advances one bounded operator or TaskGraph through discovery,
   contract, implementation, targeted validation, integration, and immutable project staging. It answers what is
   internally finished while the rest of the project continues.

The discovery map guides selection but is not a standalone asset. A project map may remain provisional while
closed candidates accumulate in the project staging area. Do not convert provisional discovery into a completion
percentage. Record progress as frozen candidate identities and named scientific nodes, edges, branches, or target
paths that remain open.

Keep candidate staging and project progress distinct. `candidate_staged` is a coordinator-queue observation that
means one digest-bound candidate is internally complete; it is not an owner or review state. Project progress uses
the existing `closure_signal.kind` values: `active`, `bounded_delivery`, `blocked_external`, or `full_freeze`.
`bounded_delivery` may list staged candidates while the project remains incomplete. `blocked_external` names the
affected frontier and does not stop other ready work. Only `full_freeze` represents completion of the declared
whole-project extraction scope.

For the new-project bounded-first mode, the selected bounded-scope target-path denominator must still be complete
and every delivered target must pass its declared reassembly gates; this denominator is not a claim about the whole
source project. The deferred register is an internal capability-repository
aid and does not enlarge the candidate bundle or the expert-review queue. A later assembly gap may reopen the same
run using the recorded source anchor and reopen condition.

Do not self-review the bounded exit. The coordinator that produced the batch cannot be the bounded-delivery reviewer;
the reviewer must have read-only access to the same run and must not modify the candidate bundle or progress snapshot.

Never use package counts, tests, model calls, elapsed time, or worker activity as scientific completion. They may be
recorded separately to compare workflow cost when the scientific scope and freeze gates remain unchanged.

## Gate ownership

Keep deterministic gates narrow: schema shape, content digests, path containment, cross-reference closure, and
declared receipt consistency are suitable for scripts. Do not try to enumerate every scientific shortcut or semantic
failure mode in validators. Delegate non-enumerable judgments to an independent read-only subagent that can inspect
the source, evidence index, bundle implementation, tests, and runtime receipts together. Typical delegated judgments
include whether a target is genuinely source-backed, whether a deferred row hides a required core relation, whether
state/branches/terminal outputs are represented honestly, and whether the claim ceiling matches the evidence. The
subagent must record findings, uncertainty, reviewed digests, and a verdict; it may reject a delivery without editing
the bundle. For `full_freeze`, the reviewer first derives terminal scientific outputs and material model branches
from the bound source, public entry points, tests/examples, and nested source versions without using the candidate
target list as the discovery denominator. It then reconciles those findings against target paths, assets, and
non-candidate dispositions; it must not limit review to paths the candidate already declares. A parameter fixture
covered by the same generic relation need not become a new asset, but its coverage claim must be source-supported.
A validator pass never substitutes for this semantic review.

## Evidence navigation and reuse

Before the thin scientific pass, build or reuse a run-scoped structural evidence index bound to the exact source
digest. It may record file and language inventory, parse status, symbols, static references and call edges, candidate
entry points, tests/examples/documents, explicit reads and writes, source anchors, tool identity, failures, and
uncertainty. Prefer structured queries and progressive disclosure over repeatedly loading broad source regions.

The index is navigation evidence, not a scientific census or boundary decision. It cannot by itself establish public
scientific inputs/outputs, equation identity, hidden runtime state, document authority, runnable coverage, candidate
kind, or completeness. Use it to select relevant anchors, then inspect the governing source and documents and run
bounded probes where static evidence is incomplete or conflicting. Code-graph, AST, language-server, lexical, and
runtime-trace tools are interchangeable producers behind this boundary; no one tool is required.

Reuse an observation only when its source/input digest, runtime-relevant conditions, claim, and consumer remain
unchanged. Invalidate the affected slice rather than rescanning unrelated evidence. Read
[workflow optimization](references/workflow_optimization.md) when introducing a preprocessor, changing the production
sequence, or comparing extraction efficiency.
For a root project-report-only bundle edit, use the exact execution-rebind record in
[scientific capability closure and progress](references/scientific_capability_closure_and_progress.md); preserve
the full bundle digest and verify unchanged scientific files before reusing a computation.

## Scientific boundary decision

The work unit is a closed scientific relation slice, not a file, routine, class, AST fragment, or arbitrary
formula count.

Emit a `scientific_operator` only when the candidate:

1. has an independent domain or numerical identity;
2. maps explicit caller-owned inputs to scientifically meaningful outputs;
3. has no required hidden source state or undeclared call-order dependency;
4. admits relation-sensitive validation of its own behavior; and
5. can be replaced or reused through its port contract.

Split at an intermediate only when that value has stable scientific meaning, a complete handoff contract,
an identifiable owner/consumer, and independent validation value. Merge adjacent formulas when the proposed
intermediate is only an implementation artifact, forces a consumer to recompute hidden science, or cannot be
owned outside the source call sequence. Arithmetic primitives, projections, one special-function call, local
scaling, caching, parsing, and loop plumbing are not operators by themselves.

Preserve the source-backed applicability envelope. A project-specific remap, closure, boundary rule, or
discretized update may be a valid extracted operator even when a different corpus could support a more general
core. Extraction records a comparison-ready scientific identity; it does not invent a universal abstraction
from one project.

Emit a `scientific_task_graph` only when required order, branching, feedback, iteration, convergence,
state transition, or failure propagation is part of the local scientific/numerical contract. A graph is the
smallest executable local subweb that owns those semantics. It schedules declared assets and explicit bounded
glue; it must not hide a formula, matrix/RHS construction, scientific normalization, state update, or source
global. Source call adjacency alone does not justify a TaskGraph.

Project-wide framework composition stays in the project map. Non-scientific glue and source material that is
not a public operator or TaskGraph receive a digest-bound non-candidate disposition rather than a fake asset.

## Candidate contract

Each frozen candidate must bind one coherent version of:

- scientific identity and a comparison-ready fingerprint: relation/equation family, quantities, assumptions,
  geometry, boundary, discretization or numerical method, and state-lifecycle semantics;
- a source-independent Chinese scientific contract that explains the problem, relation, applicability, ports,
  behavior, and failure boundary without requiring the source tree;
- complete typed ports: quantity, role, units/normalization/sign, dtype, shape, axes/indexing, ownership,
  initialization/update cadence, mutation/persistence, branch guards, and terminal consumer where applicable;
- a source-free callable implementation and only runtime-required package data;
- exact candidate dependencies and real port bindings;
- relation-sensitive tests plus a durable evidence summary matched to the claim made;
- source anchors and minimal provenance sufficient to audit derivation, bound by content digest; and
- an explicit claim ceiling, exclusions, unresolved gaps, and reopen conditions.

The contract is source-independent in meaning and source-traceable in evidence. Source names may appear in
provenance, not as the explanation a future caller needs.

Do not put public library imports, tutorials, application examples, cross-project deduplication decisions,
speculative generalized APIs, source copies, raw probes, repeated logs, captured answer arrays, or external
process receipts inside the candidate package.

## Single-project production line

1. **Freeze the source/evidence universe.** Record the source snapshot, available documents, fixtures,
   runnable cases, runtime identity, scope ceiling, and owned scratch/evidence roots. Keep source immutable.
2. **Make a thin scientific pass.** Create or reuse the digest-bound structural evidence index, then from declared
   terminal outputs work backward to central equations,
   closures, boundaries, numerical transforms, diagnostics, primary state, and external inputs; trace explicit
   inputs forward. Build enough of the project map to choose work without pretending the census is complete.
3. **Choose the first closed path.** Prefer a high-value target path with a runnable case, observable terminal
   result, explicit or recoverable state, and useful dependency fan-out. Select only the minimum relations
   required to make that path well posed.
4. **Derive the dependency queue.** Create candidate and evidence work items from scientific identities and
   explicit handoffs. A ready item has either caller-owned inputs or a frozen upstream contract. Derive TaskGraph
   readiness from current contracts rather than maintaining a second manual list: `probe_ready` means enough nodes
   and provisional ports exist to exercise composition and discover missing science; `freeze_ready` requires every
   exact bound version, compatible complete ports, dependency closure, and declared graph-level gates. Probes may run
   before freeze readiness; unrelated candidates do not wait for the graph.
5. **Run the candidate microcycle.** For one work item:
   - draft the scientific identity, applicability envelope, provisional port table, claim, and evidence plan; keep
     source fidelity (`direct`, `indirect`, or `unavailable`) separate from independent scientific validation
     (`analytic`, `invariant`, `trusted_reference`, `behavioral_only`, or `none`) because both may apply;
   - trace formulas, branches, state reads/writes, initialization, boundaries, indices, and failure behavior;
   - decide operator, TaskGraph, non-candidate disposition, or named gap using the boundary rules above;
   - confirm the scientific definition, purpose, real inputs/outputs, applicability, and failure behavior from
     source evidence; retain the source version, scope, necessary scientific/port definitions, and validation
     anchors before implementation, without requiring a finished `operator.md` or `task_graph.md`;
   - extract the smallest source-free callable without premature generalization;
   - run candidate tests and only directly affected dependency/composition tests;
   - reconcile observed behavior against the contract; correct implementation errors without changing the
     physical meaning to fit a computed result. A genuine contract defect gets an explicit revision, source
     rationale, and revalidation of the affected candidate and dependent slices;
   - bind dependencies and provenance, verify source-free execution, freeze the content digest in the project
     staging ledger, and continue with the next ready item.
6. **Assemble local TaskGraphs when ready.** Bind exact operator/nested-graph versions, validate every external
   and internal port, exercise order/branch/feedback/convergence/failure semantics, and confirm returned fields
   are the true terminal state. Freeze the graph into project staging without waiting for unrelated candidates.
7. **Expand by frontier value.** Choose the next central path, high-fan-out dependency, material branch, hidden
   state, or validation gap. Update the project map once per accepted integration. Do not exhaustively package
   low-value helpers while a central relation remains unresolved.
8. **Close the project.** Reconcile the complete source census with candidates and dispositions, and close material
   branches and state lifecycles. Once code and graph versions are stable, generate `operator.md`, `task_graph.md`,
   and the final root documents from that exact code and the retained scientific anchors, before `full_freeze`.
   Distinct packages may be documented by independent agents in parallel; the coordinator remains the single
   integrator of the live bundle. Check every final document against the source-backed definition, actual ports,
   code, tests, and output evidence at the same code digest. Run or reuse canonical plus sealed-holdout functional
   reassembly from identical explicit inputs to declared terminal outputs, binding the final bundle digest; a
   documentation-only rebind needs its independent review receipt. Preserve every candidate's exact digest,
   dependency closure, and evidence identity inside the completed project bundle. A project-specific runner may
   sequence deterministic gates and write a receipt, but successful process exits do not replace census,
   target-path, claim, oracle, or reassembly evidence. Fix a proven mechanical gate defect at the affected
   checker or binding and reuse valid computations; do not turn it into an automatic full science rerun.

   Derive concise package pages and root reports after code and graph behavior stabilizes. Reuse checked
   definitions from code, docstrings, and the structural evidence index where accurate; each page must retain
   its scientific meaning, real inputs/outputs, source locator, and graph order/state contract. Avoid repeated
   narrative that D2 may discard during normalization.

The provisional port table is a compact scientific anchor, not a required early finished document. Physical
meaning comes from the frozen source, verified implementation, and scientific checks; it is not established by
filling a template. A genuine scientific correction revises code and revalidates its affected closure. A later
documentation-only correction retains prior computations when the executable identity and inputs are unchanged
and the final contract passes independent review. Never silently redefine a quantity, port, or boundary to match
a computed result.

## Evidence and blockers

Match evidence to the candidate's claim:

- direct/analytic relations: dimensions, analytic cases, limits, boundaries, and applicability;
- discrete/numerical mappings: consistency and the applicable convergence, conservation, stability, symmetry,
  monotonicity, or conditioning properties;
- source-fidelity claims: identical explicit inputs and source comparison under predeclared tolerances;
- TaskGraphs: port handoff, order, branch, feedback, convergence/failure, and complete terminal state.

Source parity proves fidelity, not scientific correctness. Passing import or smoke tests proves neither. Record
honest extraction evidence and limit each claim to what that evidence establishes. Scientific or numerical checks
may expose a source defect, but they do not authorize this skill to rewrite the source-backed relation.

When required state is hidden in globals, common blocks, files, saved locals, random history, or call order,
first recover a minimal typed caller-owned carrier through bounded static/dynamic probes. Captured source state
is an oracle, not a runtime input. Read [the source-free playbook](references/source_free_extraction_playbook.md)
for this condition and use `scientific-runtime-dataset-construction` when a runnable source must expose missing
state or source-side oracles.

Before `blocked_external`, audit the blocker origin. Check the runner, mounts, arguments, executable, image
architecture, installable runtime dependencies, receipt schema, source-visible fields, and recoverable runtime
observations. Classify the exact missing field as source-derived, runtime-derived, or genuinely external. Fix or
derive the first two; name the external owner and reopen condition for the third. Continue other independent
frontiers whenever possible. A block on one slice is not a block on the project.

If the source appears wrong, separate observed source behavior, source intent, and independent scientific
expectations. Preserve the source-shaped relation and record the exact anomaly, affected domain, evidence,
claim ceiling, and reopen condition. Fix an extraction mismatch when the callable fails to reproduce its declared
source behavior; do not change an equation, closure, boundary, or physical meaning to correct the source itself.

When a source path cannot produce its declared terminal scientific result, first distinguish a source-local
non-executable path from a missing installable dependency, wrong invocation, recoverable hidden state, difficult
numerics, or absent tests. Use exact source anchors, call-site tracing, and a bounded source probe where possible;
none of those latter obstacles alone justifies exclusion. For a genuinely non-executable path, preserve its intended
scientific role, concrete defect evidence, and any independently executable physics subrelations. Give the broken
path an explicit non-candidate disposition rather than fabricating a runnable asset or treating source completion as
a D1 prerequisite. Revise the source-derived census and executable target-path denominator explicitly, retaining
the path in source coverage records, then create a fresh strict `1.0` snapshot and re-run all remaining whole-project
freeze gates. Do not remove an executable but unfinished core path or shrink scope to fit the current bundle. A later
source repair or SciRel scientific completion can reopen the recorded gap without changing what D1 actually proved.

## Coordination and resource ownership

The main agent is the project coordinator. It chooses scientific work from the dependency queue, owns the live
bundle/project sidecars, integrates results, and makes candidate or project claims. Its caller supplies the
project objective and scope ceiling, not a precomputed worker split.

For a wide project, partition ready work by source-backed scientific region or target-path dependency, not by
file count. The coordinator may delegate region discovery, candidate work, and contract/report drafting as
separate packets while retaining one writer for shared bundle and project state. Region and document workers
return bounded, source-anchored handoffs; their parallelism does not establish census completeness or review
independence by itself.

Use whatever delegation capability is actually available. Dispatch independent ready work when workers exist;
keep the same queue and execute work items serially when they do not. Worker availability changes throughput,
not the method, artifact boundary, or completion criteria. Do not encode a required worker count, fixed role
count, or fixed concurrency ceiling in this skill.

Read [coordinator-led extraction](references/coordinator_led_extraction.md) when delegation is possible or the
objective contains multiple independent slices. It defines work packets, exclusive write ownership, handoff,
integration, transient failure, and serial fallback. The coordinator alone updates shared maps, ledgers,
digests, aggregate progress, and live candidate versions.

Treat shared reads as part of packet ownership: declare the complete read-only allowlist and whether the current
candidate may be read, then apply the reference's independence rules before accepting a delegated claim.

Every run owns isolated run-scoped scratch, external evidence, containers, and temporary volumes. Keep bounded current evidence,
condense durable conclusions into contracts/sidecars, and retire superseded run-owned resources after their last
consumer. Never delete shared caches, images, other runs, or broad parent paths. Read
[evidence persistence](references/evidence_persistence_boundary.md) only when the run creates substantial probes,
captures, containers, or external evidence.

Treat each concurrently possible or retried execution attempt as its own write-ownership boundary. Once an
attempt emits a receipt or retained evidence, its writable paths are immutable: any rerun, especially after a
harness, input, image, or command change, uses a fresh run-owned attempt root. Reuse is allowed only after the
exact writer has terminated and the prior contents are explicitly discarded because no audit evidence remains.

## Reference routing

Load references only when their condition applies:

- Diagnosing current extraction progress without changing source, bundle, candidates, or owner state:
  [progress diagnosis](references/progress_diagnosis.md).
- Writing or validating the formal extraction bundle: [artifact template pack](references/artifact_template_pack.md)
  and [intake directory contract](references/intake_directory_contract.md).
- Choosing between operator, TaskGraph, support kernel, or disposition when the rules above are insufficient:
  [asset projection decision manual](references/asset_projection_decision_manual.md).
- Recovering hidden state, source runtime behavior, source-free replay, or a missing edge:
  [source-free extraction playbook](references/source_free_extraction_playbook.md).
- Designing source-fidelity, relation-sensitive, or reassembly evidence: load
  `scientific-computation-validation` with that extraction-only claim scope; do not duplicate its domain-specific
  test design here.
- Making a whole-project coverage or completion claim: [capability closure and progress](references/scientific_capability_closure_and_progress.md)
  and [framework closure priority](references/framework_closure_priority.md).
- Introducing structural preprocessing, reusing repeated evidence, or running a bounded baseline/candidate
  comparison: [workflow optimization](references/workflow_optimization.md).
- Deciding whether a bounded batch is genuinely deliverable: obtain the independent subagent review receipt before
  writing `closure_signal.kind=bounded_delivery`.

## Closeout

For every staged candidate report its identity, kind, exact digest, dependency versions, tests actually run,
supported claim, residual gaps, and changed files. Separately report the project discovery frontier and whether
the run produced staged candidates, a bounded slice, or `full_freeze`. Do not report the extraction as complete
until the declared project scope reaches validator-supported `full_freeze` with its scientific comparisons.
