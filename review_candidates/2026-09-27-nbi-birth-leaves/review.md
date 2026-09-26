# Candidate: FIDASIM NBI birth/geometry leaf family (five operators)

Status: development candidate prepared for expert review, to be frozen as the
pending_unapproved r71 successor of r70. Nothing here is expert approval, a
trusted version, or a public release.

## Base and comparison scope

- SciRel base: `644b223` (r70-v3 frozen, 137 assets dev44, snapshot
  `build/verification/review-2026-09-27-r70-fast-ion-kinematics-v3`; v1/v2
  preserved). r71 increments the catalog to 142 exact documents, version
  `0.1.0.dev44` -> `0.1.0.dev45`.
- Unpublished candidate pool: re-checked by relation for the NBI birth
  leaves -- none exists. The baseline has the r70 kinematics leaves (DD
  anisotropy, FLR correction, DD lab energy) but no birth-state
  materialization, birth-position sampling, halo velocity sampling, pitch
  direction mapping or energy-component velocity scaling.
- Incoming source (read only): the saved FIDASIM bundle in the sibling main
  SciRel checkout at
  `D:/software/PyCharm 2025.3.3/workspace/SciRel/build/verification/neutral-harness-baseline-v3/inputs/l1/FIDASIM`
  (198 operator packages; read-only, zero writes; not inside this intake
  worktree). Saved implementations support bounded historical development
  comparison only; the qualified L1 delivery root was re-checked empty
  (0 items) at batch start.

## Proposed identity

- `scirel.fusion.nbi-energy-component-velocity`
  (`scale_nbi_velocity_for_energy_component`) -- full/half/third
  energy-component velocity scaling with the source's Float32 divisor.
- `scirel.fusion.nbi-component-initial-state`
  (`materialize_nbi_component_initial_state`) -- six-level initial-state
  density materialization (`states(1) = nneutrals*fraction/dv`).
- `scirel.fusion.thermal-halo-velocity-sampling`
  (`sample_halo_velocity`) -- thermal-halo birth velocity from
  caller-owned standard-normal draws.
- `scirel.fusion.beam-grid-cell-sampling` (`sample_beam_grid_cell`) --
  Cartesian beam-grid cell birth position from caller-owned uniform draws.
- `scirel.fusion.pitch-gyro-velocity-direction`
  (`pitch_gyro_to_velocity_direction`) -- pitch/gyro-angle to unit
  velocity direction in a caller-supplied orthonormal frame.

## Deduplication judgment and why these five are separate identities

- Versus r70: no relation overlap -- r70 covers DD neutron weighting and
  the FLR position correction; this batch covers the birth state
  (density/level population), birth position (grid cell) and birth
  direction (pitch/gyro frame) for the same NBI chain, which r70 consumes
  but does not provide.
- Versus the baseline `shifted-maxwellian-seed` (KN1DPy): that asset builds
  a normalized distribution on a cylindrical velocity mesh; the halo leaf
  maps one particle's caller-owned normal draws to a velocity -- different
  domain, output and unit bookkeeping. No consolidation.
- The five leaves are mutually independent relations (energy scaling,
  level materialization, thermal sampling, position sampling, direction
  mapping), each with its own saved package; none duplicates another's
  formula or contract.
- Excluded from this batch on evidence: the MPI reduction/door packages
  (NBI three-spectrum, NPA weights) are runtime gates, not scientific
  relations; the DCX series depends on a spectral-line state not yet
  extracted.

## Material scientific differences and declared divergences

1. **Float32 divisor quirk preserved verbatim** in the velocity scaling
   (`sqrt(Float32(efrac))`); the last-ulp deviation from a Float64 divisor
   is quantified by exact-equality tests, not re-rounded.
2. **Registered input hardening**: finite positive scalar injection speed
   (NaN passes the source's `vinj <= 0` check), strict integer component
   index 1/2/3 (bools and float 1.0 pass the source's tuple-membership
   equality), `nlevels` exactly 6.
3. **Registered overflow/underflow gates with direct witnesses**: the
   weight-factor sum (three finite max-float fractions overflow to Inf;
   the saved arm returns rate 0 with an Inf factor), the total rate, the
   per-cell density (a finite rate times a tiny volume overflows -- the
   density gate catches what the rate gate misses), the halo velocity and
   thermal speed (plus the denominator-underflow case), the beam-grid
   affine sum, and the velocity scaling itself (a norm-overflowing finite
   ray with the max finite speed).
4. **Contract normalization (exception type only)**: a denominator
   underflowing to exactly 0.0 makes the saved halo arm raise a bare
   ZeroDivisionError; this port raises the common ValueError. The accepted
   domain is unchanged.
5. **Caller-owned randomness**: the halo and beam-grid leaves take explicit
   draws as inputs; no RNG is bound and identical draws replay identically.
6. **Zero power is a valid input** for the initial-state materialization
   (an all-zero state with a finite zero rate); the exact document states
   the real sign contract, not "positive power".
7. **Pitch identity is tolerance-bounded**: `dot(direction, b_unit) ==
   pitch` is exact only in an exactly-orthonormal frame; the accepted
   frames carry a 1e-12 orthonormality tolerance, so the identity carries
   the same tolerance. The direct tests assert the exact identity only in
   the canonical frame and the tolerance-bounded identity in random QR
   frames. The earlier draft's `sin(gyro)*cos(angle)*a` formula was wrong
   (there is no separate gyro polar angle); the saved `sqrt(1-pitch^2)`
   closed form is the contract.

## Evidence

- 9 direct tests: exact closed-form recomputation for all five leaves
  (Float32 divisor, level-1-only population, thermal-speed formula,
  zero-mean affine map, pitch decomposition in canonical and random QR
  frames), structural identities (unit-norm direction, midpoint/zero-width
  collapse, determinism under identical draws, zero-temperature collapse),
  and the registered hardenings with the discriminating witnesses listed
  above. Per-call seeded fixtures; no module-level RNG.
- No separate replay file: the FIDASIM saved packages ship package-level
  oracles rather than a pinned source-runtime replay target; the saved
  implementations' content digests are recorded as reference evidence in
  `build/test-evidence-r71.md` (no automated drift detection runs against
  them).
- 9 tests total; full-tree delta reconciles exactly (1508 -> 1524 source
  with replay; 1354/197 -> 1370/197 installed).

## Files

- `proposal/nbi_energy_component_velocity.py`, `proposal/nbi_component_initial_state.py`,
  `proposal/halo_velocity_sampling.py`, `proposal/beam_grid_cell_sampling.py`,
  `proposal/pitch_gyro_direction.py`
- `proposal/test_nbi_birth_leaves.py`
- `proposal/scirel.fusion.nbi-energy-component-velocity.json`,
  `proposal/scirel.fusion.nbi-component-initial-state.json`,
  `proposal/scirel.fusion.thermal-halo-velocity-sampling.json`,
  `proposal/scirel.fusion.beam-grid-cell-sampling.json`,
  `proposal/scirel.fusion.pitch-gyro-velocity-direction.json`

## Version and impact

Version `0.1.0.dev44` -> `0.1.0.dev45`; catalog 137 -> 142 exact documents.
The other 137 documents change only in the mechanical
`implementation_version` bump. No other asset's contract changes.
