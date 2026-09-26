# Candidate: FIDASIM fast-ion kinematics family (two operators)

Status: development candidate prepared for expert review, to be frozen as the
pending_unapproved r70 successor of r69. Nothing here is expert approval, a
trusted version, or a public release.

## Base and comparison scope

- SciRel base: `33fa7db` (r69-v2 frozen, 135 assets dev43, snapshot
  `build/verification/review-2026-09-27-r69-gseq-green-v2`). r70 increments
  the catalog to 137 exact documents, version `0.1.0.dev43` -> `0.1.0.dev44`.
- Unpublished candidate pool: re-checked by relation for fast-ion kinematics
  — none exists. The baseline fusion domain has the Bosch-Hale reactivity and
  the D-D neutron lab-energy relations; no anisotropy weighting or
  guiding-center correction exists.
- Incoming source (read only): the saved **FIDASIM** bundle, which lives in
  the sibling main SciRel checkout at
  `D:/software/PyCharm 2025.3.3/workspace/SciRel/build/verification/neutral-harness-baseline-v3/inputs/l1/FIDASIM`
  (198 operator packages; read-only imports, zero writes; not inside this
  intake worktree). Saved implementations support bounded historical
  development comparison only; the qualified L1 delivery root was re-checked
  empty (0 items) at batch start.

## Proposed identity

- `scirel.fusion.dd-neutron-emission-anisotropy`
  (`dd_neutron_kinematic_anisotropy`) — Brown-Jarmie coefficient-table
  interpolation and directional normalization for one D(d,n)3He emission
  event.
- `scirel.fusion.first-order-larmor-correction`
  (`first_order_larmor_guiding_center_correction`) — guiding-center to
  particle mapping under the source's FLR orders 0, 1 or 2.

## Reuse judgment: D-D lab energy stays on the existing asset (no new identity)

The saved FIDASIM package `DD中子运动学能量` implements the same D-D neutron
lab-energy relation as the already-integrated
`scirel.fusion.dd-neutron-lab-energy` asset: identical inputs (two deuteron
velocities + detector unit vector), same keV output, same non-relativistic
closed form `E_cm + E_boost + 2*sqrt(E_cm*E_boost)*cos(theta)`. The
integrated asset additionally carries the documented repair (a non-positive
lab energy falls back to the CM energy instead of the source's
near-Q-value artifact) and declares the constant `angular_weight = 1.0`
field, which is not a scientific capability. Disposition: **reuse / source
mapping, not a third public operator**. The saved package is referenced from
the dossier's provenance chain only; creating a variant identity for it would
duplicate a relation for a constant field and a source defect the integrated
asset already repairs.

The two new operators have no baseline equivalent: no anisotropy weighting
and no guiding-center mapping exist in the catalog.

## Material scientific differences and declared divergences

1. **Anisotropy domain bound (general form).** The Brown-Jarmie table top is
   116.909 keV; the declared domain is `0.5*scale*|v1 - vrot|^2 < 116.909`,
   i.e. `|v1 - vrot| < sqrt(2*116.909/scale)`. Inputs at or beyond the table
   top are rejected fail-closed (no extrapolation); the saved package's own
   probe (`vrel = 200 cm/s`, scale 0.01, ehalf = 200 keV) is such a rejection.
2. **Source interpolator quirk preserved verbatim**: the source's 1-D
   interpolator uses the first table spacing as a uniform grid even though
   the energy table is non-uniform. Recorded as source behavior, not
   presented as accurate interpolation.
3. **Norm-overflow containment documented, not overclaimed.** Extreme
   neutron velocities overflow the vector norms, but the angle algebra's own
   fallback (`abs(k0*sinphi) <= 1` false for NaN) forces `costheta` to 0 and
   the anisotropy stays finite — verified on extreme probes (result 1.0); a
   final non-finite output gate guards remaining combinations. The saved arm
   has no such gate.
4. **FLR output gates (registered hardening).** The saved implementation
   returns Inf silently when the position-radius subtraction overflows
   (recorded chain: position 1e308, velocity -1e308, B 1e-8 → finite radius
   about -1.04e308, position subtraction → +Inf). This port checks every
   returned field (particle position, gyro radius, scale factor) and raises.
5. **FLR source window and axis singularity preserved**: the order-2 scale
   acceptance window `(0, 2)` and the on-axis undefinedness are fail-closed
   in the source and kept.
6. **flr_order type strictness preserved**: exactly `int` 0/1/2 (bools and
   floats rejected); `None` selects the historical `flr_enabled` contract.

## Evidence

- 10 direct tests: the saved package's frozen forward probe (rtol 1e-14),
  rotational symmetry in the transverse neutron direction, positivity over
  in-domain random fixtures, the upper-table rejection (general boundary),
  norm-overflow containment on extreme probes, FLR order 0 identity, order-1
  exact cross-product radius with perpendicularity and displacement, the
  order-2 uniform-field scale exactly 1 and the recorded outside-window
  rejection, the on-axis undefinedness, missing-state rejection, and the
  recorded position-subtraction overflow chain.
- No separate replay file: the FIDASIM saved packages ship package-level
  oracles rather than a pinned source-runtime replay target; the saved
  implementations' content digests are recorded as reference evidence in
  `build/test-evidence-r70.md` (no automated drift detection runs against
  them).
- 10 tests total; full-tree delta reconciles exactly (1498 -> 1508 source
  with replay; 1344/197 -> 1354/197 installed).

## Files

- `proposal/dd_neutron_kinematic_anisotropy.py`, `proposal/first_order_larmor_correction.py`
- `proposal/test_fast_ion_kinematics.py`
- `proposal/scirel.fusion.dd-neutron-emission-anisotropy.json`,
  `proposal/scirel.fusion.first-order-larmor-correction.json`

## Version and impact

Version `0.1.0.dev43` -> `0.1.0.dev44`; catalog 135 -> 137 exact documents.
The other 135 documents change only in the mechanical
`implementation_version` bump. The fusion domain draft
(`docs/domains/fusion.md`) gains the two relations and the explicit
reuse disposition of the D-D lab-energy relation.
