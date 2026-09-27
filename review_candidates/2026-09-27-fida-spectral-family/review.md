# Candidate: FIDASIM FIDA spectral-component family (two operators)

Status: development candidate prepared for expert review, frozen as the
pending_unapproved r80 successor of r79-v3. Nothing here is expert
approval, a trusted version, or a public release.

## Base and comparison scope

- SciRel base: r79-v3 (commit `f562536`, science HEAD `e509afb`, 166
  assets `0.1.0.dev56`, snapshot
  `build/verification/review-2026-09-27-r79-neutral-merge-family-v3`).
  r80 increments the catalog to 168 exact documents, version
  `0.1.0.dev56` -> `0.1.0.dev57`. The 166 pre-existing documents change
  only in the mechanical `implementation_version` bump; no frozen r79
  byte is otherwise altered.
- Unpublished candidate pool: re-checked by relation — none exists; the
  baseline has no Doppler/Stark/Zeeman component-wavelength relation and
  no FIDA wavelength-bin accumulation (`rg -i "stark|doppler|zeeman"` and
  `rg -il "bin_fida|谱线分箱|store_fw_photons"` over `src`, `tests` and
  `catalog` return nothing beyond unrelated `bin` substrings).
- Incoming source (read only): the saved FIDASIM bundle in the sibling
  main SciRel checkout
  (`build/verification/neutral-harness-baseline-v2/inputs/l1/FIDASIM`,
  read-only, zero writes). The qualified L1 delivery root
  (`D:/Users/26569/Desktop/归档_项目/codefusion/最小闭环压测环境`) was
  re-checked empty (0 items, including hidden entries) at batch start.

## Slice selection rationale

Of the items r79 deferred again (real-HDF5 table drivers, the NPA/FIDA
weight-production chain, MC marker production, the parallel (MPI-rank)
reservoir merge graphs, the neutral-bank lifecycle), this batch
integrates the smallest well-evidenced slice of the FIDA weight chain:
the two spectral leaves `多普勒StarkZeeman谱线波长` (N5
spectral_component_wavelength_producer) and `FIDA权重谱线分箱` (the
`store_fw_photons_at_chan` terminal binning). They are self-contained
closed-form relations, they compose directly into an N5 -> N6 witness,
and they need no six-level CX/atomic tables, colrad photon transport or
detector geometry — which is why the surrounding `fida_weights_los`
phase producer (`FIDA LOS相位权重生产`, the NPA stage-B weight producer
`NPA权重物理生产`, and the three MPI weight reductions) stays deferred.

## Proposed identity

- `scirel.fusion.doppler-stark-zeeman-wavelengths`
  (`doppler_stark_zeeman_wavelengths`, N5) — the saved
  多普勒StarkZeeman谱线波长: one sightline's Lyman-alpha (3) or
  Balmer-alpha (15) component wavelengths from the nonrelativistic
  Doppler shift plus the Stark-Zeeman level displacements at
  `E' = ||E + v x B||` (source anchors src/fidasim.f90:69-81,
  :11891-11963).
- `scirel.fusion.fida-wavelength-binning`
  (`bin_fida_los_components`, N6 boundary of the FIDA weight chain) —
  the saved FIDA权重谱线分箱: the `store_fw_photons_at_chan` floor
  binning with the `1/(4*pi*dlambda)` factor, the half-open window and
  the retained out-of-range raw indices (src/fidasim.f90:12297-12347).

## Public-asset decisions for the surrounding saved graphs

The saved bundle carries the two leaves inside `FIDA_LOS权重生产图`
(physical_state -> phase_weights over `FIDA视线物理状态聚合` and
`FIDA LOS相位权重生产`). That graph is not ported: its nodes bind the
heavy CX/colrad/phase producer that this batch deliberately does not
integrate, so there is no composition boundary to declare yet. The two
leaves enter as plain operators; a graph-level composition is deferred
until the phase producer (or a second consumer) exists.

## Relation to existing baseline (comparison result)

- No integrated SciRel asset computes Doppler/Stark/Zeeman component
  wavelengths or FIDA wavelength bins. The diagnostics domain's
  JH Balmer-alpha emission/inversion relations concern level
  populations and line emission coefficients, not spectral component
  positions; the colrad assets advance states and do not produce
  wavelengths. Both identities are recorded as `add`.
- The two leaves compose: the witness feeds
  `doppler_stark_zeeman_wavelengths` output into
  `bin_fida_los_components` (the 15-component Balmer-alpha case fully
  inside the window, and a 3-component Lyman-alpha case partially
  outside it). The saved `FIDA_LOS权重生产图` orders the same N5 -> N6
  hand-off inside the phase producer.
- The saved packaging declares the two leaves as separate operators
  with separate tests; SciRel retains both as separate identities
  (distinct domains: one spectral component table vs one wavelength
  axis), matching the saved packaging and the N1 leaf convention.

## Source quirks preserved verbatim (pinned by regressions, not repaired)

- The ion velocity is converted from cm/s to m/s exactly once; the
  sightline is normalized internally, so scaled sightline inputs give
  identical outputs.
- The moving electric field uses the source's
  `E' = ||E + v x B||` with the y-component sign convention of the
  saved arm; the Stark-Zeeman frequencies `q0`/`q1` combine the
  cyclotron and Stark terms in quadrature and the shifts are evaluated
  against `lambda0`, not `lambda_D`.
- With zero fields and zero velocity every component degenerates onto
  the single Doppler center (`q0 = q1 = 0`); the 15-component table
  only separates components when a field is present.
- The binning is floor-based over the half-open window
  `[lambdamin, lambdamax)`; a component at `lambdamax` maps to the
  discarded bin `nlambda` exactly like the source's `bin > nlambda`
  branch, and out-of-range components keep their raw computed index
  (negative below the window) in the audit output.

## Registered hardenings (each with a discriminating regression)

1. `doppler_stark_zeeman_wavelengths` checks every vector and scalar
   input finite (the saved arm propagated NaN/inf silently even though
   its own document promises `ValueError` for non-finite inputs).
2. The reference wavelength must be positive (the saved arm accepted
   zero and negative references).
3. Scalar magnitudes reject booleans (the saved arm numerified
   `magnetic_magnitude_t=True` to 1.0 T).
4. `component_count` must be a genuine integer accepting `np.integer`
   (the saved arm's `not in (3, 15)` accepted whole-number floats such
   as `3.0`); bools rejected.
5. `bin_fida_los_components` rejects boolean entries in the wavelength
   and intensity arrays — bool dtype and mixed object forms such as
   `np.asarray([True, 1.0], dtype=object)` alike (the saved arm's
   `np.asarray(..., dtype=float)` silently coerced `True` to 1.0; the
   same numerification gap closed for the r79 merge family) — and
   rejects boolean window bounds. The saved arm's own `nlambda`
   genuine-integer contract is kept and pinned.

## Verification

19 direct tests in `tests/operator_contracts/test_fida_spectral_family.py`
(saved probes for both assets, the source-quirk pins, all hardening
regressions, and the two N5 -> N6 combination witnesses); document
validation 168/168 source mode with executed examples; measured gates
and receipts recorded in `build/test-evidence-r80.md`.

## Boundary and open questions

- No qualified L1 consumption, external physical correctness, expert
  approval, trusted promotion, or public release are claimed.
- The saved FIDASIM bundle supports bounded historical development
  comparison only; there is no automated drift detection against it.
- Deferred again: the `fida_weights_los` phase producer (CX -> colrad
  -> Doppler/Stark/Zeeman -> bin), the NPA stage-B weight producer,
  the three MPI weight reductions (NPA five-array, active-FIDA
  dual-array, neutron three-array), real-HDF5 table drivers, MC marker
  production, the parallel reservoir merge graphs, and the neutral-bank
  lifecycle.
- Open expert questions: (1) the wavelength operator trusts the
  caller's reference wavelength and the source's nonrelativistic /
  quadrature approximations; no independent atomic-physics validation
  is claimed — whether that ceiling is acceptable for a future
  trusted version is an expert decision. (2) The saved arm's
  equation-oracle evidence class (no Fortran runtime parity for either
  leaf) is inherited unchanged. (3) License status remains
  `pending-human-decision` for the whole family.
