---
name: scientific-asset-correctness
description: Establish scientific and numerical correctness for exact operators or TaskGraphs, repair only determinate defects, and revalidate affected dependencies; return bounded evidence.
---

# Scientific asset correctness

Read [the shared operating contract](../../references/scirel-development-core.md).
This D2 skill consumes exact D1 candidates and owns independent scientific correctness, evidence-bounded repair and
affected revalidation. It does not discover source scope, normalize/merge candidates, write lifecycle state,
approve, package or publish.

## Required input and method

Freeze one manifest containing every target/dependency digest, reverse-dependency scope, scientific contract,
applicability, available source/analytic/numerical/composition evidence, runtime/profile, writable work root and
explicit exclusions. Reject mutable aliases. Preserve D1 source issues; source fidelity is not correctness.

1. Reconstruct the stated relation: variables, units, axes, signs, normalization, assumptions, geometry, boundaries,
   closure, discretization, state lifecycle, branch/failure behavior and terminal outputs.
2. Select independent checks by risk: analytic/manufactured or external reference, invariants/limits, residuals,
   conditioning, convergence/refinement, composition and complete terminal reassembly. Carry every retained capability
   and original case/threshold denominator.
3. Classify observations as relation, numerical method, composition/state, runtime/dependency, oracle gap or
   `tooling_defect`. Missing evidence is `blocked`/`NOT_RUN`, never an implied pass.
4. Repair only when an independent relation, source observation or explicit contract makes the change determinate.
   Create a successor candidate, rerun affected reverse dependencies and disclose before/after evidence. Do not
   weaken tolerances, delete failures, switch models or hide a failed scope behind warnings.
5. Hand exact evidence and claim ceiling to normalization/integration. Local `passed` means only this correctness
   method scope; it is not human endorsement or release.

Read [scientific correction](references/scientific-correction.md)
for repair disclosure and [review criteria](references/review_criteria.md)
only when the corresponding trigger is present.
