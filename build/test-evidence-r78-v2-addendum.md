# r78-v2 successor evidence addendum — dossier wording correction

r78-v1 (commit `bba6223` freeze record; science HEAD `a8ca079`,
`0.1.0.dev55`, snapshot
`build/verification/review-2026-09-27-r78-beam-deposition-family-v1`) is
preserved untouched. Read-only review found one wording inconsistency in
the r78 dossier (`docs/evaluations/review-version-2026-09-27-r78.md`):
line 29 described the track leaf's plasma-crossing location as a
bisection ("50 步穿越二分") while line 9 and the exact document correctly
describe the saved source's algorithm — 50 fixed linear subdivisions of
the segment duration (a linear scan for the first step whose endpoint
crosses the boundary; saved anchor src/fidasim.f90 track, reproduced
verbatim in `beam_grid_ray_segment_tracking.py`). Line 29 was corrected
to "50 次固定细分定位穿越" (fix commit `03c295a`). No code, exact-document
or artifact byte changed.

## Byte-identity verification against the frozen r78-v1 snapshot

- All **162/162** exact documents re-hashed against the frozen v1
  manifest digests: **zero mismatches** (procedure: sha256 per file
  versus `manifest.json.exact_documents`, measured after `03c295a`).
- Internal wheel re-hashed: **unchanged**,
  `sha256:591a42918a7f15ca12d59ccfd580d1056b6c09ef8b51555906540bec9eedd73b`.
- Catalog `build/catalog/r78` re-read: **unchanged** root digest
  `sha256:f16f84e0a46e9552b64f0e2e9804bcc3b6ee9135dc390d5d0179b9420d6fbfbf`,
  `complete: 162/162`.

Because every verified artifact is byte-identical to r78-v1, the measured
gates recorded in `build/test-evidence-r78.md` (source full tree 1634
passed / 43 skipped; installed full tree 1633 / 44; document validation
162/162 in both modes) remain the measured receipts for r78-v2; no test
population or runtime changed.

## Boundary

No qualified L1 consumption, no expert approval, no trusted promotion, no
public release are claimed. r78-v1 remains frozen and preserved; r78-v2
is the current pending_unapproved successor and differs from r78-v1 in
the review dossier text only.
