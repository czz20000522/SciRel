---
name: scientific-computation-asset-extraction
description: Prepare a versioned scientific source project in D0, then coordinate faithful D1 extraction of its frozen delivery into source-free L1 operators and task graphs; also diagnose an existing extraction without changing it.
---

# Scientific Computation Asset Extraction

## Select the task

For a read-only progress question, use [progress diagnosis](references/progress_diagnosis.md) and inspect one
exact snapshot. A diagnosis alone does not authorize writes. For authorized production or repair, read
[stage boundaries](references/stage_boundary_contract.md), then use the project owner loop below.

For authorized source preparation, use [D0 preprocessing](references/material_access_and_preprocessing.md#d0-source-preparation):
keep official upstream read-only; first build or reuse the initial source index, then clean an owned branch/copy,
maintain indexes for stable changes, and freeze the final D0 with its upstream differences. Initial indexing does
not automatically require a second whole-project semantic review; repair known defects in their evidenced scope.
For D1, consume that exact delivery; do not repeat D0 decisions or preparation for each worker. An existing valid
D0 starts directly at D1. Preparation is not scientific-correctness qualification or an approval request per change.

D1 owns complete frozen-D0 coverage, source-shaped runnable implementations, implementation and numerical
comparison against that source, source-free composition, and read-only fidelity/completeness review.
Here and in D1 specialists, bound/original source means the delivered D0. Preserve upstream-to-D0 lineage;
complete D0 fidelity is not complete fidelity to unchanged upstream.
Use `source_fidelity` for every D1 specialist invocation. Source defects are recorded for D2; introduced
extraction defects are fixed here. D2 owns scientific correctness, library comparison, deduplication, correction and assembly. Formal asset documents belong after D2 stabilizes the retained
code, before final review freeze; D1 does not generate them merely to satisfy a template.

Default to a source-project D1 delivery after completing as much of its whole-source extraction as possible.
Relations and graphs are internal work units, not triggers to launch D2/D3 for each finished asset. Save a durable
project handoff that a different owner can consume weeks later without this conversation or a live D1 environment;
use the [stage boundary](references/stage_boundary_contract.md#information-and-immutable-handoff) for its contents.
An explicitly agreed bounded pilot/partial intake is an exception, not whole-project completion or automatic routing.

## Project owner autonomy

Select an independent container or equivalent isolation boundary from the actual project and platform contract,
prepare its dependencies, then start D0 with read-only upstream and an editable workcopy, or D1 with frozen read-only D0, an owned
persistent output location, applicable skills and the project objective. Retain the environment definition and
launch command; verify actual dependency access, read-only upstream, phase-specific source writes and output persistence before claiming readiness.
Use the selected runtime contract. If the user changes the isolation requirement, checkpoint active work and resume in the required runtime; preserve prior evidence and validate only the platform-affected behavior.

The D1 project owner runs the scientific queue below autonomously, including local repair and resumable checkpoints.
When the selected execution harness permits delegation, use subagents or workers for independent scientific families
with private writes and one integrator. Their types, models, counts and invocation commands are run configuration;
none is a method requirement. The host may be local, remote, cloud or a heterogeneous cluster.
Before dispatch, verify the owner's actual delegation tool and each worker's skill/material access; an installed
agent definition or CLI version alone does not establish usable capacity. Start from the supplied material entry
and its literal selectors; use [material access and preprocessing](references/material_access_and_preprocessing.md)
when the shape or index coverage is uncertain. Workers consume the shared frozen preparation and scoped evidence,
not a new project-wide discovery or dependency install for every region.
An outer supervisor samples existing project records for method, direction, evidence, resource and ownership drift;
it does not prescribe each relation's steps or re-accept and hash every incremental report. Intervene for demonstrated
drift, persistent lack of progress, an owner-unresolvable block, a resource/write conflict or a stage handoff.
Resume an idle incomplete owner from its checkpoint under the existing objective, without replacing its scientific
judgment with a new micro-plan. Independent review findings remain attributable and are resolved by the owner.

## Project owner loop

1. **Fix the scope and anchors.** Preserve the exact D0 snapshot and evidence universe, including its upstream delta.
   Reuse a supplied verified source selection and D0 entry; reopen selection only when absent, changed or contradicted.
   Before selecting a new source, cross-check its names/aliases against both history filenames and case-insensitive
   content in the supplied provenance, evaluations, handoffs and run inventories. When repository history is supplied include
   `docs/evaluations/`; a deployed bundle uses caller-supplied history instead. A negative query only describes its
   searched scope. Inspect source availability, runnable entrypoints and source-behavior oracles before choosing;
   copied directories and prior extracted assets do not establish an untouched, complete source.
   Reuse a digest-bound structural index to find source locations, then inspect science; an index or call graph cannot establish the
   scientific census. Map declared terminal outputs backward to governing relations, state and inputs, and trace
   inputs forward. Use the [scientific boundary criteria](references/asset_projection_decision_manual.md#scientific-relation-and-boundary-meaning)
   to distinguish a relation, its directed operator and required composition; "minimal" is not formula/function/output
   count. Record uncovered branches and non-candidate dispositions instead of silently dropping them.
2. **Choose ready scientific regions.** Derive a dependency queue from the source-backed map. Partition by relations
   and target paths, not file count. Delegate independent regions with private writes and one bundle integrator
   using [coordinator-led extraction](references/coordinator_led_extraction.md). Runtime capacity and the task set
   limits; this skill sets no worker quota. Continue independent work when one frontier is blocked.
3. **Implement and validate each relation.** Retain a compact scientific anchor, explicit ports and evidence plan,
   then route to the applicable specialist below. A contract may live in code, YAML, docstrings or an existing
   scientific record. Add only facts not reliably recoverable there: units, assumptions, conventions, source
   mapping, applicability or validation basis. Do not copy the same fact into several forms.
4. **Integrate the actual handoff.** Check source, candidate and dependency identity, affected scientific tests,
   source parity and claim limits. Stage complete candidates independently. Assemble a local TaskGraph once its
   exact dependencies are ready; preserve order, ports, branching, state, convergence and complete terminal outputs.
   Do not hide scientific computation in graph glue or treat call adjacency as a TaskGraph.
5. **Close the declared scope.** Reconcile the whole-source census, material branches and target paths. Run or reuse
   attributable package, source-free and source-comparison reassembly evidence, including material branch/state cases.
   Obtain read-only review of fidelity, source coverage and evidence sufficiency, not scientific correctness.
   Use [closure and progress](references/scientific_capability_closure_and_progress.md)
   within the selected evidence protocol. No unresolved required source-fidelity scope may become
   `full_freeze`; bounded material states its narrower scope. D1 completion is not human approval or release.
6. **Hand off the project snapshot.** Preserve the exact bundle, evidence bindings, source mapping and remaining claim limits for
   the receiving D2 integration owner supplied by that environment. D2 may reuse, combine or discard equivalent
   assets without forcing D1 to write pages that will be discarded. Keep process notes resumable; derive the concise
   root delivery summary from the final evidence rather than rewriting it after every packet. Every stage reads
   its upstream delivery without editing it; decisions, annotations and corrections live in its own derived candidate.

The five-skill extraction bundle contains every D1 specialist linked below. Later-stage skills and repository
requirements are not installed by that bundle and are not prerequisites to completing D1 or saving its handoff.

## Specialist routing

Load only the row needed by the current work item. A specialist returns evidence or a private candidate; the
coordinator owns scope, integration and completion, never self-approval of independent review.

| Current need | Route |
| --- | --- |
| Prepare, clean and freeze a source project before extraction | [D0 source preparation](references/material_access_and_preprocessing.md#d0-source-preparation); editable derivative, read-only upstream and traceable scope delta |
| Decide operator, TaskGraph, support or disposition | [Asset boundary decision](references/asset_projection_decision_manual.md); consult [scientific operator detail](references/scientific_operator.md) only for unresolved granularity |
| Locate existing materials or prepare source navigation | [Material access and preprocessing](references/material_access_and_preprocessing.md) |
| Map a scientific source region | [Source framework method](references/source_framework_production_manual.md); [physics overview](references/physics_framework_production_manual.md) only when a physical map needs clarification |
| Extract, wrap or complete a source-backed implementation | [Scientific relation implementation](../scientific-relation-implementation/SKILL.md), `source_fidelity`, exact source scope; record source defects for D2 |
| Design, execute or interpret source comparison | [Scientific computation validation](../scientific-computation-validation/SKILL.md), `source_fidelity`; source output/state/failure is the oracle |
| Recover missing source observations or hidden state | [Source-free playbook](references/source_free_extraction_playbook.md), then [runtime dataset construction](../scientific-runtime-dataset-construction/SKILL.md) only when capture is necessary |
| Review fidelity, completeness and evidence | [Scientific operator review](../scientific-operator-review/SKILL.md), `source_fidelity`, in a separate read-only context; [closure and progress](references/scientific_capability_closure_and_progress.md) governs the selected exit protocol |
| Package or load a saved L1 bundle | [Intake directory contract](references/intake_directory_contract.md); [artifact templates](references/artifact_template_pack.md) only for layout details |
| Diagnose repeated work or evidence invalidation | [Workflow optimization](references/workflow_optimization.md) |
| Retain or retire substantial external probes/captures | [Evidence persistence](references/evidence_persistence_boundary.md) |

## Repair and claim boundaries

Scientific meaning is anchored in the source, verified code and necessary explicit conventions, not Markdown
presence or heading order. D1 establishes implementation and numerical behavior fidelity to the source;
scientific and numerical-method correctness belong to D2. Later stages are not substitutes for source comparison.
A missing unit, branch, source anchor or behavior oracle is substantive
when it prevents interpretation or validation, regardless of which file should have contained it.

When a path, assertion, format or packaging hash fails, first establish whether the saved code, inputs, outputs and
runtime conditions still correspond. Preserve the failed attempt and repair only the affected mapping/checker or
binding with an attributable successor. Reuse its valid computation and rerun the cheap affected comparison.
Never loosen a scientific tolerance, change science to fit output, overwrite frozen evidence, or invent an earlier
seal. Recompute affected science when correspondence is unproved or scientific inputs/code/environment changed.

Before declaring an external block, check invocation, executable, mounts, runtime dependencies, source-visible
fields and recoverable observations. Report the actual missing fact and reopen condition. Source defects remain
visible with their evidence and claim limits; do not invent science or shrink an executable unfinished scope to
reach the deadline. Package count, tests passed, worker activity and elapsed time are not completion measures.
