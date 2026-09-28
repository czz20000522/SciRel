# Scientific skill group stage boundary contract

SciRel owns its scientific methods and assets. A host such as CodeFusion, Claude Code, or Codex may load and run
those methods, but host job state does not replace SciRel scientific state and the host does not own Operator,
TaskGraph, catalog, review, or release semantics.

This reference defines only the D1 extraction boundary. The later candidate and release lifecycle is authoritative in
[the SciRel workflow requirements](../../../../docs/requirements/scirel-workflow.md),
[the SciRel workflow design](../../../../docs/design/scirel-workflow.md), and the skills under
[`skills/integration/`](../../../integration/). User-facing discovery and execution belong to
[`skills/usage/`](../../../usage/). Do not duplicate those workflows here.

## D1 responsibility

D1 produces a saved, source-traceable L1 bundle: a project framework map, Operator and TaskGraph contracts,
source-free candidate implementations, tests, evidence, provenance, and explicit gaps. The result remains a
re-runnable source candidate. It is not a normalized SciRel identity, an expert decision, a maintained-baseline
change, a catalog entry, or a release.

Keep the output source-shaped and preserve its lineage. Do not perform cross-project equivalence decisions,
deduplication, public namespace design, expert approval, or release work. Those exclusions do not make imperfect L1
material invalid by definition: record recoverable format, test, evidence, and scientific gaps with enough detail for
a later SciRel workflow to diagnose them without rewriting the saved source record.

D1 must establish complete declared-source coverage, source-shaped implementations, and numerical comparisons
with the source before a qualified complete L1 `full_freeze`. Later stages may not be able to access or run the
source, so unresolved scientific coverage or validation remains a named D1 gap. An incomplete candidate may be
saved under an explicit claim ceiling but must not be reported as qualified complete material.

When an executed result still has independently verifiable code, inputs, outputs, and runtime-relevant
conditions, fix a path, assertion, format, or digest binding with a traceable supplemental record instead of
repeating the calculation. Check an assertion against source semantics and independent results; do not relax
its scientific tolerance to fit the candidate. Preserve the old failure and its evidence, without fabricating
a historical seal. Rerun only the affected cheap comparison or gate; repeat scientific execution when its
correspondence is missing or the inputs, executable science, or environment materially changed.

For a `bounded_delivery` handoff, D1 requires an independent read-only subagent review of the exact source-derived
census, selected bundle assets, reassembly evidence, and deferred capability register. The review receipt is a finite
exit decision for that batch, not expert approval and not a `full_freeze` claim. The producing coordinator must not
also act as this reviewer, and the reviewer must not edit the bundle or progress snapshot.

## Preserved material and gaps

- Preserve the source snapshot, raw evidence, L1 bundle, and their content identities.
- Record a gap with the observed fact, evidence, affected claim, next evidence or decision needed, and the condition
  that would make it actionable.
- Keep tool failures distinct from scientific defects. Missing evidence caps the claim and need not block unrelated
  candidates.
- Do not infer approval, publication, or maintained-baseline membership from a candidate, test result, review note,
  staged digest, or `full_freeze` signal.

Use content digests where bytes cross an artifact or evidence boundary. Do not create per-edit digest ceremony for
ordinary working notes.

## TaskGraph and evidence constraints

Ordinary TaskGraphs are dependency-closed DAGs. Feedback or iteration must declare state, update order, stopping
condition, finite bound, and nonconvergence behavior. Source parity proves source behavior only; it does not prove
general physical correctness. Project examples may support a bounded claim but do not automatically become global
rules for every SciRel asset.

For a D1 full-freeze claim, the extraction gate derives `closure_signal.kind=full_freeze` from the declared scope,
resolved asset references, package tests, source-free execution, and required reassembly evidence. This signal means
only that the declared L1 extraction bundle is internally frozen; it does not approve or publish the candidates. A
model must not set it merely because its own run completed.
