# r73 scope addendum (post-freeze, read-only verification)

`python scripts/review_scope.py build/verification/review-2026-09-27-r73-pointwise-firehose-margin-v1 --comparison-snapshot build/verification/review-2026-09-27-r72-cross-node-leaves-v3`:

- mode: snapshot_comparison; candidate commit `6475cae` vs r72-v3 `c1f7fcd` (v1; superseded in place by v2 below)
- changed_document_ids: 1 — `scirel.diagnostics.pointwise-firehose-margin` (the new asset)
- mechanical_only_document_ids: 147 (implementation_version bump only)
- removed_asset_ids: none; unresolved_source_paths: none; runtime_requirements_changed: false

The expert review scope for r73 is exactly the one new relation plus the
mechanical version bump of the other 147 documents.

## v2 refreeze (dossier correction, 5241278)

The v1 dossier carried three stale pre-freeze draft numbers; corrected and
re-frozen at `build/verification/review-2026-09-27-r73-pointwise-firehose-margin-v2`
(commit `5241278`, tree `030782832b030f293eed515e511e454c408a79d5`). Same
wheel/catalog/materials digests; only the dossier digest changed
(`8dc07363...` -> `a84208de...`). review_scope v2 vs v1: zero changed
documents (dossier-only difference); v2 vs r72-v3: one non-mechanical
change (the new asset), 147 mechanical, no removals, no unresolved source
paths, runtime requirements unchanged. v1 verified preserved byte-for-byte
(aggregate SHA-256 over all snapshot files unchanged before/after the v2
freeze: `773bfb7d...`).
