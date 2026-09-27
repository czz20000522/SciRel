# r75 post-freeze review-scope addendum (measured receipts)

Frozen snapshot: `build/verification/review-2026-09-27-r75-nbi-source-geometry-v1`
(commit `6f57c69e8bd5335533696f78f1a0e346db35895e`, tree `f0198d679f730fb6dee30f350d652da6cadcc91a`,
`0.1.0.dev50`, 151 exact documents, `review_status: pending_unapproved`).
The frozen `build/test-evidence-r75.md` bytes are unchanged by this
addendum; the dossier file in the snapshot is likewise untouched.

## Review scope (read-only `scripts/review_scope.py`, both modes measured)

- **No trusted baseline** — first-review mode (no comparison snapshot):
  `mode: first_review`, `review_asset_ids` = **all 151 assets**,
  `baseline_approval_verified: false` (receipt
  `build/r75-review-scope-first.json`). This is the expert review scope.
- **Navigation aid only** — comparison against r74-v2
  (`--comparison-snapshot build/verification/review-2026-09-27-r74-firehose-tension-wording-v2`):
  `mode: snapshot_comparison`, `changed_document_ids` = 3
  (`scirel.fusion.beam-grid-ray-intersection`,
  `scirel.fusion.nbi-source-plane-ray`,
  `scirel.fusion.nbi-trajectory-initialization`), `mechanical_only_document_ids` = 148
  (dev49 -> dev50 version bump), `baseline_approval_verified: false`
  (receipt `build/r75-review-scope-comparison.json`). r74-v2 is itself a
  `pending_unapproved` development snapshot; this comparison only helps
  locate what changed since the previous development version and is not
  the review scope, nor does it treat r74-v2 as a trusted baseline.

## Post-freeze input re-check

- Qualified L1 delivery root
  (`D:/Users/26569/Desktop/归档_项目/codefusion/最小闭环压测环境`)
  re-checked empty (0 items) after the freeze.
- Working tree clean at `6f57c69`; frozen snapshot dirs and prior
  evidence preserved read-only.

## Boundary

No expert approval, trusted promotion, or public release is claimed.
`pending_unapproved` records evidence binding only.
