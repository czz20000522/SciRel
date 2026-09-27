# Candidate: FIDASIM DCX/HALO iteration-feedback family (one operator + one bounded sequence graph)

Status: development candidate prepared for expert review, frozen as the
pending_unapproved r76 successor of r75-v2. Nothing here is expert
approval, a trusted version, or a public release.

## Base and comparison scope

- SciRel base: r75-v2 (commit `2b922fb`, 151 assets `0.1.0.dev50`, snapshot
  `build/verification/review-2026-09-27-r75-nbi-source-geometry-v2`; r75-v1
  preserved). r76 increments the catalog to 153 exact documents, version
  `0.1.0.dev50` -> `0.1.0.dev51`. The 151 pre-existing documents change
  only in the mechanical `implementation_version` bump.
- Unpublished candidate pool: re-checked by relation — none exists; the
  baseline has no HALO population-iteration feedback or population-merge
  recurrence. The KN1DPy generation/outer-convergence assets are different
  relations (neutral transport generations and solver-seed convergence,
  not the source's halo density-feedback/marker-budget recurrence).
- Incoming source (read only): the saved FIDASIM bundle in the sibling main
  SciRel checkout (read-only, zero writes). The qualified L1 delivery root
  was re-checked empty (0 items) at batch start.

## Proposed identity

- `scirel.fusion.halo-iteration-feedback`
  (`advance_halo_iteration_feedback`, N3) — one halo population-iteration
  feedback round: density growth guard, merge_neutral_populations density
  update, seed_dcx fraction, next n_halo marker count with Fortran
  truncation (src/fidasim.f90:13293-13420, merge order 10484-10500).
- `scirel.fusion.halo-iteration-feedback-sequence`
  (`advance_halo_iteration_feedback_sequence`, kind task_graph, N3) — the
  saved DCXHalo迭代反馈序列图: a bounded explicit feedback recurrence over
  a caller-provided current-density sequence with the marker-budget
  recurrence enforced and the sequence required to end exactly at a source
  stop branch.

## Scope within the deferred DCX/HALO item

This family advances the r75-deferred "DCX spectrum state" item by
integrating its population-iteration feedback core, which is complete and
deterministic in the saved bundle. Still deferred: the DCX/CX initial
state and photon fast-ion correction (needs the six-level colrad
propagation core), the NPA/FIDA weight-production chain (MPI gate packages
and LOS/Doppler geometry), and the multi-cell population merge (this
family covers the scalar single-point recurrence).

## Declared divergences and pinned semantics

1. **Explicit bounded feedback**: state (previous/merged pair), order
   (source-ordered rounds), stop branches (density_growth_exceeded,
   seed_below_threshold with 0.01 equality continuing) and the iteration
   bound (the provided sequence length) are declared per the graph
   contract; ending without a stop branch or continuing after a stop
   fails closed. No hidden reservoir, RNG or MPI state.
2. **Registered hardenings** with discriminating witnesses: real-scalar
   type check (the saved arm converts strings via float()), finite
   ratio/seed/merged outputs, and a finite, representable double-precision
   marker product budget*seed (the saved arm returns Inf silently or
   crashes with a bare OverflowError inside int(Inf)).
3. **Exact-integer budget preservation**: integer budget entries keep full
   precision at any magnitude (2**53+1 reproduces without drift); float
   entries are accepted only when finite and exactly integral — a 2**53+1
   integer given as a float cannot match its exact base and drifts
   fail-closed. Bools are rejected elementwise (the saved arm converts
   them through float64). Documented numerical bound: the marker product
   is computed in double precision, matching the source's counting
   arithmetic.
4. **Saved single-step graph folded**: the saved DCXHalo迭代反馈图 is a
   pure delegation layer whose ports equal the operator's contract
   one-to-one; it is not ported as a separate asset, and the decision is
   recorded in the sequence graph's exact document (with its digest).
5. **Saved quirks preserved verbatim**: ratio > 1 exit ordering (before
   previous/merge/seed update, previous state kept), null projections on
   the growth branch (not filled zeros), the 0.01 seed-equality boundary,
   merge addition order, and Fortran truncation of the nonnegative marker
   product.

## Evidence

- 13 direct tests: saved probes (0.559 seed case with marker count 22,
  ratio=1 continuation, 0.01 boundary, growth exit with null projections,
  five-round sequence with branch counts 4 continue / 1 seed stop),
  closed-form recurrence recomputation round by round, budget-recurrence
  drift, post-stop continuation, unterminated sequence, big-integer
  preservation, bool rejection, and the registered overflow gates.
- No separate replay file: the FIDASIM saved packages ship package-level
  oracles; the saved implementations' content digests are recorded per
  asset in the exact documents and `build/test-evidence-r76.md`.
- Pre-freeze review: three contract cases (budget*seed OverflowError,
  bool budget acceptance, >2^53 spurious drift) resolved regression-first
  at commit `60804c4`; recorded in `build/test-evidence-r76.md`.

## Files

- `proposal/halo_iteration_feedback.py`,
  `proposal/halo_iteration_feedback_sequence.py`
- `proposal/test_halo_iteration_feedback.py`
- `proposal/scirel.fusion.halo-iteration-feedback.json`,
  `proposal/scirel.fusion.halo-iteration-feedback-sequence.json`

## Version and impact

Version `0.1.0.dev50` -> `0.1.0.dev51`; catalog 151 -> 153 exact
documents. The other 151 documents change only in the mechanical
`implementation_version` bump; `src/scirel/fusion/__init__.py` adds two
pure public exports. No other asset's contract changes.
