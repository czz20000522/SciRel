# r75 expert-review packet and evidence-only successor addendum

Count correction (post-commit, labeled): this addendum originally said the
index binds "ten packet files" and that `proposal/` holds "nine
byte-identical copies". Correct counts: **nine packet files** (review.md
plus eight proposal copies) and **eight** proposal copies; the r75-v2
manifest's ten review materials are `docs/domains/fusion.md` plus those
nine packet files. The frozen r75-v2 snapshot is unchanged; only this
build-side evidence wording was corrected.

Read-only review found that the r75 freeze bound 151 exact documents and
only `docs/domains/fusion.md` as review material, with no r75 directory
under `review_candidates/` and no r75 entry in the candidate-materials
index — i.e. the expert-review three-piece entry point (candidate document
/ code / tests) that every prior new-asset batch (r49–r73) carries was
missing. r74 had none because it was a wording-only round; r75 adds new
assets, so the packet requirement applies.

## What was added (no science change)

- `review_candidates/2026-09-27-nbi-source-geometry/review.md` — the
  candidate document: base/comparison scope, proposed identities, close/
  defer record from the r72 deferred list, deduplication judgment,
  declared divergences (non-ported RNG boundary, candidate-ray parity,
  pinned infinite-line pair semantics, registered hardenings, preserved
  quirks), evidence reconciliation, and the file list.
- `review_candidates/2026-09-27-nbi-source-geometry/proposal/` — eight
  byte-identical copies of the integrated three-piece at the same commit:
  the three modules (`nbi_source_plane_ray.py`,
  `beam_grid_ray_intersection.py`, `nbi_trajectory_initialization.py`),
  the two test files (`test_nbi_source_geometry.py`,
  `test_graph_nbi_trajectory_initialization.py`), and the three exact
  documents. Byte identity verified 8/8 by SHA-256 against the integrated
  files at commit `2b922fb`.
- `docs/evaluations/candidate-review-materials-index-2026-09-25.md` — new
  "Batch r75" section binding the nine packet files by SHA-256 (review.md
  plus the eight proposal copies), noting that
  r75's science bytes were frozen (r75-v1) before the packet existed and
  that r74 was a wording-only round without a packet.

## Evidence-only successor freeze r75-v2

`build/verification/review-2026-09-27-r75-nbi-source-geometry-v2`
(commit `2b922fba90c1b6df5a361446cec9c45a56349f50`, `0.1.0.dev50`,
151 exact documents, `pending_unapproved`), created per the r66-v3
precedent that snapshots candidate files directly as review materials.
Identical scientific content to r75-v1: same exact-document set (the 151
document digests are unchanged), same wheel
(`95515acb…`, catalog root `fa189331…`), same dossier and test-evidence
bytes; the only delta is the ten review materials (fusion.md plus the nine
candidate-packet files). r75-v1 is preserved untouched.

## Review scope receipts (measured, read-only)

- v2, no comparison snapshot: `mode: first_review`, 151 assets,
  `baseline_approval_verified: false`
  (`build/r75-v2-review-scope-first.json`) — unchanged from v1; the
  review scope remains all 151 documents.
- v2 vs v1 comparison: `mode: snapshot_comparison`,
  `changed_document_ids` = 0 (`build/r75-v2-review-scope-comparison.json`)
  — the successor is evidence-only, exactly as claimed.

## Boundary

No science change, no wheel/catalog rebuild, no test-suite rerun (the
frozen test evidence and receipts remain the operative verification).
r75-v1 and r75-v2 are both `pending_unapproved`; nothing is expert
approval, trusted promotion, or a public release.
