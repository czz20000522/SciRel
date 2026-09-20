---
name: scientific-computation-asset-extraction
description: Use when extracting one source project into a complete frozen bundle of source-shaped scientific operators, local task graphs, project coverage, and source-free provenance.
---

# Scientific Computation Asset Extraction

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

Read [stage_boundary_contract.md](references/stage_boundary_contract.md) before coordinating
a project. D1 owns source-backed identification, source-free candidate extraction, and the
project freeze; it does not perform correctness disposition, cross-source normalization,
expert approval, or SciRel assembly. `closure_signal.kind` is the single current
state authority; derive `full_freeze` only from the deterministic gate and create a new
snapshot with `reopened_from_digest` when a prior freeze is invalidated.

Before a project freeze, run the complete-bundle dependency closure gate in
`validate_import_intake_package.py`. It must resolve every machine-readable
`task_graphs/...` and `operators/...` `asset_ref` and reject every nested TaskGraph
cycle. A package-local test can pass while a sibling reference is dangling; that is a
project self-consistency failure and keeps the snapshot `active` or `reopened`.

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

Never use package counts, tests, model calls, elapsed time, or worker activity as scientific completion.

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
2. **Make a thin scientific pass.** From declared terminal outputs work backward to central equations,
   closures, boundaries, numerical transforms, diagnostics, primary state, and external inputs; trace explicit
   inputs forward. Build enough of the project map to choose work without pretending the census is complete.
3. **Choose the first closed path.** Prefer a high-value target path with a runnable case, observable terminal
   result, explicit or recoverable state, and useful dependency fan-out. Select only the minimum relations
   required to make that path well posed.
4. **Derive the dependency queue.** Create candidate and evidence work items from scientific identities and
   explicit handoffs. A ready item has either caller-owned inputs or a frozen upstream contract. A TaskGraph
   waits for the exact node versions it binds; unrelated candidates do not wait for it.
5. **Run the candidate microcycle.** For one work item:
   - draft the scientific identity, applicability envelope, provisional port table, claim, and evidence plan;
   - trace formulas, branches, state reads/writes, initialization, boundaries, indices, and failure behavior;
   - decide operator, TaskGraph, non-candidate disposition, or named gap using the boundary rules above;
   - extract the smallest source-free callable without premature generalization;
   - run candidate tests and only directly affected dependency/composition tests;
   - reconcile actual behavior, tests, and ports, then write the final contract from that evidence;
   - bind dependencies and provenance, verify source-free execution, freeze the content digest in the project
     staging ledger, and continue with the next ready item.
6. **Assemble local TaskGraphs when ready.** Bind exact operator/nested-graph versions, validate every external
   and internal port, exercise order/branch/feedback/convergence/failure semantics, and confirm returned fields
   are the true terminal state. Freeze the graph into project staging without waiting for unrelated candidates.
7. **Expand by frontier value.** Choose the next central path, high-fan-out dependency, material branch, hidden
   state, or validation gap. Update the project map once per accepted integration. Do not exhaustively package
   low-value helpers while a central relation remains unresolved.
8. **Close the project.** Reconcile the complete source census with candidates and
   dispositions, close material branches and state lifecycles, and run canonical plus sealed-holdout functional
   reassembly from identical explicit inputs to declared terminal outputs against one bundle digest. This gate
   establishes `full_freeze`. Preserve every candidate's exact digest, dependency closure, and evidence identity
   inside the completed project bundle.

The provisional port table prevents blind implementation, but it is not the final document. Stabilize the
callable and tests before freezing `operator.md` or `task_graph.md`; do not write an idealized final contract
first and repeatedly force code to match speculation.

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

## Coordination and resource ownership

The main agent is the project coordinator. It chooses scientific work from the dependency queue, owns the live
bundle/project sidecars, integrates results, and makes candidate or project claims. Its caller supplies the
project objective and scope ceiling, not a precomputed worker split.

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

## Closeout

For every staged candidate report its identity, kind, exact digest, dependency versions, tests actually run,
supported claim, residual gaps, and changed files. Separately report the project discovery frontier and whether
the run produced staged candidates, a bounded slice, or `full_freeze`. Do not report the extraction as complete
until the declared project scope reaches validator-supported `full_freeze`.
