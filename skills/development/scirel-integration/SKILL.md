---
name: scirel-integration
description: Use when understanding saved L1 scientific-asset bundles, comparing them with the current SciRel library, and integrating, deduplicating, or relating their operators and TaskGraphs before expert review.
---

# SciRel Integration

## Purpose

Turn one or more source-shaped L1 bundles into a scientifically coherent candidate for the maintained SciRel library.
The essential work is semantic: understand the incoming relations, understand what SciRel already provides, compare
them, and decide what should be reused, related, changed, added, or left unresolved.

This skill supplies a method, not a fixed pipeline. Do not require a universal task manifest, orchestration script,
receipt schema, workspace layout, or standard set of probes. Choose inspections, temporary scripts, numerical
experiments, and tests from the actual scientific question. A useful task-specific check may remain run evidence;
promote it into maintained project code only when it protects a stable reusable invariant.

The inputs are the exact saved L1 directory, a frozen SciRel baseline, and a view of all current unpublished
candidates. Treat L1 and the frozen baseline as read-only. Write only to an isolated candidate area or candidate
worktree that is not the maintained baseline. The candidate pool is comparison context, not an authoritative or
runnable baseline. L1 is expected to follow the extraction contract, but it may still contain missing files, weak tests,
dangling graph references, ambiguous science, or source-specific assumptions. Diagnose those facts rather than
assuming either perfection or invalidity.

This skill does not change, approve, or release SciRel assets. It prepares a candidate document, candidate code, and
candidate tests for later expert review. Approval is what authorizes a separate task to apply the accepted candidate
to SciRel.

## Understand both sides

Read the L1 project framework map, extraction ledger and report, then the relevant operator and TaskGraph packages.
Establish what each candidate computes, its direction, assumptions, ports, units, axes, state, numerical method,
applicability, dependencies, tests, provenance, and evidence ceiling. Use the implementation and tests to challenge
the prose; do not infer missing science from names.

Read SciRel's architecture and catalog guidance, then inspect the maintained implementation, public exports,
scientific tests, TaskGraph bindings, asset documents, and provenance relevant to the incoming families. The catalog
may be partial, so absence from `catalog/examples/` is not evidence that SciRel lacks a capability. Discover the
actual baseline progressively rather than loading the whole library into context.

Compare incoming candidates with one another, the unpublished candidate pool, and SciRel. A repeated project should
normally resolve to existing identities, variants, or explicit unresolved differences instead of generating another
copy. Prefer merging, replacing, or withdrawing a candidate that no expert has opened when that removes duplicate
expert work. A queue entry alone does not freeze the candidate. Never silently rewrite a candidate after expert
observation, review, or approval.

## Compare scientific meaning

Use names, source paths, lexical similarity, signatures, hashes, or sample outputs only to find comparison targets.
Decide relationships from the scientific contract, in roughly this order:

1. relation identity, implemented direction, variables, assumptions, and claimed result;
2. units, coordinates, axes/indexing, shape, dtype, sign, and normalization;
3. model, geometry, approximation, boundary, closure, branch, and initial conditions;
4. state ownership, lifecycle, update order, feedback, convergence, restart, and failure behavior;
5. discretization, interpolation, solver, matrix/RHS construction, tolerance, and error semantics;
6. applicability domain, evidence ceiling, provenance, and license constraints.

For every incoming operator or TaskGraph, reach one evidence-bounded disposition:

- reuse the existing SciRel identity or absorb an exact duplicate while preserving source lineage;
- propose semantic equivalence, without merging until the available evidence supports it;
- record that one capability subsumes or overlaps another without assuming the smaller capability should disappear;
- retain a scientific variant, or parameterize a family only when the parameter exposes every material difference;
- propose a lossless adapter for information-preserving representation changes;
- compose exact existing capabilities under an explicit port, order, state, feedback, and failure contract;
- add a genuinely new capability;
- preserve conflicting candidates and request an expert decision; or
- keep the relation unresolved and name the smallest missing fact.

A shared implementation does not merge scientific identities. A larger TaskGraph containing a smaller graph does
not make the smaller graph redundant when it has an independent contract or reuse value. Partial node overlap is
usually an `overlaps` relation, not duplication.

## Prepare the review candidate

Keep the frozen SciRel baseline unchanged. Prepare proposed code and tests in an isolated candidate worktree, patch,
or review directory; do not bulk-copy an L1 bundle over maintained SciRel source. Reuse an existing public capability
when its contract already fits. Propose code only for the selected scientific disposition, and keep domain-organized
Python callables as the public surface.

When L1 structure is defective, repair only derived working material or the SciRel successor; do not rewrite the
saved input. When science is ambiguous, preserve the gap. When normalization changes a formula, unit, boundary,
discretization, state transition, default, or failure behavior, treat it as a scientific change and establish the
new behavior with appropriate evidence before presenting it for review.

The candidate document is the primary review surface because it lets an expert understand the proposal before reading
code. For each affected scientific identity, explain the incoming and current behavior, proposed disposition, material
scientific differences, public API and dependency impact, evidence, provenance, known limits, and the exact decision
requested from the expert. Include proposed canonical asset-document content when the candidate would add or change a
public asset; do not publish it into the maintained catalog before approval.

Candidate code shows the smallest implementation or patch needed if the proposal is accepted. Candidate tests show
the claimed relation, retained behavior, boundary and failure semantics, and affected compositions. Run them against
the isolated candidate when feasible and record the result. A pure reuse or duplicate disposition may legitimately
have no runtime-code patch, but the document must say so explicitly and comparison tests or experiments must support
the claim; do not create meaningless code merely to fill a slot.

Record the exact frozen SciRel Git base and unpublished candidate-pool snapshot used for the comparison in the
candidate document or harness run evidence. An unobserved candidate may be edited in place even after it enters the
review queue so its document, code, and tests converge into one review unit. The workbench must atomically freeze the
trio before returning its full detail to an expert. Later material changes require rework or a linked replacement
candidate. Candidate generation ends after the trio enters the review queue; do not
keep an agent session open while waiting for an expert. Approval starts a separate integration task against the
then-current SciRel baseline.

Integrate approved candidates one at a time at first, or in parallel only when their affected scientific identities
and dependency closures are demonstrably disjoint. Apply the approved patch unchanged when it still applies and rerun
the affected tests. If intervening changes alter the same identity, public contract, dependency, TaskGraph, or patch
hunk, do not choose a winner or bulk-merge queued candidates. Compare again against the current baseline and prepare a
linked replacement candidate for review. An older approval remains evidence for the older candidate; it does not
approve materially changed code. A candidate that becomes duplicate after an earlier integration should return as a
documented reuse/duplicate proposal, not be silently dropped.

Unreviewed candidate code may be stored in a review directory, artifact, branch, or worktree. It must remain excluded
from SciRel public imports, the catalog, and built wheels. Putting it in an experimental location with those exclusions
is still candidate staging; putting it in the maintained runtime package is a baseline change and requires approval.

For TaskGraphs, bind exact dependency identities and make ports, ordinary DAG edges, state ownership, branches,
feedback, stopping conditions, bounds, and failure propagation explicit. Do not hide scientific work in glue.

## Verify what the change claims

Design verification around the actual disposition and claim. Reuse still needs enough comparison evidence to show
the incoming contract fits the existing asset. Parameterization needs coverage of every retained variant. Adapters
need information-preservation evidence. Compositions need port, order, state, convergence, terminal-result, and
failure tests. New or changed science needs relation-sensitive checks appropriate to that model and method.

Use repository tools such as affected-test selection and asset-document validation when they fit the change, but do
not mistake them for the reasoning process or for scientific proof. Create task-specific probes or scripts when they
clarify the case; keep them as temporary evidence unless repeated use demonstrates a stable project requirement.
Do not weaken existing numerical assertions, tolerances, or failure checks to make an integration pass.

## Handoff

Report the exact L1 input and frozen SciRel baseline inspected, every candidate document/code/test artifact, tests and
experiments run, and the evidence limits. Account for every incoming asset in a concise comparison inventory that
identifies its disposition, the related existing or proposed SciRel identity, material differences, evidence used,
and unresolved questions. The inventory may use whatever task-local form best supports the batch; it is not a new
governance database or a claim of approval.

Stop at an expert-reviewable candidate outside the frozen SciRel baseline. Model execution, passing tests, a generated
report, or a clean build does not approve the science, apply the candidate, or authorize release.
