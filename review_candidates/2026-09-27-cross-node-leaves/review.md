# Candidate: FIDASIM cross-node leaf family (five operators)

Status: development candidate prepared for expert review, to be frozen as the
pending_unapproved r72 successor of r71. Nothing here is expert approval, a
trusted version, or a public release.

## Base and comparison scope

- SciRel base: `f1f07e6` (r71-v2 frozen, 142 assets dev45, snapshot
  `build/verification/review-2026-09-27-r71-nbi-birth-leaves-v2`; v1
  preserved). r72 increments the catalog to 147 exact documents, version
  `0.1.0.dev45` -> `0.1.0.dev46`.
- Unpublished candidate pool: re-checked by relation — none exists; the
  baseline has no D-D rate-table interpolation, no relative-energy leaf, no
  marker allocation, no NBI normalization with the CODATA e0 contract, and
  no cell-directed ray geometry.
- Incoming source (read only): the saved FIDASIM bundle in the sibling main
  SciRel checkout (read-only, zero writes). Saved implementations support
  bounded historical development comparison only; the qualified L1 delivery
  root was re-checked empty (0 items) at batch start.

## Proposed identity

- `scirel.fusion.dd-rate-table-interpolation`
  (`dd_reaction_rate_per_s`, N9) — bilinear log10 rate table interpolation
  with per-branch axis and density scaling.
- `scirel.fusion.fast-ion-relative-energy`
  (`calculate_fast_ion_relative_energy`, N9) — E_rel =
  v2_to_E_per_amu * A * |v_i - v_rot|^2.
- `scirel.fusion.mc-marker-weight-allocation`
  (`allocate_mc_markers_by_weight`, N7) — get_nlaunch marker allocation
  with caller-owned CDF draws and F-order inverse-CDF sampling.
- `scirel.fusion.nbi-injected-neutrals-normalization`
  (`normalize_nbi_injected_neutrals`, N2) — ndmc power-to-neutral
  normalization using the CODATA 2018 elementary charge.
- `scirel.fusion.nbi-cell-directed-ray` (`nbi_cell_directed_ray`, N2) —
  mc_nbi_cell source-to-cell ray with aperture acceptance and Gaussian
  divergence weight.

## Framework-node attribution (from the saved program_framework_map)

These five leaves span three framework nodes — N2
neutral_beam_source_sampling (normalization, cell ray), N7
fast_ion_fida_response (marker allocation), N9 neutron_response (rate
table, relative energy). They are cross-node independent leaves; the saved
framework map emits no TaskGraph composing them, so no cross-node
composition test is included and that composition evidence gap stays
declared.

## Deduplication judgment

- Versus the r71 initial-state leaf: that leaf pins the source's
  1.60217733e-19 elementary charge as its contract; this batch's
  normalization leaf keeps the CODATA 2018 1.602176634e-19 explicitly, as
  the saved program map records as a distinct contract (the e0 difference
  is an open expert adjudication between N2's two normalization paths).
  No consolidation.
- Versus Bosch-Hale reactivity: that asset is an analytic Maxwellian
  fit; this batch's D-D rate leaf is a table interpolation with caller-
  supplied frozen tables — different relation, no overlap.
- The five leaves are mutually independent (table lookup, kinematic
  energy, marker counting, normalization, ray geometry).

## Material scientific differences and declared divergences

1. **Registered overflow/finite-output gates** with discriminating
   witnesses: DD rate exponentiation (finite extreme table contents → Inf
   in the saved arm), relative-beam energy (max-finite velocities), NBI
   normalization (weight factor and rate/density overflow), cell-ray
   outputs.
2. **Registered conservation gate**: marker allocation conserves
   requested_markers; the saved arm has no such check.
3. **Strict integer branch index**: bool and float branch indices pass the
   source's isinstance check; this port rejects them.
4. **Saved quirks preserved verbatim**: the theta_z-uses-focy (not focz)
   ray weight quirk (pinned by the saved package's own probe), the
   Float32 energy-component divisor in the ray velocity, the
   uniform-first-spacing interpolation on a non-uniform energy axis where
   applicable, and the beyond-last-interval zero return.
5. **Zero power is valid** for the normalization (all-zero result); the
   real sign contract is stated, not "positive power".

## Evidence

- 16 direct tests: independent closed-form recomputation for the bilinear
  interpolation and relative energy, F-order CDF recomputation for marker
  allocation, count conservation, the source formula for NBI
  normalization, the saved package's own ray probes (centerline
  acceptance, theta_z quirk), the Float32 divisor identity, and the
  registered hardenings with discriminating witnesses. Per-call seeded
  fixtures.
- No separate replay file: the FIDASIM saved packages ship package-level
  oracles rather than a pinned source-runtime replay target; the saved
  implementations' content digests are recorded as reference evidence in
  `build/test-evidence-r72.md`.
- 16 tests total; full-tree delta reconciles exactly (1524 -> 1540 source
  with replay; 1370/197 -> 1386/197 installed).

## Files

- `proposal/dd_rate_table_interpolation.py`, `proposal/fast_ion_relative_energy.py`,
  `proposal/mc_marker_weight_allocation.py`, `proposal/nbi_injected_neutrals_normalization.py`,
  `proposal/nbi_cell_directed_ray.py`
- `proposal/test_cross_node_leaves.py`
- `proposal/scirel.fusion.dd-rate-table-interpolation.json`,
  `proposal/scirel.fusion.fast-ion-relative-energy.json`,
  `proposal/scirel.fusion.mc-marker-weight-allocation.json`,
  `proposal/scirel.fusion.nbi-injected-neutrals-normalization.json`,
  `proposal/scirel.fusion.nbi-cell-directed-ray.json`

## Version and impact

Version `0.1.0.dev45` -> `0.1.0.dev46`; catalog 142 -> 147 exact documents.
The other 142 documents change only in the mechanical
`implementation_version` bump. No other asset's contract changes.
