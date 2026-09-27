# Candidate: FIDASIM NBI source-geometry family (two operators + one task graph)

Status: development candidate prepared for expert review. The r75 science
bytes were frozen as pending_unapproved r75-v1 (snapshot
`build/verification/review-2026-09-27-r75-nbi-source-geometry-v1`, commit
`6f57c69`, freeze record `783e4ee`); this packet is the expert-review
three-piece entry point for that same frozen science content, bound by
SHA-256 in the candidate-review-materials index and snapshotted directly by
the r75-v2 evidence-only successor freeze. Nothing here is expert approval,
a trusted version, or a public release.

## Base and comparison scope

- SciRel base: `8c20a2b` (r74-v2 frozen, 148 assets `0.1.0.dev49`, snapshot
  `build/verification/review-2026-09-27-r74-firehose-tension-wording-v2`).
  r75 increments the catalog to 151 exact documents, version
  `0.1.0.dev49` -> `0.1.0.dev50`. The 148 pre-existing documents change only
  in the mechanical `implementation_version` bump.
- Unpublished candidate pool: re-checked by relation — none exists; the
  baseline has no source-plane ray relation, no finite-grid ray
  intersection, and no NBI trajectory-initialization composition. The r70-r72
  FIDASIM leaves cover different relations (cell-directed ray, energy
  scaling, normalization, birth position/direction leaves).
- Incoming source (read only): the saved FIDASIM bundle in the sibling main
  SciRel checkout (read-only, zero writes). Saved implementations support
  bounded historical development comparison only; the qualified L1 delivery
  root was re-checked empty (0 items) before and after the freeze.

## Proposed identity

- `scirel.fusion.nbi-source-plane-ray`
  (`construct_nbi_source_ray`, N2) — mc_nbi source-plane branch:
  rectangle/ellipse source mapping, focusing and divergence ray terms,
  beam-basis transform, per-aperture acceptance.
- `scirel.fusion.beam-grid-ray-intersection`
  (`intersect_ray_with_rectilinear_grid`, N2/N3 handoff) — grid_intersect
  finite rectilinear branch: source-order six-face enumeration, first-valid/
  first-distinct pairing, dot-product entry/exit ordering.
- `scirel.fusion.nbi-trajectory-initialization`
  (`initialize_nbi_trajectory`, kind task_graph, N2) — the saved
  NBI轨迹初始化图 caller-random paths composing five integrated leaves
  (normalization, the two new operators, energy-component velocity scaling,
  cell-directed ray); ordered branching DAG, no nested graphs, no feedback.

## Closes and defers (from the r72 deferred list)

Closes: outer NBI source geometry (operator 1) and the outer framework
TaskGraph (the graph). Deferred, with reasons in the r75 dossier: the
NPA/FIDA weight-production chain (closure needs MPI gate packages and
LOS/Doppler geometry not yet extracted) and the DCX spectrum state (needs
the six-level colrad core not yet integrated).

## Deduplication judgment

- Versus `nbi-cell-directed-ray`: that leaf is the mc_nbi_cell cell branch;
  the source-plane ray is the other, mutually exclusive mc_nbi path —
  different inputs and geometry direction, no consolidation.
- Versus `beam-grid-cell-sampling`: that leaf samples cell birth positions
  from draws; this batch's intersection relation maps a ray to finite-grid
  entry/exit — different relation.
- The graph introduces no new scientific rule: every numeric edge binds an
  already-integrated asset, and its exact document declares the composition.

## Material scientific differences and declared divergences

1. **Declared non-ported runtime boundary**: the saved graph's serial
   `utilities.f90` two-word RNG modes (seed, captured per-event state,
   1000-rejection beam-axis fallback) are controlled glue, not a scientific
   relation; this port rejects their state keys, and the caller owns variate
   resampling/retry. The saved bundle's 16-marker captured-thread-state
   replay evidence is not inherited.
2. **Candidate-ray parity pinned**: the source_ray branch computes the
   velocity scaling and optional grid handoff regardless of the aperture
   flag (saved caller-random parity); the graph document directs downstream
   consumers to gate on `accepted`, and a distinguishing regression pins the
   rejected-ray candidate outputs against direct leaf calls.
3. **Saved infinite-line pair semantics pinned, not hardened**: the grid
   intersection performs no origin-side check — a pair can lie entirely
   behind the origin, and an origin inside the grid legitimately reports its
   entry behind the origin. Arithmetic is verbatim; the document bounds the
   claim (no forward-only guarantee) and a regression pins both cases.
4. **Registered hardenings** with discriminating witnesses: finite
   focus/divergence/half-widths (NaN passes the saved arm's checks),
   Python- and NumPy-bool source-shape rejection, finite-and-nonzero ray
   norm (an overflowing squared norm collapses `beam_ray/Inf` to a zero
   "unit" ray — found by pre-freeze review), finite outputs, finite grid
   lengths (saved arm's positivity test lets NaN lengths through).
5. **Saved quirks preserved verbatim**: the Float32 energy-component
   divisor, theta_z-uses-focy (r72-pinned), the six-face enumeration order,
   the 0.001 cm pairing threshold, and the origin-backfilled zero-length
   no-intersection result.

## Evidence

- 24 direct tests: 15 operator tests (saved probes, closed-form mappings,
  aperture bounds, hardenings, pinned semantics) and 9 graph-contract tests
  (composition order, branch exclusivity, optional handoff vs direct leaf
  calls, same-variate bit-identical replay, RNG-boundary rejection,
  rejected-candidate parity). Full-tree delta reconciles exactly
  (1550 -> 1574 source with replay; 1398/195 -> 1573/44 installed; see the
  r75 corrections addendum for the installed-delta arithmetic).
- No separate replay file: the FIDASIM saved packages ship package-level
  oracles; the saved implementations' content digests are recorded per asset
  in the exact documents and `build/test-evidence-r75.md`.
- Pre-freeze review: four independent findings (norm overflow, NumPy bool,
  pair semantics wording, candidate-ray wording) resolved regression-first;
  recorded in `build/test-evidence-r75.md` and
  `build/test-evidence-r75-corrections-addendum.md`.

## Files

- `proposal/nbi_source_plane_ray.py`, `proposal/beam_grid_ray_intersection.py`,
  `proposal/nbi_trajectory_initialization.py`
- `proposal/test_nbi_source_geometry.py`,
  `proposal/test_graph_nbi_trajectory_initialization.py`
- `proposal/scirel.fusion.nbi-source-plane-ray.json`,
  `proposal/scirel.fusion.beam-grid-ray-intersection.json`,
  `proposal/scirel.fusion.nbi-trajectory-initialization.json`

## Version and impact

Version `0.1.0.dev49` -> `0.1.0.dev50`; catalog 148 -> 151 exact documents.
The other 148 documents change only in the mechanical
`implementation_version` bump; `src/scirel/fusion/__init__.py` adds three
pure public exports. No other asset's contract changes.
