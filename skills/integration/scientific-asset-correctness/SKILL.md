---
name: scientific-asset-correctness
description: Use when establishing scientific and numerical correctness for exact scientific operators or TaskGraphs, including evidence-bounded repair and affected revalidation. Does not discover source projects, normalize across sources, approve, or publish assets.
---

# Scientific Asset Correctness

## Mission and method boundary

Apply the correctness method to one exact set of frozen scientific candidates. Determine what each candidate is
proved to do, repair demonstrated defects only when an independent basis makes the correction determinate,
revalidate affected reverse dependencies, and prepare resulting versions and evidence for the receiving candidate flow.

This skill may report whether its declared correctness method scope is complete. It cannot record the durable
correctness disposition, discover a source project, merge or generalize candidates across sources, design a release
API, write workflow state, approve an asset, or publish a package. A local result is scientific material,
not an expert decision or release fact.

Use the shared [stage boundary contract](../../extraction/scientific-computation-asset-extraction/references/stage_boundary_contract.md)
for exact-digest handoffs and recovery. This skill guides the production of bounded correctness evidence and
repair proposals; it cannot change extraction scope, normalize across sources, approve an asset,
or convert a provider/worker failure into a scientific block. Record `tooling_defect` or
`external_dependency` as a structured boundary event with an explicit reopen condition.

## Required input

Freeze one run manifest containing:

- every target candidate ref and content digest;
- exact dependency versions and reverse-dependency scope;
- the scientific contract, implementation, tests, applicability, and claim ceiling;
- available source-behavior, analytic, numerical, composition, and external evidence;
- the authorized runtime/profile and writable work roots; and
- explicit scope exclusions.

Do not silently replace a bound candidate with a newer mutable version or recover missing content from an
unrelated checkout. A digest establishes identity, not correctness.

## Separate the claims

Keep these conclusions independent:

1. `source_fidelity`: agreement with a declared source behavior under identical explicit inputs;
2. `scientific_relation`: correctness of the equation, convention, closure, or physical limit;
3. `numerical_method`: consistency, boundary treatment, stability, convergence, and failure behavior of the
   discrete method;
4. `composition`: units, axes, ownership, state, order, branches, feedback, and failure semantics at ports; and
5. `functional_reassembly`: complete declared terminal output/state behavior for the bounded runnable cases.

Source parity proves only the first claim. Import, smoke, test count, code similarity, or one matching output proves
none of the others. Missing evidence caps the affected claim; it does not justify inventing a scientific rule.

## Correctness queue

Build a dependency-aware queue whose work items name one candidate or TaskGraph, one exact version, the claims to
test, the evidence required, and the reverse dependencies affected by a possible change. Independent items may run
in parallel. An operator repair precedes revalidation of TaskGraphs that bind it.

For each ready item:

1. **Reconstruct the stated relation.** Check variables, units, shape/axes, sign/normalization, assumptions,
   model/geometry, boundary/closure, discretization, state ownership/lifecycle, branch guards, terminal fields,
   and failure semantics against implementation and existing evidence.
2. **Freeze claim-specific gates.** Use `scientific-computation-validation` to select independent analytic,
   manufactured, residual, invariant, limit, boundary, refinement, differential, composition, and reassembly
   evidence. Fix metrics, units, scales, tolerances, expected order, and applicability before observing held-out
   candidate results.
3. **Try to falsify the candidate.** Run the authorized tests and use `scientific-operator-review` for an
   independent read-only challenge when available. Preserve actual observations, rejected calibrations, missing
   fields, and disagreements rather than reducing them to one `pass` label.
4. **Classify the earliest defect.** Distinguish contract ambiguity, implementation mismatch, scientific
   relation error, numerical method error, composition/state error, runtime/dependency failure, and oracle gap.
   Fix declared installable dependencies or runner problems inside the owned environment when permitted. For
   missing evidence, determine whether it is derivable from the bound source/materials, observable at runtime, or
   genuinely external; continue unrelated queue items.
5. **Repair only from a sufficient basis.** Use `scientific-relation-implementation` for the smallest change that
   satisfies the independently stated correction. Establish that basis through necessary source/runtime
   investigation and scientific derivation or references; its absence from the initial handoff is not a reason
   to stop at diagnosis. A confirmed, repairable in-scope defect requires an implemented successor and validation,
   not only a repair proposal. Never change an assertion, tolerance, equation, boundary, or
   document merely to match observed output. Freeze a successor with predecessor, exact diff, rationale, expected
   source divergence, and affected-domain declaration.
6. **Revalidate the impact cone.** Rerun every invalidated claim gate and all TaskGraphs or dependants whose ports,
   state, order, terminal fields, or applicability changed. Unaffected evidence may be rebound only when its
   conditions and content are demonstrably unchanged.
7. **Prepare the disposition.** Propose `correctness_qualified`, `failed`, or `unresolved` and bind it to the exact
   candidate and evidence set for owner validation. A qualified proposal lists the exact supported claims and limits.
   A failed proposal preserves the counterexample. An unresolved proposal names the smallest missing fact, its claim
   impact, and the condition for reopening.

## Coordination

The main agent is responsible for the run manifest, queue, current versions, dependency graph, and aggregate
correctness report. When workers exist, dispatch bounded items with read-only shared inputs and exclusive output
paths; keep
implementation, validator, and read-only reviewer contexts independent when the scientific risk warrants it.
When workers are unavailable, execute the same queue serially. Do not encode a worker count, role count, or fixed
concurrency ceiling.

Only the main agent integrates repair materials and prepares successor dependency versions; the governing owner
issues durable revisions and dispositions. Reject worker returns that target stale digests, change undeclared files,
weaken gates after seeing output, or claim workflow authority.

## Output and completion

For every input produce:

- exact predecessor and final candidate versions;
- claim-by-claim evidence records with actual commands, runtimes, metrics, and limits;
- findings, counterexamples, and unresolved evidence gaps;
- repair diffs and rationale where applicable;
- exact reverse-dependency bindings and revalidation results; and
- one explicit correctness disposition.

The method run is complete only when every in-scope input has a proposed disposition and every proposed successor's
affected dependency cone has been revalidated. `failed` or `unresolved` can complete the bounded investigation but
cannot be reported as `correctness_qualified`. Owner validation is still required before the disposition becomes a
durable workflow fact. Do not infer any handoff, approval, normalization, package, or release state.

For a repair assignment, a bounded investigation exit is not completed remediation. Before deferring an in-scope
defect, identify the necessary investigation attempted and why behavior or a defensible correction remains
undetermined. A temporary execution/material-access failure leaves repair pending; it does not establish
scientific irreparability. Hand final human review the corrected implementation, original behavior, error basis,
changes and validation/limits under the shared
[scientific-correction disclosure](../../extraction/scientific-relation-implementation/references/scientific-correction.md#required-disclosure-at-the-current-stage).
