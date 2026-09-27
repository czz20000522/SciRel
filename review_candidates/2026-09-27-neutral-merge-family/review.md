# Candidate: FIDASIM neutral-reservoir/population merge family (three operators + one composition graph)

Status: development candidate prepared for expert review, frozen as the
pending_unapproved r79 successor of r78-v2. Nothing here is expert
approval, a trusted version, or a public release.

## Base and comparison scope

- SciRel base: r78-v2 (commit `01f3988`, science HEAD `a8ca079`, 162
  assets `0.1.0.dev55`, snapshot
  `build/verification/review-2026-09-27-r78-beam-deposition-family-v2`).
  r79 increments the catalog to 166 exact documents, version
  `0.1.0.dev55` -> `0.1.0.dev56`. The 162 pre-existing documents change
  only in the mechanical `implementation_version` bump; no frozen r78
  byte is otherwise altered.
- Unpublished candidate pool: re-checked by relation — none exists; the
  baseline has no population-density merge, no reservoir-sampling merge
  and no composition of the two.
- Incoming source (read only): the saved FIDASIM bundle in the sibling
  main SciRel checkout
  (`build/verification/neutral-harness-baseline-v2/inputs/l1/FIDASIM`,
  read-only, zero writes). The qualified L1 delivery root
  (`D:/Users/26569/Desktop/归档_项目/codefusion/最小闭环压测环境`) was
  re-checked empty (0 items, including hidden entries) at batch start.

## Slice selection rationale

Of the items r78 deferred (real-HDF5 table drivers, the NPA/FIDA
weight-production chain, the multi-cell population merge, MC marker
production), this batch integrates the multi-cell population merge
(the 中性库合并家族) because it has the smallest useful dependency
closure — the three operators and one graph are self-contained and
compose directly with the already-integrated NDMC producer's
population outputs — while the NPA/FIDA chain requires six-level CX and
atomic tables, the Doppler-Stark-Zeeman spectral model and detector
geometry, and is deferred again.

## Proposed identity

- `scirel.fusion.neutral-population-density-merge`
  (`merge_neutral_population_density`, N3) — the saved 中性库种群合并:
  single-cell six-level density addition with explicit write/read
  ownership and before/after/contribution bookkeeping (source anchor
  src/fidasim.f90:10484-10498, addition at :10493).
- `scirel.fusion.neutral-population-grid-merge`
  (`merge_neutral_population_cells`, N3) — the saved 中性库种群网格合并:
  the same relation over an explicit `(6,nx,ny,nz)` beam-grid state
  with cell shape/count reporting and no cross-cell mixing.
- `scirel.fusion.neutral-reservoir-merge`
  (`merge_neutral_reservoirs`, N3) — the saved 中性库合并: one source
  `merge_reservoirs(res1,res2)` call with fully explicit state and RNG
  records (src/fidasim.f90:10343-10392 and the inline update_reservoir
  walk): lazy initialization, ordered nonfull appends, the
  full/nonfull orientation swap, and the both-full per-slot selection
  at the float32 seen-record probability.
- `scirel.fusion.neutral-population-state-merge`
  (`merge_neutral_population_state`, kind task_graph, N3) — the saved
  中性库种群合并图: source-ordered composition of the density half and
  the reservoir half over fully caller-owned state, with the res2=res1
  local feedback declared in the diagnostics.

## Public-asset decision for the saved single-node delegation graph

The saved bundle declares 中性库合并图 as a separate TaskGraph whose
single node calls `merge_neutral_reservoirs` and attaches diagnostics.
Registered deviation from the saved packaging: it is not ported as a
separate SciRel asset — its ports equal the operator's contract
one-to-one, following the established DCXHalo迭代反馈图 precedent
(r75 halo-iteration-feedback-sequence lineage) — so the composition
graph's reservoir node binds directly to the integrated
`scirel.fusion.neutral-reservoir-merge` operator. Promotion of a
standalone delegation graph is deferred until a second consumer exists.

## Relation to existing baseline (comparison result)

- No integrated SciRel asset merges neutral populations or reservoirs.
  The closest neighbour, `scirel.fusion.halo-iteration-feedback`,
  consumes the same source relation's *density update only*, as one
  scalar addition inside a feedback guard, and its document explicitly
  excludes reservoir sampling ("Full Monte Carlo, reservoir sampling,
  MPI/OpenMP ownership and HDF5 writers remain outside this
  relation"). The new family is the missing merge relation itself,
  with the reservoir half and the ownership bookkeeping new — recorded
  as `add`, not as variant or composition of an existing identity.
- Downstream compatibility: the NDMC producer accumulates
  `nlevels`-general population grids; the grid merge is the saved
  family's fixed six-level form. The end-to-end witness composes them
  at `nlevels=6` (two NDMC marker batches merged cell-wise). No
  direct composition is claimed beyond that witness; a general-level
  merge is not asserted.
- The saved bundle declares the single-cell and grid density merges as
  separate operators with separate tests; SciRel retains both as
  separate identities (distinct domains: one cell vs the whole grid),
  matching the saved packaging and the N1 leaf convention.

## Source quirks preserved verbatim (pinned by regressions, not repaired)

- Lazy target initialization: `W = exp(log(u0)/k)`,
  `i = k + floor(log(u1)/log(1-W)) + 1`, `n = 1`, only when
  `target_n <= 0`; the uniform pair is consumed even when the merge is
  source-empty.
- Replacement updates multiply `W` first and draw the next replacement
  horizon from the *updated* `W`.
- The both-full probability is computed in float32,
  `p = float32(n1)/float32(n1+n2)`, and a source slot is selected only
  when `uniform > p` (strict comparison).
- After any nonempty merge the source state output is the merged
  target state broadcast back (res2 = res1), not the pre-merge source;
  the source-empty branch returns the target untouched.
- The append walk fills slot `n-1` while `n <= k`, consults the
  replacement horizon at `n == i`, and skips otherwise; the first
  append into a full-prefix target overwrites the old record at slot
  `n-1` before later records occupy the following slots.

## Registered hardenings (each with a discriminating regression)

1. Reservoir metadata and capacity accept genuine integers including
   `np.integer` (the saved arm's `type(...) is int` rejected
   `np.int64`) but reject bools, `np.bool_` and whole-number floats.
2. `W` rejects booleans (the saved arm's `isinstance` accepted
   `W=True`).
3. Replacement slot indices must be genuine integers (the saved arm's
   integral-float acceptance truncated `7.0` and coerced bools).
4. Density and slot/uniform arrays reject boolean entries — both bool
   dtype arrays and mixed object arrays such as `[True, 1.0]` (the
   saved arm's `np.asarray(..., dtype=float)` silently numerified
   `True` to 1.0; the mixed-object gap was found by pre-freeze review
   in the r79 working tree and closed before the freeze, with
   regressions covering weights, velocities, initialization uniforms,
   replacement uniforms and both-full uniforms).

## Verification

23 direct tests in `tests/operator_contracts/test_neutral_merge_family.py`
(saved probes for all four assets, the source-quirk pins, the
hardening regressions, and the NDMC composition witness); document
validation 166/166 source mode with executed examples; measured gates
and receipts recorded in `build/test-evidence-r79.md`.

## Boundary and open questions

- No qualified L1 consumption, external physical correctness, expert
  approval, trusted promotion, or public release are claimed.
- The saved FIDASIM bundle supports bounded historical development
  comparison only; there is no automated drift detection against it.
- Deferred again: real-HDF5 table drivers, the NPA/FIDA
  weight-production chain, MC marker production, the parallel
  (MPI-rank) reservoir merge graphs, and the neutral-bank lifecycle.
- Open expert questions: (1) the merge family's densities carry the
  caller's unit interpretation ("source population density"); if the
  expert adjudicates the N3 rate-density reconciliation (r78 open
  question), the merge documents should inherit that ruling. (2) The
  six-level fixed shape of the grid merge versus the NDMC producer's
  `nlevels`-general grids: whether a level-general merge should exist
  is a new-capability decision. (3) License status remains
  `pending-human-decision` for the whole family.
