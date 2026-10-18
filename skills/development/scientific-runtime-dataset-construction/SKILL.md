---
name: scientific-runtime-dataset-construction
description: Capture source-runtime inputs, predecessor/hidden state, branches, event history, or numerical oracles needed to close one declared extraction or validation gap.
---

# Scientific runtime dataset construction

Use the shared operating contract already loaded for this task mode. If it is
not loaded, read [the shared operating contract](../references/scirel-development-core.md)
once before proceeding; do not reload it for each routed sub-skill.
Use the real bound source runtime to expose a named observation gap. The dataset is external evidence, never a
formal operator/TaskGraph dependency or a captured answer. This skill does not choose boundaries, implement science,
judge correctness, write owner state or accept/release an asset.

## Trigger and dataset contract

Use only when a required source/runtime fact is absent and is recoverable by an authorized source execution.
Require exact source revision, runtime/profile, case/branch denominator, capture placement, semantic termination
criterion, output location and custody. A provider/worker error is a process observation; an absent producer or
human choice is a blocked owner decision with a reopen condition.

1. Design the smallest coverage matrix that distinguishes the named gap: normal, boundary, failure, state/lifecycle,
   iterative/convergence, stochastic/MPI or table/matrix cases as applicable. Preserve full denominator and split
   integrity; one seed or one parallel run does not establish arbitrary equivalence.
2. Instrument only required entry/exit/state fields. Record raw source inputs, branch selectors, event history,
   outputs, termination status, source/runtime identities and per-case digests. Keep probes/parsers/arrays outside
   `operators/` and `task_graphs/`.
3. Validate capture integrity, reachability, semantic completion and provenance before handing observations to the
   caller. A partial/failed capture remains visible; do not fill missing rows from reports or interpolate hidden state.
4. If proposing a typed carrier, bind it to source observations and distinguish it from a captured fixture. Route a
   relation gap to [asset correctness](../integration/scientific-asset-correctness/SKILL.md), and claim evaluation to
   [computation validation](../scientific-computation-validation/SKILL.md).

Read [dataset contract](references/dataset_contract.md) for manifest/case fields and [boundary coverage](references/boundary_coverage.md)
for case design. Use [method feedback protocol](references/method_feedback_protocol.md) only for a bounded routine
microprobe. Return dataset path, manifest/hash, source/runtime provenance, case counts by state, covered gap, failed,
blocked and `NOT_RUN` cases, claim ceiling and next owner. Never infer an algorithm uniquely from samples.
