---
name: scientific-operator-review
description: Independently review one exact scientific operator or TaskGraph and its bound evidence; return read-only findings for source fidelity or scientific claims.
---

# Scientific operator review

Read [the shared operating contract](../scientific-computation-asset-extraction/references/scirel-skill-core.md).
This is an independent, read-only challenge. It cannot edit a candidate, design/execute tests, choose extraction
scope, normalize assets, approve, advance stage state or release.

## Trigger and input

Use when a caller supplies an exact target and asks for fidelity/completeness or correctness review. Require target
and dependency digests, contract, implementation/dependency closure, applicable tests/evidence, claim ceiling and
review scope. Review only supplied material; do not claim access to source, network, runtime or external references
that were not provided. Use [stage boundaries](../scientific-computation-asset-extraction/references/stage_boundary_contract.md)
to identify the owner.

- D1: select `source_fidelity`; inspect source-derived inventory, omitted branches, state/order, dependency closure,
  source failures/NaNs and attributable source-vs-candidate evidence. A matching source defect is a D2 issue, not a
  fidelity failure; introduced mismatch or missing declared coverage is a finding.
- D2/D3 correctness: inspect quantities/equations, units, axes, signs, assumptions, geometry, boundaries/closure,
  discretization, state lifecycle, failure/convergence behavior, independent oracle and composition. Use
  [correctness criteria](references/review_criteria.md) only for this route.

## Review loop and result

1. Bind the review to the exact digest and claim ceiling; inspect the affected scientific cone, not every unrelated
   file. Structural indexes prioritize reading but cannot establish scientific equivalence.
2. Trace each material input through ports and dependencies; compare evidence to the stated criterion and scope.
3. Separate demonstrated defect, missing evidence, runtime/tooling failure and unresolved scientific choice. Do not
   turn a missing check into `pass`, or a provider failure into a scientific failure.
4. Return findings with severity, evidence reference, affected target/case, claim impact and reopening condition.
   Use `supported`, `revise`, `blocked`, or `not_supported` only for the declared review mode.

Keep findings attributable to this revision. The receiving owner decides repair, normalization, human endorsement
and release; a clean review is not approval. Load [evidence-based review attention](references/evidence_based_review_attention.md)
only for multi-round review queues.
