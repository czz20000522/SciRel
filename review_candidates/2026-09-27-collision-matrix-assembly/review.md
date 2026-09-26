# Candidate: KN1DPy collision-matrix assembly family (two operators)

Status: development candidate prepared for expert review, to be frozen as the
pending_unapproved r67 successor of r66. Nothing here is expert approval, a
trusted version, or a public release.

## Base and comparison scope

- SciRel base: `6240995` (r66-v3 frozen, 128 assets dev40, snapshot
  `build/verification/review-2026-09-27-r66-alpha-contraction-v3`; the v1 and
  v2 r66 snapshots are preserved but superseded). r67 increments the catalog
  to 130 exact documents, version `0.1.0.dev40` -> `0.1.0.dev41`.
- Unpublished candidate pool: re-checked by relation for collision-matrix
  assembly — none exists; the baseline has the seven `scirel.collisions`
  cross-section leaves, the cylindrical velocity quadrature and the thermal
  speed scale, and (since r66) the downstream Alpha contraction leaves, but no
  assembly operator. This is a **new capability** pair closing the declared
  r66 upstream edge.
- Incoming source (read only): the saved KN1DPy bundle
  `D1待重审历史产物/KN1DPy-631d0bf1` (provisional; strict D1 withdrawn),
  implementations pinned by SHA-256
  `80fcd63681d255fbe6a2a0fc2e400d63143c9809099d1181bb30ef3266a956fe` (atomic)
  and `34358f11e3ee91fa6768c8cf89d22eb1a2edbe2707f9e58d0b91472bf1b50d06`
  (molecular). The bundle root used for the environment-gated replay is
  `SciRel/build/verification/neutral-harness-baseline-v3/inputs/l1/KN1DPy`.
- Qualified L1 consumption: none (delivery root re-checked empty; strict D1
  withdrawn). Bounded historical development evidence only.

## Proposed identity

- `scirel.kinetic.atomic-collision-matrix-assembly`, callable
  `assemble_atomic_hydrogen_collision_matrices(vr, vx, Vr2pidVr, dVx, Tnorm, mu=1.0)`
  — four `(N,N)` atomic SIG matrices (`SIG_CX`, `SIG_H_H`, `SIG_H_H2`,
  `SIG_H_P`), `N = nvr*nvx`, plus the saved arm's captured predecessor state
  (`v_v2`, `v_v`, `vr2_vx2`, `vx_vx`, `Vr2pidVrdVx`, `Vth2`) as declared
  forensic fields.
- `scirel.kinetic.molecular-collision-matrix-assembly`, callable
  `assemble_molecular_hydrogen_collision_matrices(vr, vx, Vr2pidVr, dVx, Tnorm, mu=1.0)`
  — four `(N,N)` molecular SIG matrices (`SIG_CX`, `SIG_H2_H`, `SIG_H2_P`,
  `SIG_H2_H2`) plus the same captured predecessor state.

## Material scientific differences and declared divergences

1. **Cross-section reuse instead of a second embedded copy.** The saved
   packages embed verbatim copies of the KN1DPy `sigma/` fits. This port
   evaluates the same fits through the integrated `scirel.collisions` leaves
   (coefficient- and clip-identical). On a 200,011-point energy probe spanning
   the union of the declared fit domains (all clip endpoints, the H-P 10 eV
   branch boundary, E = 0) the three elastic families of each arm match the
   source-embedded fits bit for bit; each arm's charge-exchange family differs
   by at most 2.22e-15 (atomic) / 2.21e-15 (molecular) relative, root-caused
   to the standardized `np.exp` evaluation versus the source's `np.e **`. A
   1,000,001-point log-grid root-cause probe observes up to 17
   double-precision ulp by `np.spacing`. These are sampled measurements, not
   bounds over the continuous domain; the replay tolerance for the CX
   families is set to rtol=1e-14. Fallback condition: if an expert requires
   bit-identical CX replay, the source-embedded fits would have to be
   reintroduced (a labelled second copy).
2. **The integrated leaves follow two declared output-shape conventions**
   (some wrap one leading singleton axis, some do not); the port normalizes
   both to the carrier's shape and fails closed on any other shape. This
   normalization wrapper is new glue declared in the port, not source code.
3. **Tnorm/mu scalar tightening (port-added fail-closed).** The saved arm
   accepts a size-1 array `Tnorm`/`mu` and would then produce a `(1,1)`
   `Vth2` field; this port rejects any non-0-d `Tnorm`/`mu` with a named
   `ValueError`. Registered as a deliberate divergence from the saved arm's
   rejection behavior.
4. **Declared units.** `Tnorm` is declared in eV (consistent with
   `Vth = sqrt(2*Q*Tnorm/(mu*H_MASS))`, `Q = 1.602177e-19` J/eV, and the
   integrated thermal-speed-scale relation); `vr` is declared positive (the
   validation rejects non-positive entries; no monotonicity gate), `vx`
   strictly increasing with at least one positive and one negative entry (no
   exact-symmetry gate) — matching what the validation actually enforces.
5. **Molecular SIG_CX energy factor quirk preserved verbatim**: the molecular
   CX family uses `H_MASS*Vth2/Q` (no 0.5, no `mu`; kinetic_h2.py:1045), not
   the atomic-side convention; a discriminating test guards against
   re-aligning it.
6. **No positivity gate; negative cells preserved.** `SIG_CX` is nonnegative
   on the declared domain; the three elastic families of each arm carry
   bounded negative cells intrinsic to the signed `vr2_vx2` / `vx_vx` factors,
   reproduced as-is, never clamped. Physical acceptability is an open expert
   question.
7. **Registered source-document conflict (molecular arm).** The saved
   `分子氢碰撞矩阵组装/operator.md` claims canonical 2x2 negative-cell counts
   of 2/2/4, but the reproducible computation on the saved package test's own
   canonical fixture yields 4/4/8 (the atomic document's 8/4/4 does match).
   The saved document is kept verbatim; the candidate tests assert the actual
   recomputation, and the cause is left to expert review.

## Evidence

- Direct tests: an independent broadcasting-geometry oracle built on the
  source's own embedded formulas (including the source's `np.e **` CX
  evaluation) pins the assembly semantics (rtol=1e-12, the saved packages'
  budget), plus predecessor-state capture, `SIG_CX` nonnegativity, bounded
  elastic negative cells with deterministic canonical counts, fail-closed
  carrier contracts (including the scalar tightening), input read-only
  behavior, and an end-to-end composition feeding the r66 contraction ports.
- Environment-gated replay (3 tests): SHA-256-pinned saved-arm parity —
  bit-for-bit for the elastic families and predecessor state, rtol=1e-14 for
  the CX families (see item 1), and rejection-behavior agreement.
- 17 tests total (14 direct + 3 replay); `pytest --collect-only` verified.

## Files

- `proposal/atomic_collision_matrix_assembly.py`, `proposal/molecular_collision_matrix_assembly.py`
- `proposal/test_collision_matrix_assembly.py`, `proposal/test_collision_matrix_assembly_l1.py`
- `proposal/scirel.kinetic.atomic-collision-matrix-assembly.json`,
  `proposal/scirel.kinetic.molecular-collision-matrix-assembly.json`

## Version and impact

Version `0.1.0.dev40` -> `0.1.0.dev41`; catalog 128 -> 130 exact documents.
The other 128 documents change only in the mechanical
`implementation_version` bump. The four declared `scirel.collisions`
dependencies per arm are integration dependencies of the port (the saved
package embedded the same fits); no other asset's contract changes.
