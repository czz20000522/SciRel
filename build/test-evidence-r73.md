# r73 test evidence — pointwise firehose-margin relation

Base r72 `c1f7fcd` (147 assets, dev47, frozen snapshot
`build/verification/review-2026-09-27-r72-cross-node-leaves-v3`) -> r73
`0.1.0.dev48` (148 assets). One new operator in `scirel.diagnostics`:
`scirel.diagnostics.pointwise-firehose-margin`
(`compute_pointwise_firehose_margin`), the pointwise
`B^2/mu0 + p_perp - p_parallel` relation in Pa with no derivative, no mirror
branch, no minimum reduction and no stable flag. No incoming source of any
kind; the relation is an independent SciRel-maintained decomposition of the
already-maintained combined diagnostic, motivated by the 2026-09-27 outbound
holdout evidence (flat-b: 3 invocations with `mirror_branch_applicable=false`;
state-json: degenerate positive mirror values with `mirror_sample_flag=True`
on one-sample states). The r72 snapshots are untouched.

## Shell record

All counted gates, builds and the freeze ran under pwsh 7+ / Git Bash with
`PYTHONDONTWRITEBYTECODE=1` and explicit `PYTHONPATH`;
`SCIREL_KN1DPY_REVIEW_ROOT` pointed at the saved KN1DPy bundle under the
sibling main SciRel checkout (read-only, for the pre-existing replay tests
only — this batch consumes no saved source). The qualified L1 delivery root
(`D:/Users/26569/Desktop/归档_项目/codefusion/最小闭环压测环境`) was re-checked
empty (0 items) at batch start.

## Environment diagnostic (preserved, not hidden)

The host global Python 3.14 site-packages was temporarily altered by an
outbound experiment during this batch (scirel force-reinstalled to dev39,
later restored to dev24, leaving a transient mixed dev24/dev39 state). The
baseline source-tree run in that environment recorded exactly one failure,
`test_admitted_wheel_runs_the_source_free_user_acceptance`, at
`examples/user_acceptance.py:37`: the test's nested venv was created with
`system_site_packages=True`, and the polluted host site-packages could
precede the environment path in `sys.path`, so the historical wheel resolved
outside `sys.prefix`. The failure was preserved as a diagnostic; the test was
NOT weakened. The test isolation was fixed instead (`8b8dd15`-style
environment blocker removed at the root cause): `system_site_packages=False`,
dependency roots injected via `.pth` into `sysconfig.get_path('purelib')`
queried inside the nested interpreter (Windows `getsitepackages()[0]` is the
venv root, where `.pth` files are never processed — the resolution trap), and
the in-venv import assertion retained. After the fix the test passes in the
polluted environment and in clean environments. No frozen evidence was
edited.

## Test delta (collect-verified)

- `test_pointwise_firehose_margin.py`: 10 direct tests — elementwise closed
  form on unsorted samples; one-sample and all-equal-B validity (the holdout
  input shapes); bit-identical equality with the combined diagnostic's
  `firehose_margin` field over randomized finite inputs; output-key contract
  (exactly `firehose_margin`; the five mirror/minimum/stable keys asserted
  absent); faithful negative-margin return; shape/empty/nonfinite/mu0
  rejections; non-scalar mu0 rejection before arithmetic (list, tuple, 1-D
  and 2-D arrays — a review-scope regression: a 1-element array mu0
  broadcast the output to shape (1,)); float64 overflow gate with `errstate`
  suppression of the intermediate warning; 0-d scalar shape/dtype; mu0
  override arithmetic.
- 10 new tests. Full-tree delta: 1583 -> 1593 collected; source runs
  1540 -> 1550 (replay active) and 1388 -> 1399 (no replay root; polluted
  global environment, final post-fix run); installed receipts below.
- Selection checks: `scripts/select_affected_tests.py` maps the new asset to
  its direct test plus `tests/test_admitted_integrations.py`
  (`full_suite_required: false`); the count-sync engineering tests pass with
  148/149 fixtures.

## Gates (final bytes, returncode-checked)

- Source-mode full tree, replay root active: **1550 passed, 43 skipped,
  0 failed**, pytest returncode 0 (r72 full tree: 1540, +10).
- Source-mode full tree, no replay root, polluted global environment, BEFORE
  the test-isolation fix: 1398 passed, 194 skipped, 1 failed
  (`test_admitted_wheel_runs_the_source_free_user_acceptance`) — preserved
  diagnostic above. Final source-mode no-replay run AFTER the fix:
  **1399 passed, 194 skipped, 0 failed** (baseline 1388 passed + 10 new
  tests + 1 previously-failing test now passing).
- Document validation, source state: **148/148**, `runtime_origin: source`,
  `examples_executed: true` (including the new document's example).
- Clean venv `build/venv-r73-clean` (own numpy 2.5.3 / scipy 1.18.1 /
  pytest 9.1.1 from `build/dependency-wheelhouse`, PLUS setuptools
  84.0.0 added to the wheelhouse and installed so the nested-wheel
  acceptance test actually executes instead of skipping), wheel installed
  `--no-index --no-deps`; explicit import-path check:
  `scirel.__file__` resolves inside the venv prefix.
- Installed document validation from the clean venv
  (`--installed-runtime`, `python -I`): **148/148**,
  `runtime_origin: installed`, `examples_executed: true`, returncode 0.
- Installed full tree (dev48 wheel in clean venv, `SCIREL_INSTALLED_RUNTIME=1`,
  `-I -o pythonpath=`): **1398 passed, 195 skipped, 0 failed**, pytest
  returncode 0, INCLUDING the executed-and-passed
  `test_admitted_wheel_runs_the_source_free_user_acceptance` (10/10 in its
  module). Reconciliation: r72 installed receipts 1386/197 had the two
  wheel-building tests skipped for lack of setuptools; with setuptools
  present both run and pass, giving +10 new tests +2 recovered skips =
  1398 passed, 197-2=195 skipped.
- Catalog `build/catalog/r73`: `complete: 148/148`, root digest
  `sha256:0f6c5cf533016ad4a1b0d7d76cdc7d884cdabc8978e11b79d57931c6462f5f03`.
  Prior catalog builds are preserved and unreferenced by this freeze.
- Internal wheel `scirel-0.1.0.dev48-py3-none-any.whl`, SHA-256
  `284513daa5e4e6ed69c06e3706defd66c4887559fbf8d005b9ff7430b378afe3`.
- Candidate review-material index: batch r73 added (4 entries covering
  review.md, the proposal module, test and exact document), every entry
  resolves and matches its recorded SHA-256 (script-verified).
- Domain draft `docs/domains/anisotropic-pressure-diagnostics.md` updated:
  third diagnostic bullet added; the closing paragraph now covers all three
  diagnostics and explicitly limits the derivative/duplicate-B rules to the
  two derivative-bearing assets (review finding applied).
