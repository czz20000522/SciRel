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

The inputs are the exact saved L1 directory, a pinned SciRel development base, the last trusted version if any, and a
view of all current unpublished candidates. Treat L1, trusted versions, and frozen review versions as read-only. Work
in an isolated development branch or worktree, where integration may change `src/scirel`, documents, TaskGraphs, and
tests and produce an internal wheel. The candidate pool is comparison context, not an authoritative scientific
baseline; code already integrated into a development branch is runnable but not thereby trusted. L1 is expected to
follow the extraction contract, but it may still contain missing files, weak tests,
dangling graph references, ambiguous science, or source-specific assumptions. Diagnose those facts rather than
assuming either perfection or invalidity.

This skill may integrate and verify development SciRel assets. It cannot grant expert trust or publish a release.
Prepare the scientific comparison, exact documents, implementation, tests, and evidence for a frozen version review;
expert recognition is bound to that exact version and its cumulative scientific delta from the last trusted version.

## Understand both sides

Read the L1 project framework map, extraction ledger and report, then the relevant operator and TaskGraph packages.
Establish what each candidate computes, its direction, assumptions, ports, units, axes, state, numerical method,
applicability, dependencies, tests, provenance, and evidence ceiling. Use the implementation and tests to challenge
the prose; do not infer missing science from names.

Read SciRel's architecture and catalog guidance, then inspect the development implementation, public exports,
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

When the incoming and maintained forms differ by a callable name, asset id, port mapping, split, or merge, replaying
the unchanged L1 test against the maintained package measures **drop-in compatibility**, not scientific equivalence.
A missing symbol or unresolved source id proves that direct binding is unavailable; it is not by itself a scientific
conflict. If equivalence, reuse, or a lossless adapter is claimed, construct a task-specific binding or adapter and
compare the mapped scientific outputs, invariants, accepted domain, and failures. State explicit one-to-many or
many-to-one mappings instead of hiding them under a byte-identity or undifferentiated `reuse` claim.

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

## Integrate the development candidate

Keep L1, trusted versions, and frozen review versions unchanged. Integrate code, exact documents, TaskGraphs, and tests
on an isolated development branch or worktree; do not bulk-copy an L1 bundle over SciRel source. Reuse an existing
capability when its contract already fits. Change code only for the selected scientific disposition, and keep
domain-organized Python callables as the public surface.

When L1 structure is defective, repair only derived working material or the SciRel successor; do not rewrite the
saved input. When science is ambiguous, preserve the gap. When normalization changes a formula, unit, boundary,
discretization, state transition, default, or failure behavior, treat it as a scientific change and establish the
new behavior with appropriate evidence before presenting it for review.

The candidate document is the primary review surface because it lets an expert understand the change before reading
code. For each affected scientific identity, explain the incoming and current behavior, proposed disposition, material
scientific differences, public API and dependency impact, evidence, provenance, known limits, and the exact decision
requested from the expert. Include proposed canonical asset-document content when the candidate would add or change a
public asset. The exact document may live in the isolated development package, but its pilot catalog is internal
validation, not a trusted or user-facing release catalog.

Candidate code shows the smallest integrated implementation or diff. Candidate tests show
the claimed relation, retained behavior, boundary and failure semantics, and affected compositions. Run them against
the isolated development version when feasible and record the result. A pure reuse or duplicate disposition may legitimately
have no runtime-code patch, but the document must say so explicitly and comparison tests or experiments must support
the claim; do not create meaningless code merely to fill a slot.

Record the exact SciRel Git base and unpublished candidate-pool snapshot used for the comparison in the
candidate document or harness run evidence. An unobserved candidate may be edited in place even after it enters the
review queue so its document, code, and tests converge into one review unit. The workbench must atomically freeze the
trio before returning its full detail to an expert. Later material changes require rework or a linked replacement
candidate. Agent development and preparation may end after the review material is submitted; do not keep an agent
session open while waiting for an expert. The complete version submitted for trust review also needs a frozen Git
tree/commit, exact-document set, cumulative scientific delta from the last trusted version, affected reverse
dependencies, verification evidence, and internal wheel/catalog digests when built.

Integrate independent scientific families incrementally; coordinate work on overlapping identities and dependency
closures. If intervening changes alter the same identity, public contract, dependency, TaskGraph, or patch hunk, do
not choose a winner or bulk-merge queued candidates. Compare again against the current development base and record
the new relation and action. An older review remains evidence for its exact version; it does not recognize materially
changed code. A candidate that becomes duplicate after earlier integration should return as a documented
reuse/duplicate conclusion, not be silently dropped.

Unreviewed code may enter imports and internal wheels on an isolated development branch. It must not enter the trusted
user-facing catalog/runtime or a public release. A development pilot catalog, if built, must be labeled as such. A
successful build is engineering evidence, not expert recognition.

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

When replaying an L1 contract, include a control that runs the same test against its own saved implementation whenever
that is needed to distinguish a broken input from a successor difference. A successor pass establishes only that the
exercised cases do not distinguish the implementations. A successor failure establishes a difference whose cause still
needs semantic classification; it does not select `variant`, `conflict`, or `lossless adapter` automatically.

## Specialist routing

Load `scientific-asset-correctness` when an exact candidate needs claim-specific correctness assessment, an
evidence-bounded repair, or reverse-dependency revalidation. Load `scientific-asset-normalization` when a
correctness-qualified cross-source batch needs deduplication, parameterization, composition, or bounded refactoring.
Use `scientific-computation-validation` when the scientific claim requires independent gate design or evidence
assessment. These are conditional methods, not a mandatory serial pipeline; a well-supported reuse or no-code
duplicate proposal can proceed directly to the review candidate.

## Handoff

Report the exact L1 input and frozen SciRel baseline inspected, every candidate document/code/test artifact, tests and
experiments run, and the evidence limits. Account for every incoming asset in a concise comparison inventory that
identifies its disposition, the related existing or proposed SciRel identity, material differences, evidence used,
and unresolved questions. The inventory may use whatever task-local form best supports the batch; it is not a new
governance database or a claim of approval.

Distinguish inventory coverage from review readiness in batch reporting. `inventoried` means an input received a row;
`triaged` means it has an evidence-bounded preliminary disposition; `candidate-ready` means an expert can inspect the
document, proposed code or explicit no-code rationale, and distinguishing tests for a specific decision. Report each
level separately when they differ. A reconciled inventory, even with no missing rows, does not make every row a
scientifically reviewable candidate.

Deliver a runnable development version and, when ready, a frozen expert-reviewable version with its scientific delta
and evidence. Review the cumulative delta against the last trusted version, not merely the preceding development
commit. Reuse evidence only when implementation, contract, dependencies, and applicable environment remain unchanged.
If an expert accepts only part of that delta, remove or rework the rest on an isolated successor, rerun affected checks,
and freeze it anew; never mark the mixed original snapshot trusted. Model execution, passing tests, a generated report,
or a clean build does not approve the science or authorize release.
