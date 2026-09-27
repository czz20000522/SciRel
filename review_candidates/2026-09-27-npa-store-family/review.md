# Candidate: FIDASIM NPA store_npa energy-bin leaf (one operator)

Status: development candidate prepared for expert review, frozen as the
pending_unapproved r81 successor of r80-v3. Nothing here is expert
approval, a trusted version, or a public release.

## Base and comparison scope

- SciRel base: r80-v3 (record commit `2999ac5`, repair/tree commit
  `935c17f`, 168 assets `0.1.0.dev57`, snapshot
  `build/verification/review-2026-09-27-r80-fida-spectral-family-v3`).
  r81 increments the catalog to 169 exact documents, version
  `0.1.0.dev57` -> `0.1.0.dev58`. The 168 pre-existing documents change
  only in the mechanical `implementation_version` bump; no frozen r80
  byte is otherwise altered.
- Scope disclosure (r81 pre-freeze review correction): this batch also
  carries the r80-v3 review finding for
  `scirel.fusion.doppler-stark-zeeman-wavelengths` — a nonpositive
  component wavelength now fails closed (source module, tests and exact
  document updated; `test_nonpositive_component_wavelengths_fail_closed`)
  — because the finding arrived after the r80-v3 freeze and the brief
  routes it to the next development version. It is part of r81's
  substantive science delta and review scope, not hidden in the
  mechanical version bump. The multi-coil exact-document clarification
  below is the other non-mechanical document change.
- Unpublished candidate pool: re-checked by relation — none exists; the
  baseline has no NPA energy-bin/flux-increment relation
  (`rg -i "energy_bin|store_npa|earliest"` over `src`, `tests` and
  `catalog` returns only unrelated `earliest-crossing` and JH-inversion
  substrings).
- Incoming source (read only): the saved FIDASIM bundle in the sibling
  main SciRel checkout
  (`build/verification/neutral-harness-baseline-v2/inputs/l1/FIDASIM`,
  read-only, zero writes). The qualified L1 delivery root
  (`D:/Users/26569/Desktop/归档_项目/codefusion/最小闭环压测环境`) was
  re-checked empty (0 items, including hidden entries) at batch start.
  This batch also re-verified the bundle's live bytes against the
  input-manifest `l1/FIDASIM` scope (1253 files, per-file SHA-256 and
  sizes, ordinal recipe digest `sha256:cd0010b8...` reproduced;
  `source_byte_verified: true` is a property of that snapshot, not a
  qualified-L1 claim).

## Slice selection rationale

Of the items r80 deferred again (the `fida_weights_los` phase producer,
the NPA stage-B weight producer, the MPI weight reductions, real-HDF5
table drivers, MC marker production, the parallel reservoir merge
graphs, the neutral-bank lifecycle), this batch integrates the NPA
detection chain's smallest leaf: the stateless `store_npa` scalar slice
(`NPA能量通道通量增量`, src/fidasim.f90:10600-10724). It is self-contained
(caller-owned grid/indices/flux), composes directly as the record
producer for a caller-owned `(energy, detector, class)` accumulator,
and its saved package carries the bundle's strongest historical
evidence class — while the surrounding NPA producers (hit production,
attenuation, the stage-B weight chain, MPI five-array reduction) stay
deferred because their dependency closure is far larger.

## Proposed identity

- `scirel.fusion.npa-energy-bin-increment`
  (`select_npa_energy_bin_increment`, N8) — the saved NPA能量通道通量增量:
  `energy = beam_mass * v2_to_E_per_amu * dot(v, v)`, the Fortran
  `minloc(abs(energy_grid - energy))` nearest-bin selection with the
  first channel winning ties, the class cap `min(orbit_class, nclass)`,
  and the non-accumulated `flux/dE` record with the source's
  first-adjacent-center `dE` convention (src/fidasim.f90:10600-10724).

## Public-asset decision for the surrounding saved graphs

The saved bundle composes this leaf inside `NPA轨迹探测器响应图` /
`NPA命中到探测器响应图` (hit trajectory -> typed store_npa record ->
non-accumulated increment). Those graphs are not ported: their nodes
bind the N3/N8 hit and attenuation producers that this batch does not
integrate. The leaf enters as a plain operator; a graph-level
composition is deferred until a second consumer exists.

## Evidence ceiling: ledger claim versus re-verifiable evidence

The saved bundle's `extraction_ledger.md` (2026-08-16 entry) upgrades
this relation to `source_behavior_verified` via an external native
source microprobe (`../FIDASIM_evidence/source_probe/npa_store_flux_audit/`,
three real `store_npa` replays at frozen source `9019e945...`,
`max_abs = 0`). That directory does not exist next to the frozen saved
input (`inputs/l1/FIDASIM`), whose live bytes this batch re-verified
against the input-manifest scope digest, and the package's own test
header marks itself `source_unavailable: source-free equation and
boundary oracle`. The historical microprobe may well have run, but this
frozen input cannot re-verify its receipt. r81 therefore records the
ledger claim as provenance while keeping the review ceiling at the
package-level equation/boundary oracle; if the external receipt is
later located and digest-bound, a successor may raise the evidence
level. No Fortran runtime parity is claimed.

## Relation to existing baseline (comparison result)

- No integrated SciRel asset selects an NPA energy bin or returns a
  flux/dE increment; the nearest FIDA-spectral neighbours (r80's
  wavelength binning) bin photons by wavelength, not particles by
  energy, and share no code path. Recorded as `add`.
- Composition witness: the caller accumulates three returned records
  into its own `(energy, detector, class)` storage and reproduces the
  per-(bin, class) partial sums including the class cap — the N8
  `store_npa` usage the saved graphs declare, without this leaf
  touching storage.

## Source quirks preserved verbatim (pinned by regressions, not repaired)

- `dE = grid(2) - grid(1)` from the first adjacent center pair, even on
  non-uniform grids and for hits binned far from the first two centers.
- Exact ties select the first channel (Fortran `minloc` semantics).
- The detector index is passed through verbatim; the class is capped by
  `min(orbit_class, nclass)`.

## Registered hardenings (each with a discriminating regression)

1. Index contracts (`detector_index_one_based`, `orbit_class_one_based`,
   `class_count`) must be genuine integers accepting `np.integer` — the
   saved arm's bare `isinstance(value, int)` accepted `True` while
   rejecting `np.int64` and whole-number floats; the float rejection
   is continuity from the saved arm, the `np.integer` acceptance and
   the bool rejection are the hardening.
2. Boolean entries in the velocity vector and the energy centers are
   rejected (container, bool dtype and object forms), and the three
   scalars reject booleans/non-finite values.
3. The computed energy must be finite (an overflowing velocity/mass
   product fails closed instead of being binned through `inf`).
4. r81 pre-freeze review findings: the first adjacent spacing `dE` must
   be a positive finite float and the returned `flux/dE` increment
   finite — the saved arm returned `inf` for `dE = 5e-324` and a silent
   `0.0` when `dE` overflowed (`(-1e308, 1e308)`), both violating the
   package document's "finite nonnegative" increment promise.

## Verification

14 direct tests in `tests/operator_contracts/test_npa_store_family.py`
(saved probes, quirk pins, hardening regressions, and the N8 caller
accumulation witness); document validation 169/169 source mode with
executed examples; measured gates and receipts recorded in
`build/test-evidence-r81.md`.

## Same-batch multi-coil clarification (no default change)

Independent field-margin-compose use of
`scirel.field.multi-coil-vacuum-field` surfaced a misreading risk: the
exact document called `current_a` a "source-set drive current" and the
2x2 example omitted `weights`, while the implementation (and the old
tests) default every filament to weight 1, so the response is the
superposition of per-filament drives `current_a * weights[i]`. If a
caller's `current_a` is one section total, the caller must distribute
weights summing to 1 (1/(nr*nz) only for even splits); if each filament
is an independent turn, the default is correct. r81 clarifies the exact
document with both conditional readings and adds one discriminating
numeric test (`weights = [0.5]*4` reproduces exactly half the
default-weights field; `[0.25]*4` reproduces the 250 A all-turns run);
the default weights of 1, the algorithm, and the frozen r80 summary
bytes are unchanged, and no `sum(weights) = 1` gate is imposed (reading
(a) legitimately uses weight 1 on every filament).

## Boundary and open questions

- No qualified L1 consumption, external physical correctness, expert
  approval, trusted promotion, or public release are claimed.
- The saved FIDASIM bundle supports bounded historical development
  comparison only; there is no automated drift detection against it.
- Deferred again: the `fida_weights_los` phase producer, the NPA
  stage-B weight producer, the three MPI weight reductions, real-HDF5
  table drivers, MC marker production, the parallel reservoir merge
  graphs, and the neutral-bank lifecycle.
- Open expert questions: (1) whether the ledger's historical
  microprobe claim may raise this leaf's evidence level in a successor
  once the external receipt is located and digest-bound; (2) whether
  the multi-coil `current_a` semantics should eventually get an
  explicit caller-declared interpretation flag instead of the
  documented convention; (3) license status remains
  `pending-human-decision`.
