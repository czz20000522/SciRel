# r73 scope addendum (post-freeze, read-only verification)

`python scripts/review_scope.py build/verification/review-2026-09-27-r73-pointwise-firehose-margin-v1 --comparison-snapshot build/verification/review-2026-09-27-r72-cross-node-leaves-v3`:

- mode: snapshot_comparison; candidate commit `6475cae` vs r72-v3 `c1f7fcd`
- changed_document_ids: 1 — `scirel.diagnostics.pointwise-firehose-margin` (the new asset)
- mechanical_only_document_ids: 147 (implementation_version bump only)
- removed_asset_ids: none; unresolved_source_paths: none; runtime_requirements_changed: false

The expert review scope for r73 is exactly the one new relation plus the
mechanical version bump of the other 147 documents.
