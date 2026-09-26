# r66 test evidence — KN1DPy collision frequency contraction family

Base r65 `228a2d6` (126 assets, dev39, frozen snapshot
`build/verification/review-2026-09-26-r65-terminal-molecular-v6`) -> r66
`0.1.0.dev40` (128 assets). Two new operators in `scirel.kinetic`:
`atomic-alpha-contraction` and `molecular-alpha-contraction`. Saved arms
reproduced bit for bit on the declared domain (atomic verbatim; molecular
reproduces the saved formal implementation carrying the registered
kinetic_h2.py:1204 Alpha_CX reshape repair). The r65 freeze is untouched.

## Shell record

All counted gates, builds and the freeze ran under Git Bash on Windows with
`PYTHONDONTWRITEBYTECODE=1` / `python -B` and explicit `PYTHONPATH` /
`SCIREL_KN1DPY_REVIEW_ROOT` set in-process. The replay arm's
`SCIREL_KN1DPY_REVIEW_ROOT` points at
`SciRel/build/verification/neutral-harness-baseline-v3/inputs/l1/KN1DPy`
(the `KN1DPy-631d0bf1` bundle; strict D1 withdrawn, provisional). Saved-tree
imports read-only; zero writes.

## Test delta (collect-verified)

- `test_alpha_contraction.py`: 7 direct tests (including the asymmetric-SIG
  discriminating test with a one-hot SIG[5,3]=1 + Fortran-order labelled fH
  carrier witness, and both ni_correct branches)
- `test_alpha_contraction_l1.py`: 5 environment-gated replay tests
  (bit-for-bit saved-arm parity per operator, rejection agreement,
  asymmetric-SIG parity across both ni_correct branches)
- Total 12 new tests; `pytest --collect-only` verified (12 collected).

## Receipt-defect fix (this session)

The stale b5h3q6w78 full-tree receipt (5 failed, 1415 passed, 43 skipped,
16 errors) was reproduced and traced to stale asset-count assertions: the
two r66 exact documents moved `catalog/examples` to 128 while the test
files still pinned 126/127, so `build_catalog`'s
`declared_total cannot be smaller than included assets` gate fired inside
`test_asset_documentation.py` (4 failures) and the `test_thin_mcp_adapter`
catalog fixture (16 errors) plus the asset-index assertion in
`test_affected_test_selection.py` (1 failure). Fix: counts 126 -> 128,
gate fixtures 127 -> 129. The earlier "1436 passed" dev40 receipt was from
before the two exact documents existed and was not reused.

## Gates (final bytes)

- Source-mode full gate (replay active):
  **1436 passed, 43 skipped, 0 failed**
  (log line `1436 passed, 43 skipped, 7 warnings in 220.52s`; r65: 1424
  passed, +12).
- Document validation, source state: **128/128**, `runtime_origin: source`,
  `examples_executed: true`.
- Clean venv `build/venv-r66-clean` (own numpy 2.5.3 / scipy 1.18.1 /
  pytest 9.1.1, `include-system-site-packages = false`), wheel installed
  `--no-index --no-deps`: installed version reads `0.1.0.dev40`, isolated
  `-I` import resolves inside the venv prefix.
- Same validator from the clean venv with `--installed-runtime`:
  **128/128**, `runtime_origin: installed`, `examples_executed: true`.
- Installed full tree: **1290 passed, 189 skipped, 0 failed**
  (`SCIREL_INSTALLED_RUNTIME=1`, `python -I -B -m pytest -q -o pythonpath=
  -p no:cacheprovider tests/`; log line `1290 passed, 189 skipped,
  7 warnings in 202.93s`; r65: 1283 passed, 184 skipped).
- Catalog `build/catalog/r66`: `complete: 128/128`, root digest
  `sha256:73473c7a6641d29d7cfc6769d995d2c650eb5071faea7bcb00d33dffa6c474d3`.
  The superseded pre-rewrite catalog build (`root_digest sha256:5b75e4b2...`,
  built from the placeholder-port documents) is preserved at
  `build/catalog/r66-stale-placeholder-docs/` and never referenced by any
  freeze.
- Internal wheel `scirel-0.1.0.dev40-py3-none-any.whl`, SHA-256
  `be8e86b95de14c65e8e7035f253507f065c576b0ee74ea13bdce68ebfac705f5`
  (rebuild of `build/wheel-r66/` after the document rewrite; `src/scirel`
  unchanged since e97fa1a).
- Candidate review-material index: batch r66 added (7 entries covering
  review.md and 6 proposal files under
  `review_candidates/2026-09-27-alpha-contraction/`), every entry resolves
  and matches its recorded SHA-256 (script-verified).

## v2 corrections (same version, same science)

v1 stayed frozen and untouched at
`build/verification/review-2026-09-27-r66-alpha-contraction-v1` (commit
`33653d5`). The v2 freeze
(`build/verification/review-2026-09-27-r66-alpha-contraction-v2`) binds
corrected bytes with version `0.1.0.dev40` and `src/scirel` unchanged:

- `review.md`: r65 freeze path corrected to
  `build/verification/review-2026-09-26-r65-terminal-molecular-v6`
  (commit `228a2d6`); the Evidence section now states the real direct-test
  ceiling (the one-hot F-order carrier witness covers the atomic `Alpha_H_H`
  family only) plus the SHA-256-pinned saved-formal replay and the external
  `validation_oracle_gap`, instead of implying a whole-family independent
  recomputation.
- Both r66 exact documents (integrated and proposal copies byte-identical):
  `evidence_ceiling` narrowed the same way.
- `test_alpha_contraction.py` (integrated and proposal copies): comment-only
  fix -- with nvr=3 the F-order flat index 3 maps to `(0,1)`, not `(1,1)`
  (`fH_labelled[0,1,0]`); no assertion changed.
- `scripts/freeze_review_version.py`: review materials now also accept
  tracked `review_candidates/` files, so the v2 manifest lists the seven
  candidate three-piece-set files directly.
- Candidate review-material index: r66 batch digests updated for the four
  changed files; script-verified 7/7 r66 entries resolve and match (the 10
  residual mismatches sit in superseded r60/r61/r62 batches and predate this
  session).

## v2 gates

- Affected-mode selection over the corrected bytes with the replay root
  active: **1436 passed, 43 skipped, 0 failed** (`pwsh ./scripts/check.ps1
  -Mode affected` with `SCIREL_KN1DPY_REVIEW_ROOT` pointing at the saved
  bundle under the sibling SciRel checkout, read-only; this exercised the
  full current tree's test set including both alpha files' replay arms).
- Without the replay root the same selection gives 1293 passed,
  186 skipped -- both numbers are expected states, neither is a failure.
- Document validation, source state, after the `evidence_ceiling` narrowing:
  **128/128**, `runtime_origin: source`, `examples_executed: true`.
- Catalog rebuilt at `build/catalog/r66-v2` (v1's `build/catalog/r66`
  preserved): `complete: 128/128`, root digest
  `sha256:690006fbd78ed9f856b6841deb1a8f114d94e90bba4d2bae1c336243ba97a558`.
- Wheel reused unchanged from `build/wheel-r66/`:
  `scirel-0.1.0.dev40-py3-none-any.whl`, SHA-256
  `be8e86b95de14c65e8e7035f253507f065c576b0ee74ea13bdce68ebfac705f5`;
  `src/scirel` is byte-identical to v1's frozen tree, so the v1
  installed-runtime receipts (128/128 installed validation, 1290 passed /
  189 skipped installed tree) remain valid for v2.

## v3 correction (tooling scope only)

v2 stayed frozen and untouched at
`build/verification/review-2026-09-27-r66-alpha-contraction-v2` (commit
`09096b3`). Its freeze-script draft admitted any tracked file under
`review_candidates/` as a review material, which exceeds the surface needed
for the candidate three-piece set. The v3 freeze
(`build/verification/review-2026-09-27-r66-alpha-contraction-v3`) freezes
the tightened rule with the exact same 7-file material set; science,
version, wheel, catalog and exact documents are byte-identical to v2.

- `scripts/freeze_review_version.py`: besides tracked `docs/*.md`, review
  materials now admit exactly `review_candidates/<batch>/review.md` and
  `review_candidates/<batch>/proposal/*.py|*.json`; clean-Git, in-repo-path,
  repeat-rejection and copy-then-digest checks unchanged.
- `tests/test_review_version_freeze.py`: +9 focused regressions -- the 7
  current r66 candidate files are accepted and snapshotted; batch-root files
  other than review.md, deeper/nested candidate paths, proposal Markdown,
  non-py/json proposal extensions, and untracked candidate files are
  rejected. File total: 22 passed.
- Affected-mode selection over the v3 bytes with the replay root active:
  **22 passed** (the freeze-tooling tests are the only affected set; `src/`
  and `catalog/examples` are byte-identical to v2, so v2's full-tree receipt
  1436 passed / 43 skipped and installed receipts remain the valid science
  evidence for v3).
- Dossier and candidate-material index updated to describe the tightened
  rule and the v1->v2->v3 chain.
