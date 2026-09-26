# Candidate: KN1DPy transport-step family (three operators)

Status: development candidate prepared for expert review, to be frozen as
the pending_unapproved r63 successor of r62. Nothing here is expert
approval, a trusted version, or a public release.

## Base and comparison scope

- SciRel base: `965028c` (r62, cross-mesh distribution interpolation,
  113 assets dev35, `pending_unapproved`).
- Unpublished candidate pool: re-checked by relation for upwind transport
  coefficient assembly, bidirectional generation propagation, or Boltzmann
  RHS assembly — none exists. All three incoming leaves are **new
  capabilities**.
- Incoming source (read only): the saved KN1DPy bundle
  `D1待重审历史产物/KN1DPy-631d0bf1` (provisional; strict D1 withdrawn),
  three operator packages, each implementation pinned by SHA-256. All
  imports of the saved tree ran `python -B` with
  `PYTHONDONTWRITEBYTECODE=1`; the round wrote nothing into the saved tree.
- Qualified L1 consumption: none. The qualified L1 delivery root is empty
  (re-checked this round) and KN1DPy's strict D1 qualification has been
  withdrawn. Every comparison is bounded historical development evidence.

## Inventory (all rows candidate-ready)

| Saved callable | Disposition | Proposed SciRel identity | Material differences | Evidence (shared across the family) |
| --- | --- | --- | --- | --- |
| `assemble_neutral_upwind_transport_coefficients` (anchor `kinetic_h.py:1170-1249`) | add new capability | scirel.kinetic.neutral-upwind-transport-coefficients | **no repair** — the saved first-order upwind trapezoidal scheme (Ak/Bk/Fk/Ck/Dk/Gk) is reproduced bit for bit; the operator involves x and vx axes only (no vr) | shared: 10 direct + 4 replay |
| `propagate_neutral_generation` (anchor `kinetic_h.py:1260-1275; kinetic_h2.py:1385-1415`) | add new capability | scirel.kinetic.neutral-generation-propagation | **no repair** — first_flight and scattered bidirectional propagation reproduced bit for bit; Bk is the scattered-branch forward source coefficient (not first-flight); Fk is the first-flight forward source term; incoming_boundary applies only to the positive-vx branch; negative-vx right boundary is fixed zero | shared: 10 direct + 4 replay |
| `assemble_neutral_boltzmann_rhs` (anchor `kinetic_h.py:1636-1646; kinetic_h2.py:1794-1803`) | add new capability | scirel.kinetic.neutral-boltzmann-rhs | **no repair** — the signed sum Vth*(S + Beta_CX - alpha_c*f + OmegaM + Swall) is reproduced bit for bit; NaN thermal speed is rejected on both arms | shared: 10 direct + 4 replay |

Relations kept distinct and not merged: upwind coefficients produce the
inputs to propagation; BoltzmannRHS is a diagnostic assembly consuming
different upstream terms (collision frequency, source sums, total
distribution). The three form a coherent transport-step family but serve
different roles in the saved source pipeline.

## Declared domain tightenings (pre-review, r63 round)

1. **Upwind x finiteness**: NaN in x passes the monotonic predicate
   (`diff(x) <= 0` is False for NaN) and produces NaN coefficients; this
   asset fail-closes with a named ValueError.
2. **Upwind vx finiteness**: inf vx is accepted by the saved arm and
   produces NaN coefficients; this asset fail-closes.
3. **Propagation vx finiteness**: NaN vx is silently accepted by the saved
   arm and the corresponding generation slice is left zero; this asset
   fail-closes.
**No divergence on BoltzmannRHS Tnorm**: the saved arm already rejects
NaN/inf thermal speed with a ValueError; this asset reproduces the same
behavior. Both arms agree (confirmed by the saved-arm probe and
`test_the_saved_rejection_behavior_agrees_exactly`).

All three divergences are documented in the exact documents' assumptions
and pinned by regression tests.

## Boundary semantics (documented)

- `incoming_boundary` applies only to the positive-vx branch (the forward
  propagation entry point); the negative-vx branch starts from zero at the
  right boundary. This is the saved contract, not a defect.
- Bk is the scattered-branch forward source coefficient; Fk is the
  first-flight forward source term. The exact document originally mislabeled
  Bk as a first-flight coefficient; corrected.

## Files

- `proposal/upwind_transport_coefficients.py`,
  `proposal/neutral_generation_propagation.py`,
  `proposal/neutral_boltzmann_rhs.py`
- `proposal/test_transport_step.py` (10 direct),
  `proposal/test_transport_step_l1.py` (4 replay)
- `proposal/scirel.kinetic.neutral-upwind-transport-coefficients.json`,
  `proposal/scirel.kinetic.neutral-generation-propagation.json`,
  `proposal/scirel.kinetic.neutral-boltzmann-rhs.json`

## Public API and dependency impact

Three new public callables in `scirel.kinetic` and the root namespace;
three new exact documents; version `0.1.0.dev36` -> `0.1.0.dev37`; catalog
113 -> 116 assets. The other 113 exact documents change only in their
mechanical `implementation_version` bump. No existing test assertion
weakened.

## Evidence ceiling

The environment-gated replay establishes bit-identical agreement with the
saved formal operator on the compared inputs and rejection paths only.
No test establishes the transport model against an external numerical PDE
solver or independent physical reference: the saved package records that
residual as `validation_oracle_gap`. KN1DPy's strict D1 qualification is
withdrawn; the saved bundle supports bounded historical development
comparison only. Expert recognition, version-level trust and distribution
licensing remain pending.
