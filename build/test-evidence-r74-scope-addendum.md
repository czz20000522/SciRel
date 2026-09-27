# r74 scope addendum (post-freeze, read-only verification; v2 correction)

## v2 refreeze (review-scope correction, c8f518e)

The r74-v1 addendum (commit `0251212`) stated "review_asset_ids equals
changed_document_ids: the expert review scope for r74 is exactly the two
corrected magnetic_field input descriptions plus the mechanical version bump
of the other 146 documents." A read-only Codex review correctly identified
this as a review-scope error: there is no trusted baseline, and
`docs/development-process.md` (freeze section) and
`docs/requirements/scirel-workflow.md` require that without a trusted
baseline the first-review set is ALL documents; an unapproved development
snapshot (r73-v2) can only serve as a development-delta navigation aid, and
`review_scope.py` itself reports `baseline_approval_verified: false` in both
modes. The addendum could not be silently edited: this correction is
recorded in a corrected dossier and a successor freeze.

r74-v2 `build/verification/review-2026-09-27-r74-firehose-tension-wording-v2`
(commit `c8f518ee66af37f4be46ff43ba8716376d03d03f`, tree
`37251e2e24dda665d849a0e6520dca4c229d401f`, `0.1.0.dev49`, 148 assets,
pending_unapproved) binds the corrected dossier
(`docs/evaluations/review-version-2026-09-27-r74.md`,
`sha256:310ddba448f53a665157c39f73334c3d66d22788b265e8a61d5c1845b861ee22`).
Everything else is byte-identical to v1: test evidence
`sha256:7763b1c44bbb2a62894ec8434a74735126a2be5b4baa53d3062c9d75638fd2d5`,
wheel `sha256:4796ff07cb13972fed6fe366d84ba70de22615b2893dfe5dd555a79da66f5ac9`
(reused; freeze re-validated wheel-vs-committed-source), catalog root
`sha256:66130f61f5e013370d0ffef7972f11c60749bd006709b86205458e9bb54c8d43`
(reused; freeze re-validated catalog-vs-documents). r74-v1
(`1da9e14`, manifest digest `sha256:daac861135c80c2769c47a3485fd6514eab183b77290353a7bc568d1f480c269`)
is preserved byte-for-byte and superseded, not edited. The r73-v1/v2
snapshots are untouched.

## Exact review_scope receipts (both modes, r74-v2, returncode-checked)

1. First-review mode (`python scripts/review_scope.py
   build/verification/review-2026-09-27-r74-firehose-tension-wording-v2`,
   no comparison snapshot; receipt `build/r74-v2-scope-first-review.json`):

   - mode: first_review
   - candidate commit: `c8f518e`
   - review_asset_ids: **all 148** exact documents — this is the expert
     first-review set (no trusted baseline exists)
   - baseline_approval_verified: false
   - removed_asset_ids: none; unresolved_source_paths: none

2. Development-delta navigation aid (`--comparison-snapshot
   build/verification/review-2026-09-27-r73-pointwise-firehose-margin-v2`;
   receipt `build/r74-v2-scope-comparison.json`):

   - mode: snapshot_comparison
   - candidate commit `c8f518e` vs r73-v2 `5241278`
   - changed_document_ids: 2 — `scirel.diagnostics.pointwise-firehose-margin`,
     `scirel.diagnostics.firehose-mirror-margins` (the two wording
     corrections)
   - mechanical_only_document_ids: 146 (implementation_version bump only)
   - baseline_approval_verified: **false** — r73-v2 is itself
     `pending_unapproved`; this comparison locates what changed since the
     previous development freeze and is NOT the review scope
   - removed_asset_ids: none; unresolved_source_paths: none;
     runtime_requirements_changed: false

The same two modes run against r74-v1 (before the refreeze) produced the
same scopes (first_review: 148; comparison: 2 + 146 mechanical), so the
scope correction changes only the wording of the record, not any artifact:
the science, documents, wheel, catalog and test evidence of v1 and v2 are
identical.

The qualified L1 delivery root was re-checked empty (0 items) at batch
start and after the v2 freeze.
