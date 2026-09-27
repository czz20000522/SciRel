---
name: scientific-asset-normalization
description: Use when generalizing and normalizing a selected batch of correctness-qualified scientific candidates across sources through comparison, deduplication, parameterization, composition, and bounded refactoring. Does not establish source coverage or scientific correctness, approve, package, or publish assets.
---

# Scientific Asset Normalization

## Mission and method boundary

Apply the normalization method to one caller-selected batch of exact scientific candidates. Compare scientific
meaning before code shape, preserve material applicability differences, create common contracts and implementations
where the evidence supports them, and prepare one internally consistent document/code/test candidate for expert review.

This skill may report that its declared method scope is complete, but it cannot write or advance normalization
lifecycle state. It does not reopen source-project discovery, re-decide inherited correctness without a concrete
contradiction, write workflow facts, approve assets, assemble a distribution, or publish
documentation. Read the governing
[SciRel workflow requirement](../../../docs/requirements/scirel-workflow.md).

Use the shared [stage boundary contract](../../extraction/scientific-computation-asset-extraction/references/stage_boundary_contract.md).
Preserve the correctness-qualified inputs and evidence used for comparison. A structural or profile
repair may be batched deterministically; a scientific ambiguity, external dependency, or
human decision becomes a `boundary_event` and is not silently resolved during normalization.

## Required input

Freeze a batch manifest containing exact candidate and dependency digests, scientific contracts, applicability,
correctness evidence and claim ceilings, source lineages, runtime profiles, selected scope, and exclusions. Reject
mutable aliases and implicit "latest" versions.

Every candidate must have a usable correctness qualification for the claims normalization will preserve. If the
input is missing that basis or normalization exposes a concrete contradiction, record
`input_correctness_conflict` for the affected branch and stop transforming it. Do not repair its science here.

## Comparison model

Build one comparison matrix before changing implementations. Compare in this order:

1. relation/equation identity, direction, variables, and assumptions;
2. units, coordinates, axes/indexing, shape, dtype, sign, and normalization;
3. model, geometry, approximation, branch, boundary, closure, and initial condition;
4. state ownership, lifecycle, update order, feedback, convergence, restart, and failure behavior;
5. discretization, interpolation, solver, matrix/RHS construction, and numerical tolerances;
6. applicability domain and evidence ceiling; then
7. provenance, names, language, package structure, and implementation similarity.

Use [the decision rubric](references/deduplication-decision-rubric.md) for exact duplicates, equivalence,
parameterized variants, lossless adapters, compositions, conflicts, and unresolved relations. Names, taxonomy,
AST/token similarity, or a few matching outputs cannot establish equivalence.

Use machine-generated fingerprints, indexes, signatures, and similarity only to form comparison candidate sets and
to eliminate byte-identical work. Bind cached comparison rows to exact candidate, dependency, contract, and evidence
digests; reuse them only while those inputs remain unchanged. Spend semantic review on the material discriminators
above and on ambiguous or high-impact families. A prefilter may reduce pairwise comparisons, but it cannot merge,
parameterize, compose, or discard a scientific identity.

## Normalization workflow

1. **Account for the batch.** Give every input one inventory row and preserve its exact dependency closure,
   lineage, claims, and exclusions. Do not omit a hard candidate to manufacture completion.
2. **Partition by scientific family.** Group only after material comparison fields are available. Keep ambiguous
   candidates separate and name the missing discriminator.
3. **Choose the disposition.** Retain an independent candidate, absorb an exact duplicate while preserving all
   lineages, propose supported semantic equivalence, define a parameterized family, introduce a lossless adapter,
   build an exact composition, or record `conflict`/`unresolved`.
4. **Design the normalized contract.** Define comparison-ready identity, common namespace, callable signature,
   port meanings, units/axes, lifecycle, applicability, variant discriminators, and failure behavior. A common
   interface must expose every material scientific difference rather than erasing it behind defaults. Judge
   completeness from the whole relation and its bound materials; repeated or equivalent wording and technical
   quotations are not normalization defects by themselves.
5. **Implement bounded transformations.** Refactor only what the normalized contract requires. Do not hide
   interpolation, extrapolation, closure, geometry reconstruction, dimensional reduction, physics-specific
   normalization, discretization changes, matrix/RHS construction, or missing-state recovery in glue.
6. **Compose exact capabilities.** A normalized TaskGraph binds exact nodes and nested graphs and declares ports,
   order, branches, state ownership, feedback, convergence, and failure propagation. It cannot conceal a new
   scientific relation in orchestration code.
7. **Prove non-regression.** Re-run inherited relation, numerical, port, lifecycle, and terminal-state gates for
   every changed candidate. Add adapter round-trip/information-preservation tests and composition tests where
   applicable. New evidence proves the normalized version only; an old pass is not copied by name.
8. **Freeze the batch.** Bind every input to retained, transformed, absorbed, conflicting, or unresolved outputs;
   freeze exact implementations, contracts, dependencies, comparison decisions, transformation diffs, and
   regression evidence.

Use [the output contract](references/refinement-output-contract.md) for the current package layout and
[the normalized relation page contract](references/relation-page-contract.md) for each relation.

## Coordination

The main agent is responsible for the input inventory, comparison matrix, relation-family partition, proposed
canonical identities, shared namespace, lineage, and aggregate method result. When workers exist, dispatch disjoint
relation families or independently testable transformations with exclusive output responsibility. When they do not,
process the same queue serially. Worker availability changes throughput, not the artifact or decision rules; do not
prescribe a worker count or fixed concurrency ceiling.

Workers may propose classifications or successors but cannot edit shared matrices or canonical records. The main
agent rejects stale-digest work, reconciles cross-family dependencies, integrates one current version, and runs the
final batch-wide lineage and regression checks.

## Completion

Report the exact input batch, every relationship disposition, normalized candidates and contracts, absorbed
duplicate lineages, parameterized variants, adapters, compositions, transformation diffs, tests actually run,
claim ceilings, and unresolved conflicts.

The normalization method is complete only when every input appears in the final inventory and lineage, every changed
output has exact dependencies and non-regression evidence, and every uncertain equivalence remains explicitly
separate. The SciRel workflow still validates and records any lifecycle transition. Do not infer
review, approval, distribution, release, or production acceptance.
