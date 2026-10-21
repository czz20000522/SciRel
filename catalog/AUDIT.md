# Capability audit and adversarial testing

This is the project-wide audit protocol for the 248 catalog assets. It is not a
replacement for direct tests; it defines how a capability moves from "tests pass"
to "audited for its declared domain".

## Why this exists

Passing tests prove behavior only on the exercised cases. A decomposer can pass
source-parity tests while a later SciRel rewrite/integration introduces a new
numerical branch, conditioning failure or contract misunderstanding. The audit
must therefore test parameter envelopes and independent oracles, not just repeat
the submitted examples.

## Risk tiers

- **A (critical)**: eigen/singular/generalized pencils, roots, iterative
  convergence, equilibrium/Picard, Green inversions, adaptive quadrature,
  interpolation near discontinuities, collision/rate asymptotics, anything whose
  output feeds another scientific capability.
- **B (high)**: multi-step compositions, geometry/grid mapping, splines/basis,
  nonuniform grids, high dynamic range rates, unit/axis conversions.
- **C (ordinary)**: closed-form scalar reductions, constants, format/IO adapters
  and validation helpers.

## Per-asset audit record

Each audited asset records:

- asset_id, domain, risk tier, owner;
- declared applicability and numerical limits;
- direct tests and exactly what branches they cover;
- probe families: scaling, permutation/axis, limits, singular/defective cases,
  extreme magnitude, dtype, invalid/failure paths;
- external truth: source project, independent analytic/limit, or `NONE`;
- contract claims re-checked against observed behavior;
- residual risks and a verdict (`pass`, `pass-with-limits`, `fail`, `blocked`).

## Required checks

1. Run every `verification.tests` file and the contract example.
2. Probe at least one admissible input outside the example: scaling,
   nonuniform grid, repeated/defective spectrum, near-singular matrix, large or
   small magnitude, or a boundary/limit.
3. Test at least one declared failure path and confirm no silent fallback.
4. For tier A, compare against an external source/analytic oracle where available;
   SciRel output must never be the reference for itself.
5. Record the numerical floor (roundoff/conditioning), not only residual norms.
6. Update the contract if its evidence claim is broader than what was tested.

## Known P0 finding

`scirel.kinetic.multifluid-frequency-solve` / `fluid_solve_state` fails at valid
two-species parameters (`B0≈2.4e-3 T`, `k=0.05–0.15 m^-1`): two k-points raise
`ArithmeticError`/`ZeroDivisionError`, two return duplicated/missing eigenpairs.
The current solver is a SciRel QZ/refinement rewrite, not a verbatim source copy;
the existing tests cover an invalid tolerance and a very small-k example only.
This is treated as a SciRel capability defect, not a worker glue task.

## Gate

- No unresolved tier-A defect enters a release candidate.
- Every asset has an audit status and evidence link.
- A capability with a known limitation may pass only with that limitation in its
  contract and user-facing API documentation.
