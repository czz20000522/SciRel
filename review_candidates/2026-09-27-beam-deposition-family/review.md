# Candidate: FIDASIM beam-neutral multi-segment deposition family (three operators + one composition graph)

Status: development candidate prepared for expert review, frozen as the
pending_unapproved r78 successor of r77-v3. Nothing here is expert
approval, a trusted version, or a public release.

## Base and comparison scope

- SciRel base: r77-v3 (commit `de6b410`, 158 assets `0.1.0.dev54`, snapshot
  `build/verification/review-2026-09-27-r77-dcx-colrad-family-v3`).
  r78 increments the catalog to 162 exact documents, version
  `0.1.0.dev54` -> `0.1.0.dev55`. The 158 pre-existing documents change in
  the mechanical `implementation_version` bump except
  `scirel.fusion.collisional-radiative-state-advance`, which additionally
  carries the unit-label contract repair described below.
- Unpublished candidate pool: re-checked by relation — none exists; the
  baseline has no DDA segment traversal, no N3/N4 deposition handoff, no
  NDMC producer and no segment-deposition composition.
- Incoming source (read only): the saved FIDASIM bundle in the sibling main
  SciRel checkout (`build/verification/neutral-harness-baseline-v3/inputs/l1/FIDASIM`,
  read-only, zero writes). The qualified L1 delivery root was re-checked
  empty (0 items) at batch start.

## Proposed identity

- `scirel.fusion.beam-grid-ray-segment-tracking`
  (`trace_beam_grid_ray_segments`, N3) — deterministic DDA segment
  traversal with the source's two-record plasma-crossing split, adaptive
  subsegments, one-based indices and terminal policies.
- `scirel.fusion.n3-n4-segment-deposition`
  (`assemble_n3_n4_segment_deposition`, N3/N4 seam) — per-track N4
  handoff verification and the source marker normalization
  (`dens/nlaunch`, `photons/nlaunch`, population-loss flux, accumulated
  deposition).
- `scirel.fusion.ndmc-deposition-producer`
  (`run_ndmc_deposition_producer`, N3) — the source-faithful `nneutrals`
  (e0 = 1.60217733e-19), per-fraction initial-state gate and the
  `store_neutrals` full/half/third population accumulation plus
  `flux_tot`.
- `scirel.fusion.beam-neutral-segment-deposition-loop`
  (`deposit_beam_neutral_segments`, kind task_graph, N3) — the saved
  束中性逐段碰撞辐射沉积图: source-ordered composition
  deposition_initialization -> beam_grid_track -> local_state_sequence ->
  n4_cell_update_handoff -> deposition, with carried-state feedback.

## Public-asset decision for the two saved validation operators

The saved bundle declares `N3逐段沉积初态规范化` and
`N3局域等离子体原子快照规范化` as separate operators. Review
finding: both are data-edge validation gates — they return caller data
essentially unchanged and compute no scientific relation — while no
integrated SciRel public operator is a pure pass-through validator (the
thinnest, `dcx-thermal-species-selection`, still emits a used quantity;
`nbi-component-initial-state` and `mirror-total-pressure` compute real
relations). Decision: both execute as graph-internal helpers of the
deposition loop, reproducing the saved contracts verbatim (registered
deviation from the saved packaging); standalone promotion is deferred
until a second consumer exists (e.g. real-HDF5 table drivers).

## Dimensional reconciliation (reviewer findings, pending expert adjudication)

These are reviewer findings with cited source and existing documents;
they are not human expert approval, and the unit questions below stay
open for adjudication.

1. **The N3/N4 chain carries rate-density states (cm^-3 s^-1)**: the
   source seeds `states(1) = nneutrals*fraction/dv` with `nneutrals` in
   particles/s (saved anchor src/fidasim.f90:13016-13057). The integrated
   `nbi-component-initial-state` asset already labels this
   `initial_state_rate_per_volume_cm_inv3_s_inv` (cm^-3 s^-1, "the
   source's implicit 1 s convention is not proven"). Consequences:
   `(sum(previous)-sum(next))/nlaunch` is cm^-3 s^-1 and
   `flux*dv` is particles/s, so `deposited_particles_per_s` is correctly
   labeled; the saved arm's `*_cm_inv3` state field names mislabel the
   carried unit, and the new public names use the precise
   `*_cm_inv3_s_inv` form (no pre-release compatibility burden).
2. **Colrad unit labels re-audit**: the colrad advance is unit-agnostic
   linear algebra; with rate-density inputs its integrated density is
   cm^-3 (matching `store_neutrals`' `pop%dens += dens/nlaunch` into
   cm^-3 arrays) and its photon output is cm^-3 s^-1 (matching the N3
   handoff's `photons_per_cm3_s`). The frozen r77
   `collisional-radiative-state-advance` document labels (states cm^-3,
   integrated cm^-3 s, photons s^-1) are inconsistent with its own
   family's initial-state output (cm^-3 s^-1) and with this chain.
   Resolution: the labels are corrected in the r78 successor documents
   as a development contract repair with unchanged arithmetic; the
   frozen r77-v3 snapshot bytes keep the earlier labels. A direct
   composition claim is not made: the N4 record remains an explicit
   external caller capability, exactly as the saved graph declares
   ("caller separately composes N4").
3. **Signed segment flux**: the source's
   `flux = (iflux - sum(states))/nlaunch` is signed, and the colrad
   advance drives a net level-population gain over a segment whenever
   the rate matrix's inflow (population) terms outweigh its losses
   (a loss-only matrix with all column sums <= 0 cannot produce a gain).
   The witness uses the integrated
   `collisional-radiative-state-advance` with such a matrix and flows
   the resulting handoff through the producer end to end
   (`test_producer_colrad_population_gain_path_is_consistent`).
   The NDMC producer therefore requires only finiteness (source-faithful
   signed accumulation); the saved arm's documented nonnegativity and
   its implementation's rejection of negative records are recorded as a
   bounded incompatibility for expert adjudication.
4. **e0 fork (pre-existing inter-asset divergence)**:
   `nbi-injected-neutrals-normalization` uses the CODATA 2018 value
   1.602176634e-19 while `nbi-component-initial-state` and this
   producer's gate use the source value 1.60217733e-19 (frozen trace
   rel 0.0 vs ~4.34e-7). The source-faithful gate deliberately rejects a
   CODATA-e0 normalization; which constant the frozen source should
   standardize on remains with expert adjudication.
5. **nlaunch normalization semantics**: the source divides
   `dens/nlaunch` before `store_neutrals`, so consumed records carry
   per-marker-normalized densities; callers must not re-normalize. The
   declaration form stays with expert adjudication.

## Registered hardenings (with discriminating witnesses)

- Genuine-integer track limits, sample indices and grid shapes; bools,
  `np.bool_` and whole-number floats rejected (the saved arm's
  `isinstance(int)`/`astype(int)` accepted bools and truncated floats).
- Genuine finite scalar gates for `nlaunch`, cell volume, segment
  duration and prior deposition (bools and `np.bool_` rejected,
  including the graph-internal initialization and snapshot helpers).
- Non-numeric N4 record fields raise ValueError instead of the saved
  arm's raw TypeError.
- Negative N4 `dens_cm_inv3` or `photons_per_cm3_s` fail closed (the
  saved arm's own contract declares them nonnegative but its
  implementation only rejected negative next states).
- Genuine transition-table knot counts in the snapshot helper (the
  saved arm's `int()` silently truncated fractional values).
- Accumulated NDMC populations must stay finite.

## Saved quirks preserved verbatim

The zero-velocity empty traversal, the 50-subdivision crossing split,
the crossing-limit segment pop, the adaptive count/cap formula, the
source node order of the deposition loop (non-interchangeable), the
vacuum-segment zero-temperature acceptance, and the in-grid
`store_neutrals` accumulation order (per-record `flux*dv`, unpermuted).

## Evidence

- 29 direct tests in `tests/operator_contracts/test_beam_deposition_family.py`:
  saved probes for all four assets, an end-to-end colrad witness (the
  integrated eigen-advance drives a net population gain through a
  physically shaped matrix and the signed handoff flows into the
  producer), provider/record contract rejections, and the registered
  hardenings.
- No separate replay file: the FIDASIM saved packages ship package-level
  oracles; the saved implementations' content digests are recorded per
  asset in the exact documents and `build/test-evidence-r78.md`.
- Pre-freeze review: the public-asset decision, dimensional
  reconciliation, signed-flux cross-asset check, np.bool_ scalar gates,
  fractional knot counts and negative expected totals were raised as
  reviewer findings and resolved above before freeze.

## Files

- `proposal/beam_grid_ray_segment_tracking.py`,
  `proposal/n3_n4_segment_deposition.py`,
  `proposal/ndmc_deposition_producer.py`,
  `proposal/beam_neutral_segment_deposition_loop.py`
- `proposal/test_beam_deposition_family.py`
- `proposal/scirel.fusion.beam-grid-ray-segment-tracking.json`,
  `proposal/scirel.fusion.n3-n4-segment-deposition.json`,
  `proposal/scirel.fusion.ndmc-deposition-producer.json`,
  `proposal/scirel.fusion.beam-neutral-segment-deposition-loop.json`

## Version and impact

Version `0.1.0.dev54` -> `0.1.0.dev55`; catalog 158 -> 162 exact
documents. The other 158 documents change in the mechanical
`implementation_version` bump; `scirel.fusion.collisional-radiative-state-advance`
additionally carries the unit-label repair (document text only);
`src/scirel/fusion/__init__.py` adds five pure public exports plus one
constant. No other asset's contract changes.
