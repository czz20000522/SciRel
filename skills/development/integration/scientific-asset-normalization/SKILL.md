---
name: scientific-asset-normalization
description: Normalize a caller-selected batch of correctness-qualified scientific candidates through comparison, deduplication, parameterization and bounded refactoring.
---

# Scientific asset normalization

Use the shared operating contract already loaded for this task mode. If it is
not loaded, read [the shared operating contract](../../references/scirel-development-core.md)
once before proceeding; do not reload it for each routed sub-skill.
This D2 skill operates on an exact, correctness-qualified batch. It compares scientific meaning before code shape,
preserves applicability differences and produces a coherent development implementation with comparison evidence.
It does not reopen source discovery, re-decide correctness without a concrete contradiction, write lifecycle state,
approve, package or publish.

For direct SciRel product work without an exact D1 and correctness-qualified
batch, return to the development path in [the shared operating contract](../../references/scirel-development-core.md);
do not manufacture a qualification packet for a local change.

## Input and workflow

Require exact candidate/dependency digests, source lineages, applicability/contracts, correctness evidence and
claim ceilings, selected scope, exclusions and runtime profile. Reject `latest` aliases and missing qualification;
record `input_correctness_conflict` for a contradiction and route only that branch to correctness.

1. Group candidates by relation, direction, units/axes, state/failure semantics and declared applicability. A shared
   name or similar code is not equivalence; keep incompatible domains separate.
2. Choose the smallest common contract supported by evidence. Parameterize only material differences that remain
   explicit; do not move interpolation, closure, discretization or scientific conversion into glue.
3. Deduplicate with source lineage and before/after behavior evidence. Preserve original candidates and failures
   read-only; successor code/comments carry conventions and reuse references without copying dossiers.
4. Run focused structural, contract, regression and affected scientific checks. Reuse attributable evidence when
   identity and inputs are unchanged; preserve full denominator and `NOT_RUN` rows.
5. Return retained/rejected/isolated candidates, comparison matrix, changed identities, checks, limitations and
   receiving integration owner. A stable implementation is not a catalog/release approval.

Load [deduplication rubric](references/deduplication-decision-rubric.md), [relation page contract](references/relation-page-contract.md)
or [refinement output contract](references/refinement-output-contract.md) only for that output.
