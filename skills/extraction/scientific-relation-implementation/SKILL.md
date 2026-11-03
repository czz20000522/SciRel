---
name: scientific-relation-implementation
description: Implement or change one declared scientific relation, numerical model, closure, diagnostic, solver feature, or evidence-bounded asset gap.
---

# Scientific relation implementation

Read [the shared operating contract](../scientific-computation-asset-extraction/references/scirel-skill-core.md).
Implement the smallest executable relation inside the caller's authorized boundary. This skill does not discover
scope, approve/review, normalize across sources, write lifecycle state or publish/release.

## Route

- For D1 extraction, select `source_fidelity` and use the frozen D0 as oracle. Preserve source defaults,
  state/order, branches, exceptions and failures; record source defects for D2. Read [scientific correction](references/scientific-correction.md)
  only for a confirmed D2 defect.
- For D2/new science, bind equations, assumptions, units, coordinates, domain, closure, initial/boundary
  conditions, state lifecycle, discretization, tolerances and failure semantics. If a material choice is unresolved,
  stop that claim with an explicit owner decision instead of guessing.

## Workflow

1. Freeze target/source mapping, inputs/outputs, dependencies, caller state and applicability. Use existing code,
   YAML, docstrings or exact records as contract anchors; do not duplicate facts into a new page without need.
2. Implement or wrap the relation with minimal interface/dependency changes. Native/local components are valid when
   source, permission, ABI/build and runtime identity are retained; do not hide science in glue or fixtures.
3. Exercise contract dimensions, analytic/manufactured or independent-reference cases when constructible, material
   limits/invariants/symmetries, boundary/zero/failure paths, iteration order and convergence. Preserve all original
   tolerances and denominator rows.
4. Use [scientific computation validation](../../development/scientific-computation-validation/SKILL.md) for independent claims;
   use [operator review](../scientific-operator-review/SKILL.md) separately. Rerun changed behavior and affected
   reverse dependencies only.
5. Deliver implementation/source mapping, exact dependency/runtime identity, checks and evidence references. Keep
   first failures, `blocked`/`NOT_RUN`, and unresolved alternatives; never alter science to fit output.

A corrected successor must disclose original observation, independent basis, exact change, before/after evidence and
remaining limits. The result is evidence for the receiving owner, not a correctness disposition or release fact.

## Candidate quarantine and merge chain

A relation that is not admitted must not be implemented inside `src/scirel/` or
`catalog/examples/`. Stage candidate code and contracts in the review tree; keep
the audit verdict and owner decision beside them. Only an admitted closure enters
the package and public catalog. The current `SCIREL_REVIEW_HOLD` import guard is
transitional, not containment: direct module imports and packaging mistakes can
bypass a runtime guard.

Before merging a candidate:

1. resolve contract dependencies and Python imports to the full closure;
2. run the closure's contract, direct tests, examples, docs and import-surface
   checks in the review harness;
3. merge leaves before compositions and regenerate public exports/docs from the
   admitted manifest, not from a glob or hand-maintained `__all__`;
4. re-run the closure; a composition with a held/failed member is not exposed;
5. delete the staged copy only after the merged closure is green.

If an outbound request needs an absent/held capability, treat it as a gap to fill
inside the request: mark it, try a public formula/exposed composition, verify and
continue; otherwise report the concrete missing input and a bounded result. Do
not turn the gap into a user task to obtain a human reviewer or decompose the
library. The exposure hold is a catalog-publication state, not an outbound stop
line.
