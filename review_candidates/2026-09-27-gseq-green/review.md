# Candidate: GSEQ filament-coil Green family (three operators)

Status: development candidate prepared for expert review, to be frozen as the
pending_unapproved r69 successor of r68. Nothing here is expert approval, a
trusted version, or a public release.

## Base and comparison scope

- SciRel base: `ad0331e` (r68-v1 frozen, 132 assets dev42, snapshot
  `build/verification/review-2026-09-27-r68-omega-aggregation-v1`). r69
  increments the catalog to 135 exact documents, version
  `0.1.0.dev42` -> `0.1.0.dev43`.
- Unpublished candidate pool: re-checked by relation for the filament-coil
  Green chain — none exists. The baseline `scirel.field` domain has the
  scipy-elliptic `circular-filament-green` relation but no geometry/modulus
  generator, no public K/E evaluation, and no caller-supplied-elliptic
  response variant.
- Incoming source (read only): the saved **GSEQ** bundle
  (`build/verification/neutral-harness-baseline-v3/inputs/l1/gseq`) — the
  first non-KN1DPy source integrated in this chain. The saved GSEQ bundle
  supports bounded historical development comparison only; the qualified L1
  delivery root was re-checked empty (0 items) at batch start.
- Provenance ceiling: provisional bounded historical development comparison;
  not qualified-L1 provenance, not expert approval.

## Proposed identity

- `scirel.field.coil-green-geometry`
  (`compute_axisymmetric_coil_modulus`) — source-regularized observation
  radius, per-coil squared moduli, distance denominators.
- `scirel.field.complete-elliptic-integrals-approx`
  (`evaluate_complete_elliptic_integrals`) — the source's apx==1
  polynomial-log K(m), E(m) approximation with its whole-array sentinel
  guard preserved verbatim.
- `scirel.field.filament-coil-green-field`
  (`evaluate_filament_coil_green_field`) — the GSEQ imethod==1 closed-form
  coil response sum.

## Deduplication judgment (relation variant, not a new capability)

The response operator's relation is the SAME circular-filament Green physics
as the baseline `scirel.field.circular-filament-green`. It is recorded as a
**declared relation variant**, not a new scientific capability. The variant
boundary, and why the public identities stay separate:

1. **Elliptic values are caller-supplied per coil** (typically the GSEQ
   approximation for provenance parity) instead of internally evaluated
   scipy special functions; this decoupling is the operator's contract, not
   an implementation detail.
2. **One scalar observation target** with the source's `r0 + 1e-8` axis
   regularization applied exactly once upstream (the geometry operator's
   output is the response operator's required input), versus arbitrary point
   arrays evaluated per point.
3. **Combined `2e-7*N*I` current factor** and the source's exact formula
   arrangement (algebraically equal to the baseline form; verified to rtol
   1e-12 at equal K/E).
4. **Singular handling**: fail-closed rejection versus the baseline's
   zeroing of non-finite terms.
5. The K/E approximation operator is a separate numerical relation (an
   approximation with a declared sampled error against scipy: ≤1e-8 (K) /
   ≤2e-8 (E) relative on a 200,001-point sweep of [1e-6, 0.999999] — sampled
   evidence, not a continuous bound), not a redundant copy of any baseline
   capability; nothing in the baseline exposes K/E publicly.

Consolidation into the baseline asset was considered and rejected: it would
destroy the GSEQ provenance-parity chain (the saved formulas pair with the
source's own K/E) and mix two singular-handling contracts in one callable.
The variant boundary is recorded in the exact document
(`identity.relation` names the variant-of relationship) and left to experts
for any future unification.

## Material scientific differences and declared divergences

1. **Singular-geometry rejection (registered hardening).** Recorded
   pre-review failure chain, now a combination regression: a regularized
   radius that lands exactly on the filament ring drives the geometry
   operator to modulus == 1, the elliptic operator to its finite sentinel
   (K = 1e300, E = 1 — kept verbatim as the source's contract), and the
   source response to a silent (2e293, NaN, NaN). This port rejects the
   configuration (`separation == 0` / `modulus == 1`) with ValueError.
2. **Negative raw radius rejection (registered hardening).** A raw
   observation radius in (-1e-8, 0) would turn positive solely through the
   axis offset; the saved implementation accepts it, this port rejects it.
3. **Overflow rejection (registered hardening).** Finite but extreme
   magnitudes (`r0 = rl = 1e308`; `current = turns = 1e308`) overflow the
   squared sums or the response factor; both operators raise instead of
   handing NaN/Inf downstream.
4. **Whole-array sentinel preserved** in the K/E operator (source contract):
   every-element m == 1 yields K = 1e300, E = 1; mixed arrays yield
   K = +Inf, E = NaN at the m == 1 elements. The response operator refuses
   the geometry that triggers them.
5. **No repair claims**: the source arithmetic (including the legacy
   arrangement of the closed form) is ported verbatim on accepted inputs;
   only the input/output boundary is hardened.

## Evidence

- 12 direct tests: geometry closed forms (exact offset equality, rtol=1e-15
  closed forms), polynomial-log K/E evaluation (exact array equality),
  response closed forms (exact float equality), linearity in current,
  midplane B_r cancellation for a mirrored pair, cross-implementation
  agreement with the baseline scipy asset (rtol 1e-12 at equal K/E; ≤1e-5
  relative with the source approximation over probed geometries, sampled
  evidence), the singular coincident-chain regression, negative-radius and
  overflow rejections. Per-call seeded fixtures; no module-level RNG.
- No separate replay file: the gseq saved packages ship package-level
  oracles rather than a pinned source-runtime replay target; the
  cross-implementation comparison against the baseline scipy asset provides
  the second arm. The test suite performs no automated drift detection
  against the saved bytes; the saved implementations' content digests are
  recorded as reference evidence in `build/test-evidence-r69.md` (the GSEQ
  bundle itself lives in the sibling main SciRel checkout, not in this
  intake worktree).
- 12 tests total; full-tree delta reconciles exactly (1486 -> 1498 source
  with replay; 1332/197 -> 1344/197 installed).

## Files

- `proposal/coil_green_geometry.py`, `proposal/complete_elliptic_integrals_approx.py`,
  `proposal/filament_coil_green_field.py`
- `proposal/test_filament_coil_green_gseq.py`
- `proposal/scirel.field.coil-green-geometry.json`,
  `proposal/scirel.field.complete-elliptic-integrals-approx.json`,
  `proposal/scirel.field.filament-coil-green-field.json`

## Version and impact

Version `0.1.0.dev42` -> `0.1.0.dev43`; catalog 132 -> 135 exact documents.
The other 132 documents change only in the mechanical
`implementation_version` bump. The response operator declares two
integration dependencies (geometry and elliptic operators). A neutral
particle transport domain draft (`docs/domains/neutral-particle-transport.md`)
is added in this batch, referencing exact documents only.
