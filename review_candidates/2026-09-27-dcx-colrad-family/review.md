# Candidate: FIDASIM DCX/HALO colrad family (four operators + one composition graph)

Status: development candidate prepared for expert review, frozen as the
pending_unapproved r77 successor of r76-v1. Nothing here is expert
approval, a trusted version, or a public release.

## Base and comparison scope

- SciRel base: r76-v1 (commit `0cca44c`, 153 assets `0.1.0.dev51`, snapshot
  `build/verification/review-2026-09-27-r76-halo-iteration-feedback-v1`).
  r77 increments the catalog to 158 exact documents, version
  `0.1.0.dev51` -> `0.1.0.dev52`. The 153 pre-existing documents change
  only in the mechanical `implementation_version` bump.
- Unpublished candidate pool: re-checked by relation — none exists; the
  baseline has no colrad rate-matrix assembly, no eigenstate advance, no
  DCX/halo initial-state weighting and no marker-initialization
  composition.
- Incoming source (read only): the saved FIDASIM bundle in the sibling main
  SciRel checkout (read-only, zero writes). The qualified L1 delivery root
  was re-checked empty (0 items) at batch start.

## Proposed identity

- `scirel.fusion.dcx-thermal-species-selection`
  (`select_dcx_thermal_species_mass`, N3) — thermal-species mass selection
  for the source species loop.
- `scirel.fusion.dcx-halo-colrad-initial-state`
  (`prepare_dcx_colrad_initial_state`, N3) — per-marker initial-state
  weighting with the exact-isotope fast-ion branch and photon correction.
- `scirel.fusion.collisional-radiative-rate-matrix`
  (`assemble_collisional_radiative_rate_matrix`, N3) — real rate matrix
  from caller-owned transition tables and the local plasma state.
- `scirel.fusion.collisional-radiative-state-advance`
  (`advance_collisional_radiative_states`, N3/N4 seam) — one colrad time
  step via real eigen-decomposition with photon projection and the
  outside-plasma ballistic rule.
- `scirel.fusion.dcx-halo-marker-initialization`
  (`initialize_dcx_halo_marker`, kind task_graph, N3) — the saved
  DCXHalo标记初态图: source-ordered composition of beam-grid cell
  sampling, the two caller provider capabilities (plasma snapshot, CX
  rates), species selection, halo velocity sampling and initial-state
  weighting.

## Scope within the deferred DCX item

This family integrates the colrad core that r75/r76 declared as the
blocker of the DCX spectrum-state item, using caller-owned transition
tables — no atomic-data facts are invented. Still deferred: real-HDF5
table drivers and the multi-segment deposition loop (束中性逐段碰撞辐射沉积图),
the NPA/FIDA weight-production chain, the multi-cell population merge and
MC marker production.

## Declared divergences and pinned semantics

1. **Zero-eigenvalue boundary pinned, not repaired**: the saved arm's
   `(exp(0)-1)/1` rule zeroes a zero mode's integrated density, while the
   Fortran source adds +1 before the exponential (a different value). The
   saved bundle's own ledger registers the divergence and shows it
   untriggered in 823 bounded replay events (240 synthetic R-N48 + 583
   real-HDF5-table R-N49, all non-zero eigenvalues). This port reproduces
   the saved arm and pins the branch with a discriminating regression;
   expert adjudication is requested.
2. **Eigensolver conditioning ceiling**: this port uses numpy/LAPACK
   eigensolvers, not the source's balance+QR eigensystem; the saved
   ledger records a ~5e-6 conditioning floor versus captured flux on
   stiff matrices (583 real-table events) with ~1e-13 agreement between
   independent references. Documented as an evidence ceiling, not bit
   parity.
3. **Registered hardenings**: finite/type gates on states, dt, matrices,
   table mappings, Einstein rates and initial-state products (the saved
   arm propagates NaN/Inf silently); strict integer emitting and species
   indices (bools rejected); provider contract violations raise ValueError
   with declared missing fields instead of the saved arm's raw
   TypeError/KeyError; table spacings must be positive.
4. **Saved quirks preserved verbatim**: the upper-table-edge zero-rate
   policy, the minlog threshold zeroing, the strict-equality isotope
   branch, the Einstein column-sum diagonal rewrite, the real-eigenstate
   1e-12 contract, and the source node order of the marker slice
   (non-interchangeable).

## Evidence

- 17 direct tests: saved probes (isotope shares, constant-table matrix
  oracle, upper-edge policy, diagonal eigen-advance with photon
  projection, ballistic rule, marker flow with graph-order diagnostics),
  round-by-round leaf equivalence, provider call-order enforcement,
  provider contract rejections, and the registered hardenings including
  the exponential-overflow and zero-eigen pins.
- No separate replay file: the FIDASIM saved packages ship package-level
  oracles; the saved implementations' content digests are recorded per
  asset in the exact documents and `build/test-evidence-r77.md`.
- Pre-freeze review: the zero-eigen boundary question resolved by pinning
  plus an explicit evidence boundary (see above) rather than a silent
  repair of source arithmetic.

## Files

- `proposal/dcx_thermal_species_selection.py`,
  `proposal/dcx_halo_colrad_initial_state.py`,
  `proposal/collisional_radiative_rate_matrix.py`,
  `proposal/collisional_radiative_state_advance.py`,
  `proposal/dcx_halo_marker_initialization.py`
- `proposal/test_dcx_colrad_family.py`
- `proposal/scirel.fusion.dcx-thermal-species-selection.json`,
  `proposal/scirel.fusion.dcx-halo-colrad-initial-state.json`,
  `proposal/scirel.fusion.collisional-radiative-rate-matrix.json`,
  `proposal/scirel.fusion.collisional-radiative-state-advance.json`,
  `proposal/scirel.fusion.dcx-halo-marker-initialization.json`

## Version and impact

Version `0.1.0.dev51` -> `0.1.0.dev52`; catalog 153 -> 158 exact
documents. The other 153 documents change only in the mechanical
`implementation_version` bump; `src/scirel/fusion/__init__.py` adds five
pure public exports. No other asset's contract changes.
