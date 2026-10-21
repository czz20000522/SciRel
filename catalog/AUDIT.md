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

## Prevention at ingestion

The failures found by the audit are mostly ingestion-design failures, not isolated
coding mistakes. The receiver must not accept a candidate merely because its
submitted tests pass. Future intake requires:

1. **Declared evidence envelope** — the candidate states the tested parameter
   ranges, branches, grids, species/model regimes and known singular limits. A
   test outside that envelope is a new claim, not a regression.
2. **Oracle class** — every tier-A capability names one of: independent
   analytic/high-precision, bounded source-method parity, or self-consistency
   only. `self-consistency` is not an independent oracle and must be visible in
   `verification.evidence_ceiling`.
3. **Asset-specific direct evidence** — shared test files must state which
   asset/feature they actually validate. A file that describes itself as a plan
   or proposed gate cannot be bound as validation evidence.
4. **Adversarial probes** — at least one scaling/limit/singular/defective-case
   probe beyond the source example, plus one declared failure path. Tier A
   requires this before acceptance; tier B requires it before release.
5. **Roundoff/conditioning floor** — record the numerical floor and do not use a
   tolerance below it as a pass criterion. Growth/zero-mode claims need a
   separate precision argument.
6. **Composition evidence** — when a composition binds the capability, intake
   runs the composition as well as the leaf. Leaf tests cannot prove graph
   wiring, ordering, units or failure propagation.
7. **Independent intake rerun** — the receiver reruns the probe set in its own
   environment and may add cases that the decomposer did not know about; this is
   not a demand for receiver-specific behavior, only an adversarial test of the
   declared scientific relation.
8. **Verdict before admission** — tier A needs an audit verdict (`pass`,
   `pass-with-limits`, `blocked`); no unresolved tier-A defect enters a release
   candidate. A known limitation is allowed only when it is written into the
   contract and user-facing API documentation.

The decomposer still owns the source-faithful translation and its evidence. The
receiver owns the independent acceptance test, the declared scope and the
decision to admit. Neither side may use "tests pass" or "SciRel output matches
itself" as the final proof.

## Merge layers and exposure hold

Candidate admission has three outcomes:

- **auto-merge**: agent verdict is `pass` or `pass-with-limits`, no agent
  disagreement remains, and the evidence is reproducible. The asset enters the
  exposed catalog.
- **human-review**: the agent cannot decide, agents disagree, or a model/source
  attribution needs an owner decision. The contract/test evidence is preserved
  but the asset is listed in `catalog/review/HOLD.json` and excluded from
  documentation, capability index, query service and capability matrix.
- **rejected**: a required check fails; record the failure and do not expose.

A tier-A asset with only self-consistency evidence cannot auto-merge. An asset
leaves the hold only after the owner records the decision and the missing
evidence; then its contract is rebound and it can be exposed. The hold is not a
second truth: the contract remains the single scientific truth while review is
pending.


## Verdict registry and gate

`catalog/review/VERDICTS.json` records one verdict per catalog asset. The gate
(`scripts/review_gate.py --check`) fails when an asset is missing, an exposed
asset is not `pass`/`pass-with-limits`, or a held asset is not `human-review`.
`not-audited` and `blocked` are never exposed. The verdict registry is a review
state, not a second scientific truth.
