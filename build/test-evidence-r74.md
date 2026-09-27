# r74 test evidence — firehose B^2/mu0 wording correction (magnetic tension)

Base r73-v2 `5241278` (148 assets, dev48, frozen snapshot
`build/verification/review-2026-09-27-r73-pointwise-firehose-margin-v2`) -> r74
`0.1.0.dev49` (148 assets). Pure wording correction: no `src/scirel` byte
changes, no formula, numeric, API, tolerance or default change, no new or
removed asset. The scientific wording fix: SI magnetic pressure is
`B^2/(2*mu0)`; `B^2/mu0` inside the firehose margin is the magnetic-tension
contribution in pressure units. Changed: two exact-document input
descriptions (`scirel.diagnostics.pointwise-firehose-margin`,
`scirel.diagnostics.firehose-mirror-margins`), two test names plus their
comments in `tests/operator_contracts/test_pointwise_firehose_margin.py`
(bodies byte-identical), and the mechanical `implementation_version` bump
dev48 -> dev49 across all 148 exact documents and `pyproject.toml`.

## Shell record

All counted gates, builds and the freeze ran under pwsh 7+ in
`D:\software\PyCharm 2025.3.3\workspace\SciRel-intake-20260925` with
`PYTHONDONTWRITEBYTECODE=1`, explicit `PYTHONPATH` where the selector needs
it, and `SCIREL_KN1DPY_REVIEW_ROOT` pointed at the saved KN1DPy bundle in the
sibling main SciRel checkout
(`D:\software\PyCharm 2025.3.3\workspace\SciRel\build\verification\neutral-harness-baseline-v3\inputs\l1\KN1DPy`,
7 items; used only by the pre-existing replay tests — this batch consumes no
saved source). The qualified L1 delivery root
(`D:/Users/26569/Desktop/归档_项目/codefusion/最小闭环压测环境`) was re-checked
empty (0 items) at batch start.

Correction provenance (recorded, not hidden): the wording edits and a first
validation pass were originally made inside a nested Git worktree
(`.claude/worktrees/r74-tension-wording`, commit `8ea24e5`, branch
`r74-firehose-tension-wording`), where the harness blocked pwsh and forced a
Git Bash bypass; that bypass was rejected as invalid verification. The
preserved commit was transferred byte-exact into this checkout
(`git apply --binary` of `git diff 6586ce8 8ea24e5`; all 150 changed files
compared SHA-256 between the two working trees: 150/150 identical; the nested
worktree was removed only after this comparison, the branch and commit
remain). Every counted receipt below was then measured under pwsh in this
checkout against the transferred bytes.

## Test delta (collect-verified)

- 0 new tests, 0 removed tests, 0 modified test bodies. Two tests renamed:
  `test_overflowing_magnetic_pressure_fails_closed` ->
  `test_overflowing_magnetic_tension_term_fails_closed`;
  `test_mu0_override_changes_only_the_magnetic_pressure_term` ->
  `test_mu0_override_changes_only_the_magnetic_tension_term`. Both renamed
  tests were executed by name in source state and in the installed clean
  venv: 2 passed in both.
- Full-tree counts are unchanged from r73 (rename only), and every measured
  receipt below reproduces the r73 numbers exactly.

## Gates (final bytes, returncode-checked)

- Affected selection: `scripts/select_affected_tests.py --format json` over
  the 150-file workspace change reported `full_suite_required: true` (public
  baseline change: `pyproject.toml` plus 148 exact documents), so the full
  suite ran — consistent with the freeze gate requiring full-tree evidence.
- Source-mode full tree, replay root active: **1550 passed, 43 skipped,
  0 failed**, pytest returncode 0, 229.29 s (identical to r73-v2 receipts).
- Document validation, source state: **148/148**, `runtime_origin: source`,
  `examples_executed: true`, returncode 0 (receipt
  `build/r74-source-doc-validation.json`).
- Clean venv `build/venv-r74-clean` (Python 3.14.3; numpy 2.5.3, scipy
  1.18.1, pytest 9.1.1, setuptools 84.0.0 installed offline from
  `build/dependency-wheelhouse`; no system site-packages), dev49 wheel
  installed `--no-index --no-deps --force-reinstall`; explicit `-I` import
  check: `scirel.__file__` resolves inside the venv prefix, installed
  distribution version reads `0.1.0.dev49`.
- Installed document validation from the clean venv (`-I`,
  `--installed-runtime`): **148/148**, `runtime_origin: installed`,
  `examples_executed: true`, returncode 0 (receipt
  `build/r74-installed-doc-validation.json`).
- Installed full tree (`-I`, `SCIREL_INSTALLED_RUNTIME=1`, `-o pythonpath=`):
  **1398 passed, 195 skipped, 0 failed**, pytest returncode 0, 226.93 s —
  identical to the r73-v2 installed receipts, including the executed-and-
  passed `test_admitted_wheel_runs_the_source_free_user_acceptance`
  (re-run by name in the same venv: 1 passed).
- Catalog `build/catalog/r74`: `complete: 148/148`, root digest
  `sha256:66130f61f5e013370d0ffef7972f11c60749bd006709b86205458e9bb54c8d43`.
  Prior catalog builds are preserved and unreferenced by this freeze.
- Internal wheel `build/wheel-r74/scirel-0.1.0.dev49-py3-none-any.whl`,
  SHA-256
  `4796ff07cb13972fed6fe366d84ba70de22615b2893dfe5dd555a79da66f5ac9`.
- Domain draft `docs/domains/anisotropic-pressure-diagnostics.md` was audited
  for the same defect and needs no change: it states the formulas without
  calling `B^2/mu0` a magnetic pressure. Frozen material
  (`review_candidates/2026-09-27-pointwise-firehose-margin/proposal/*`,
  `provenance/pleiades-import.json`, the r73 evaluation dossier and the
  r73-v1/v2 snapshots) carries the same historical wording and is preserved
  untouched by design: frozen records are not rewritten.

## Boundary

No new qualified L1 consumption, no new scientific behavior, no expert
approval, no trusted promotion, no public release are claimed. The 2026-09-27
outbound holdout follow-up evidence remains unfrozen and is not claimed here.
