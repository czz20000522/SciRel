---
name: scientific-operator-review
description: Independently review exact scientific operators or TaskGraphs and bound evidence; D1 reviews source fidelity and completeness, later correctness tasks review scientific claims. Returns read-only findings, not repairs, approval or stage completion.
---

# Scientific Operator Review

## Purpose and authority

Independently review one exact operator or TaskGraph, its scientific contract, implementation, dependencies,
tests, and validation evidence. Look for the strongest demonstrable correctness risks and return evidence-bound
findings to the caller.

This skill is read-only. It does not design or execute tests, edit content, choose project extraction scope,
compare candidates for normalization, approve an asset, write workflow facts, or decide whether a production stage
is complete. When a platform invocation supplies a typed response schema, follow that schema; local labels never
override owner state.

Use the shared [stage boundary contract](../scientific-computation-asset-extraction/references/stage_boundary_contract.md)
to identify the current owner. A finding is evidence for one exact revision; this skill
cannot rewrite the candidate, advance owner state, or carry approval to a successor digest.
Out-of-scope concerns become a structured `boundary_event`.

## Input boundary

Require the exact target digest, exact dependency versions, scientific and port contract, implementation, bound
tests/evidence, declared claim ceiling, applicability, and requested review scope. Review only supplied material.
Do not claim source, network, runtime, or external-reference access that the invocation did not provide.

The scientific contract may be expressed in code, YAML, docstrings, function/module comments and exact existing
records. Do not require a formal page or repeat recoverable facts. Inspect upstream deliveries read-only; findings
and any later corrections belong to the receiving stage's derived candidate.

For a scientific-correctness review, read [the correctness criteria](references/review_criteria.md) for detailed finding tests. Use
`scientific-computation-validation` only in a separate validation task when a proposed or executed gate needs
specialist assessment.

For large correctness-review increments or a requested sequence of AI reviews before human judgment, use
[evidence-based review attention](references/evidence_based_review_attention.md). Keep package eligibility,
review attention and final human approval separate; recommendations do not grant owner authority.

## Efficient review focus

Use exact-digest structural indexes, claim/evidence matrices, prior findings, and predecessor diffs to navigate the
target and identify the affected scientific cone. They may prioritize reading but cannot replace inspection of the
material contract, implementation, tests, and evidence anchors. Mechanical similarity, unchanged filenames, or a
clean diff does not establish scientific equivalence.

Reuse a prior review conclusion only when the target digest, dependency versions, claim, applicability, evidence,
and review scope are identical. For a successor, concentrate repeated inspection on changed formulas, ports, state,
branches, evidence, and reverse dependencies while still accounting for every claimed dimension. Do not repeat a
full unchanged review merely to produce new activity, and do not skip a material risk because it was absent from an
index.

## Review order

For D1 select `source_fidelity`. Review the source-derived inventory, implementation mapping, omitted material
branches, native/package dependency closure, state/order and attributable source-vs-candidate evidence. Check
whether the comparison would reveal a plausible translation mismatch and whether source failures/NaNs and
suspected defects are retained honestly. A matching known source defect is a source-issue finding for D2,
not a fidelity blocker. Introduced behavior changes, missing source comparison, hidden checkout dependencies
or incomplete declared coverage remain fidelity/completeness findings. Do not require independent physical
oracles, scientific correction, analytical accuracy or experimental validation for this mode. Return advisory
findings on these claims; do not execute tests, modify artifacts or decide stage completion.

The following correctness review order applies when scientific/numerical correctness is actually claimed.

1. **Confirm identity and claim.** State the exact target, relation direction, supported domain, claimed evidence
   level, and exclusions. A digest binds bytes, not scientific truth.
2. **Challenge the contract.** Check quantities, equations, assumptions, units, shape/axes/indexing,
   sign/normalization, model/geometry, boundaries/closures, discretization, state ownership/lifecycle, branch
   guards, terminal fields, and failure semantics.
3. **Trace implementation fidelity.** Map every material formula, coefficient, axis, boundary, branch, update,
   convergence decision, and returned field to code and tests. A TaskGraph may schedule exact assets and bounded
   adapters; it must not hide an undeclared scientific mapping in glue.
4. **Challenge evidence.** Check that each named claim has an applicable independent oracle, predeclared metric
   and tolerance/order, relevant boundaries/failures, actual observation, exact runtime/target binding, and honest
   limitation. Source parity cannot prove scientific or numerical correctness.
5. **Test the negative interpretation.** Name plausible sign, coefficient, axis, mask, boundary, state-order,
   residual, or failure mutations and verify the supplied evidence would distinguish them. If it would not, report
   the evidence gap instead of assuming the implementation is correct.
6. **Check dependency impact.** For a successor, verify the stated diff, correction basis, expected source
   divergence, affected ports, and revalidation of exact reverse dependencies.

## Findings and outcome

Every finding includes severity (`Blocker`, `Major`, or `Minor`), exact candidate-relative path or artifact ref,
verbatim supplied evidence where possible, violated claim, impact, and the smallest corrective or validation need.
Separate a demonstrated defect from missing evidence and from an unresolved scientific choice.

Use advisory outcomes only:

- `supported`: supplied material supports the exact bounded claim and no material correctness defect is found;
- `revise`: a correctable contract, implementation, numerical, composition, or evidence defect is demonstrated;
- `not_supported`: the target lacks a coherent scientific identity, fabricates evidence, or cannot support its
  stated claim from the supplied scope.

In `source_fidelity` mode these outcomes assess fidelity/completeness claims only. A source-issue note does
not turn `supported` fidelity into scientific correctness or make it `revise` without an actual extraction gap.

Report residual risks even for `supported`. A reviewer without execution access phrases unrun tests as proposals,
never observations. Do not mutate the target, close a human comment, approve an asset, or translate the outcome
into upload, expert approval, normalization, packaging, or release state.
