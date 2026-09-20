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
