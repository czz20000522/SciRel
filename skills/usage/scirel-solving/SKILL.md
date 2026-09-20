---
name: scirel-solving
description: Use when turning a user's scientific request into a normalized problem, a SciRel-based solution plan, an executed result, and an evidence-bounded explanation using only the visible released catalog.
---

# SciRel Solving

## Purpose

Use the SciRel capabilities visible to the current runtime to answer a scientific request. First understand and
normalize the science, then discover and compose applicable assets, execute them, check the actual result, and explain
the result and its limits. Do not begin by guessing a function from the user's wording.

This skill is SciRel-owned and may run in CodeFusion, Claude Code, Codex or another capable harness. The harness owns
the session, permissions, tools, execution environment, artifacts and delivery; it does not own the scientific
semantics in this skill. This workflow does not inspect unpublished candidates, approve assets, publish TaskGraphs,
or substitute PINN/XNet training for SciRel computation.

The runtime exposes only released assets. Do not add a per-request step that re-proves their approval. A release
identifier may be recorded by the environment for reproducibility without becoming part of the scientific argument.

Read `docs/requirements/scientific-request-workflow.md` for user-visible requirements and
`docs/design/scientific-request-workflow.md` for workflow boundaries when changing this method.

## Normalize the request

State what the user is asking the system to compute before selecting assets. Capture the scientific model, relation
direction, unknowns, geometry, coordinates, units and normalization, initial/boundary conditions, closures and
profiles, supplied inputs, requested outputs, tolerances, stopping conditions, and delivery form to the extent that
they matter for this problem.

Separate user facts, explicit assumptions, defaults, and unresolved questions. Ask for clarification when an unknown
would change the model, applicability, boundary, closure, units, or meaning of the result. A harmless presentation
choice should not block the scientific work. Never silently choose a materially different model.

## Discover applicable capabilities

Use `scientific-asset-navigation` for broad searches, competing models, adapters or multi-asset compositions. Search
the visible catalog progressively: route to a bounded shortlist, inspect summaries, then read the exact documents of
serious candidates. Decide applicability from relation and direction, model, geometry, coordinates, units, axes,
boundaries, inputs, output contract, failure behavior, and evidence ceiling.
When the catalog is exposed through SciRel's thin adapter, read
`docs/requirements/thin-mcp-adapter.md` before the first call in an unfamiliar harness. Use its declared request and
response fields rather than guessing connector envelopes from asset documents or implementation source.
Route and summary records are sufficient to discard clearly unrelated assets. Do not load every exact document to
prove absence; load exact documents only for serious candidates and scientific near misses whose detailed contract
materially affects the decision.

The catalog bound to the visible release is the only capability-discovery and applicability source for this workflow.
Once it is available, do not scan installed modules, package exports, source trees, tests, provenance, historical
admission records, or wheel manifests for additional capabilities or for facts missing from an exact document. Those
materials may diagnose a catalog/runtime consistency failure after a catalog asset has been selected, but they may not
create or widen a solution plan. Treat an importable but undocumented callable as unavailable to this workflow.
Do not enumerate or resolve runtime callables to prove that a capability is absent. Resolve only assets that survive
exact-document matching and enter a valid solution plan; invoke them only after that plan passes its preflight checks.
A rejected or missing candidate needs no runtime probe.

Names, source projects, keywords, and similarity may improve recall but cannot make an incompatible asset applicable.
If pagination is unfinished or catalog coverage is partial, report that no match was found in the inspected scope;
do not claim that SciRel as a whole lacks the capability. Exhausting every included record does not make a partial
catalog complete. Name this outcome an inspected-scope gap or incomplete catalog coverage, never a release capability
gap, even with a qualifier. If the complete visible release has no applicable asset, report a release capability gap.
Never replace a missing capability with a nearby weaker model.

## Plan and validate the run

Prefer one existing TaskGraph when it solves the normalized problem. Otherwise build a per-request run instance from
visible Operators and TaskGraphs. That instance is not a catalog asset and must not be published merely because it ran.

For every node and edge, check the actual applicability and port meaning, units, shape, dtype, coordinates, axes,
normalization, ordering, state, branch and failure propagation. Ordinary dependencies must form a DAG. Any iteration
must have explicit state, update order, stop/convergence condition, bound and nonconvergence outcome.

Glue may select fields or perform declared lossless representation changes. Do not hide interpolation, closure,
discretization, geometry reconstruction, scientifically material unit conversion, or another scientific relation
inside glue. If such a relation is required and no applicable released asset exists, stop with a capability gap.

## Execute and check the result

Execute only after the plan is valid. Preserve the causal SciRel exception and do not silently retry with another
model, asset, convention, or tolerance.

Choose result checks that discriminate this request: finite/domain checks, dimensions, boundary conditions,
conservation, residuals, convergence, positivity, symmetry, limits, or another problem-specific invariant. Use
`scientific-computation-validation` when the requested claim needs independent validation design. Distinguish checks
that passed, failed, were inapplicable, or were not performed. A successful call is not proof of physical correctness,
and a local check does not expand an asset's evidence ceiling. Do not run the full repository test suite as part of an
ordinary user calculation.

## Explain and hand off

Return the requested result, chart, file or project together with a concise audit explanation containing the normalized
problem, assumptions/defaults, selected capabilities and applicability, material nodes/connections, executed checks,
evidence limits, untested properties and capability gaps.

Expose decision provenance and observable evidence, not hidden chain-of-thought. Keep four logical products --
Normalized Problem, Solution Plan, Execution Evidence and Result Explanation -- but choose a task-appropriate format.
Do not require a universal manifest or script, and do not create empty artifacts merely to satisfy those names.
