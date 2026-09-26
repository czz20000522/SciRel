# Candidate: KN1DPy Omega aggregation family (two operators)

Status: development candidate prepared for expert review, to be frozen as the
pending_unapproved r68 successor of r67. Nothing here is expert approval, a
trusted version, or a public release.

## Base and comparison scope

- SciRel base: `3554469` (r67-v1 frozen, 130 assets dev41, snapshot
  `build/verification/review-2026-09-27-r67-collision-matrix-assembly-v1`).
  r68 increments the catalog to 132 exact documents, version
  `0.1.0.dev41` -> `0.1.0.dev42`.
- Unpublished candidate pool: re-checked by relation for the Omega
  aggregation — none exists; the baseline's `elastic-frequency-channels` and
  `elastic-regeneration-aggregation` assets declare "species-pair Omega
  evaluations upstream" as their input, and the r66/r67 Alpha-contraction and
  SIG-assembly outputs are the declared predecessors, but no Omega operator
  exists. This is a **new capability** pair closing that declared edge.
- Incoming source (read only): the saved KN1DPy bundle
  `D1待重审历史产物/KN1DPy-631d0bf1` (provisional; strict D1 withdrawn),
  implementations pinned by SHA-256
  `5b80ea51cf51490208c5e39d71ca5a56c9a4610943a703e066cbbfa4ea6d9038` (atomic,
  kinetic_h.py:1116-1188) and
  `13b001078958fa6fd8a819e65340a3a4e22fbfb6a3dbb58e4451db92e81f78d9`
  (molecular, kinetic_h2.py:1232-1296). The bundle root used for the
  environment-gated replay is
  `SciRel/build/verification/neutral-harness-baseline-v3/inputs/l1/KN1DPy`.
- Qualified L1 consumption: none (delivery root re-checked empty; strict D1
  withdrawn). Bounded historical development evidence only.

## Proposed identity

- `scirel.kinetic.atomic-omega-aggregation`, callable
  `assemble_atomic_hydrogen_omega_frequencies(fH, nH, Alpha_H_P, Alpha_H_H2,
  SIG_H_H, Vr2pidVr, dVx, vr, vx, Vth, vxi, vxH2, MH_H_sum, vr2_2vx2_2D,
  DeltaVx_tol=0.01, Wpp_tol=0.001, H_P_EL=True, H_H2_EL=True, H_H_EL=True)` —
  `VxH`, `Omega_H_P`, `Omega_H_H2`, `Omega_H_H`, `Omega_EL`, `Wperp_paraH`,
  each `(nx,)`.
- `scirel.kinetic.molecular-omega-aggregation`, callable
  `assemble_molecular_hydrogen_omega_frequencies(...)` — `VxH2`,
  `Omega_H2_P`, `Omega_H2_H`, `Omega_H2_H2`, `Omega_EL`, `Wperp_paraH2`,
  each `(nx,)`.

## Material scientific differences and declared divergences

1. **Branch-selector asymmetry preserved verbatim.** The atomic Wperp branch
   test is `sum(MH_H_sum) <= 0` (direct vr2 projection at zero or negative
   totals); the molecular test is `sum(MH2_H2_sum) < 0` (a zero accumulator
   takes the accumulated-moment path). A discriminating oracle test pins the
   two arms onto opposite branches at exactly zero.
2. **Source-exact division ordering preserved.** The molecular Omega_H2_P
   denominator `(nH2*DeltaVx)` divides outside the sum while the Omega_H2_H
   denominator divides inside it (kinetic_h2.py:1257 vs :1270); the oracle
   reproduces both orderings and the replay is bitwise.
3. **Registered fail-closed hardenings (port-added, diverging from the saved
   arm's silent behavior):**
   - non-positive `nH`/`nH2` with any elastic channel enabled raises
     `ValueError` (the saved arm silently skipped the whole Omega block and
     returned zeros);
   - `Vth`, `DeltaVx_tol`, `Wpp_tol` must be finite positive scalars (the
     saved arm validates none: a zero `Vth` or a NaN tolerance — which
     bypasses the arm's `tol <= 0` check — flows into the divisions);
   - every returned field is finally checked finite (the saved arm returns
     NaN/Inf silently, e.g. the source-recorded hazard that the legacy
     `sign(0)=0` makes the floored DeltaVx denominator exactly zero on
     symmetric drift difference — a legitimate-input NaN now rejected
     instead of returned).
4. **Legacy semantics preserved verbatim:** the symbolic `sign`
   (`int(x>0)-int(x<0)`, source note "replace with np.sign" — a
   normalization expert question), the `max(Omega_*, 0)` clamps (outputs
   nonnegative by construction, unlike the signed Alpha/SIG families), the
   source-hardcoded `DeltaVx_tol=0.01`/`Wpp_tol=0.001` defaults, and the
   branch-time `SIG @ F(fH)` inline re-contraction on the Fortran-order
   carrier (C-order preallocated buffer layout included).
5. **No positivity gate beyond density, no clamp of Wperp_paraH**: the
   perpendicular second moment is returned as computed (its sign drives the
   Omega_H_H direction); only the Omega families are clamped.

## Evidence

- Direct tests: independent closed-form reduction oracles over manufactured
  inputs for all six outputs per arm (saved packages' 1e-12/1e-9 budgets),
  covering both Wperp branches, the inside/outside-the-sum division ordering,
  the Fortran-order versus C-order SIG carrier discriminator, zero clamps,
  the exact `Omega_EL` sum, channel-switch gating, input immutability, the
  registered scalar-tolerance and density hardenings, and the non-finite
  output gate (extreme-`Vth` overflow probe). Fixture random sources are
  freshly seeded per call so single affected-test runs see byte-identical
  carriers to the whole-file run.
- Environment-gated replay (5 tests): SHA-256-pinned saved-arm parity, all
  six outputs bit for bit on both branch-path fixtures per arm, plus
  rejection agreement restricted to boundaries where the saved arm itself
  raises.
- 24 tests total (19 direct + 5 replay); `pytest --collect-only` verified.

## Files

- `proposal/atomic_omega_aggregation.py`, `proposal/molecular_omega_aggregation.py`
- `proposal/test_omega_aggregation.py`, `proposal/test_omega_aggregation_l1.py`
- `proposal/scirel.kinetic.atomic-omega-aggregation.json`,
  `proposal/scirel.kinetic.molecular-omega-aggregation.json`

## Version and impact

Version `0.1.0.dev41` -> `0.1.0.dev42`; catalog 130 -> 132 exact documents.
The other 130 documents change only in the mechanical
`implementation_version` bump. Each arm declares two integration
dependencies (the r66 contraction and r67 assembly assets); no other
asset's contract changes.
