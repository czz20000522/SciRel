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
4. Use [scientific computation validation](../scientific-computation-validation/SKILL.md) for independent claims;
   use [operator review](../scientific-operator-review/SKILL.md) separately. Rerun changed behavior and affected
   reverse dependencies only.
5. Deliver implementation/source mapping, exact dependency/runtime identity, checks and evidence references. Keep
   first failures, `blocked`/`NOT_RUN`, and unresolved alternatives; never alter science to fit output.

A corrected successor must disclose original observation, independent basis, exact change, before/after evidence and
remaining limits. The result is evidence for the receiving owner, not a correctness disposition or release fact.
