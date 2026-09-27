# r79 test evidence — FIDASIM neutral-reservoir/population merge family

Base r78-v2 `01f3988` (science HEAD `a8ca079`, 162 assets,
`0.1.0.dev55`, frozen snapshot
`build/verification/review-2026-09-27-r78-beam-deposition-family-v2`)
-> r79 `0.1.0.dev56` (166 assets), science HEAD `987c7f2`. Four new
fusion assets from the saved FIDASIM bundle (framework node N3
`neutral_population_transport`): `scirel.fusion.neutral-population-density-merge`,
`scirel.fusion.neutral-population-grid-merge`,
`scirel.fusion.neutral-reservoir-merge`, and the composition task graph
`scirel.fusion.neutral-population-state-merge`. The saved single-node
delegation graph 中性库合并图 is not ported (ports equal the operator's
contract one-to-one; DCXHalo迭代反馈图 precedent, registered deviation).

## Shell record

Early development probes ran under Git Bash in the isolated worktree
`.claude/worktrees/r79-neutral-merge` (branch
`codex/r79-neutral-merge-family`, science commit `987c7f2`
fast-forwarded to the single-writer branch
`codex/kn1dpy-maxwellian-rate-intake` before the gates). Their probe
results are superseded by the final pwsh gates below and are retained
in the process record, not as gate receipts. Two probe-run defects were
found and are retained here as failure records:

1. A Bash full-suite probe piped pytest through `tail`, so the outer
   `[exited with code 0]` was tail's status, not pytest's; the real
   summary was `5 failed, 1636 passed, 43 skipped, 16 errors`. The
   outer 0 was not treated as a pass. Of the five failures, one is
   fully attributed: `test_asset_documentation.py::test_complete_catalog_cannot_hide_missing_documents`
   hit the stale `declared_total=163` expected-count assertion (the
   r78 round's 162+1; this round is 166+1=167), fixed by the count
   bump before any gate. The remaining failures and the 16 errors are
   attributed to file contention with the concurrently started
   catalog/wheel builds only to the extent supported by evidence: the
   same files passed when re-run alone, and the identical suite passed
   cleanly (gate 1) once nothing ran concurrently — a per-test
   failure-by-failure diagnosis of that transient run was not
   preserved, so no stronger claim is made. All formal gates were
   re-run without pipes and with captured exit codes.
2. The first installed full-tree gate (gate 6) was run without
   `SCIREL_INSTALLED_RUNTIME=1`, so `tests/conftest.py` would not have
   bound the candidate fixture to the installed wheel; the run failed
   (`1 failed, 1623 passed, 40 skipped, 36 errors`) and the record is
   retained. The corrected gate below sets the variable, clears
   `PYTHONPATH`, and verifies `scirel.__file__` resolves inside the
   clean venv.

A third pre-freeze review finding was closed in the science commit
before any freeze: the reservoir leaf's `_finite_array` rejected only
bool-dtype arrays, so a mixed object array such as
`np.asarray([True, 1.0], dtype=object)` was silently numerified by
`astype(float)`; the mixed-object form is now rejected everywhere
(weights, velocities, initialization uniforms, replacement uniforms,
both-full uniforms) with a discriminating regression
(`test_mixed_object_boolean_entries_are_numerification_rejected_everywhere`).

All final gates ran under pwsh 7+ in
`D:\software\PyCharm 2025.3.3\workspace\SciRel-intake-20260925` at
science HEAD `987c7f2`, with `PYTHONDONTWRITEBYTECODE=1`,
`python -B`, gate scripts parse-checked with
`Parser::ParseFile` before execution (the first gate-1 attempt was
discarded before start: its `param()` block followed
`Set-StrictMode`, a pwsh parse error; the script was fixed and
PARSE-OK before any run). `SCIREL_KN1DPY_REVIEW_ROOT` pointed at the
saved KN1DPy bundle in the sibling main SciRel checkout (used only by
the pre-existing replay tests). The qualified L1 delivery root
(`D:/Users/26569/Desktop/归档_项目/codefusion/最小闭环压测环境`) was
re-checked empty (0 items, including hidden entries) at batch start.
The FIDASIM saved bundle was read (zero writes) as provisional
evidence only. Saved-implementation content digests are recorded per
asset in the exact documents' provenance sections.

## Gates (final bytes at `987c7f2`, real captured exit codes)

- Gate 1, source full tree, replay root active
  (`build/r79-gate-1-source-fullsuite.ps1`, log
  `build/r79-pwsh-source-fullsuite.log`, junit
  `build/r79-source-fullsuite-junit.xml`): **1657 passed, 43 skipped,
  0 failed**, exit code 0, 250.65 s (r78-v2: 1634/43; +23 family
  tests).
- Gate 2, document validation, source state
  (`build/r79-gate-2-5-build-validate.ps1`, receipt
  `build/r79-source-doc-validation.json`): **166/166**,
  `runtime_origin: source`, `examples_executed: true`, exit code 0.
- Gate 3, internal wheel build (`build/r79-wheel-build.log`):
  `scirel-0.1.0.dev56-py3-none-any.whl`, SHA-256
  `1a30d6582ac98478790c3712ea0914aabab3918c13a6f73e5249498343df9df6`.
- Gate 4, clean venv install (`build/r79-wheel-install.log`):
  `build/venv-r75-clean` (numpy 2.5.3, scipy 1.18.1, pytest 9.1.1,
  setuptools 84.0.0 offline from `build/dependency-wheelhouse`; no
  system site-packages), dev56 wheel installed
  `--no-index --no-deps --force-reinstall`, exit code 0.
- Gate 5, installed document validation (`-I`, `--installed-runtime`,
  receipt `build/r79-installed-doc-validation.json`): **166/166**,
  `runtime_origin: installed`, `examples_executed: true`, exit code 0.
- Gate 6, installed full tree (`build/r79-gate-6-7-installed-catalog.ps1`,
  log `build/r79-pwsh-installed-fullsuite.log`, junit
  `build/r79-installed-fullsuite-junit.xml`; `SCIREL_INSTALLED_RUNTIME=1`,
  `PYTHONPATH` cleared, `-I`): **1656 passed, 44 skipped, 0 failed**,
  exit code 0, 238.11 s; junit confirms 1700 tests, 0 errors, 0
  failures, 44 skipped; `scirel.__file__` verified inside the venv
  (`build/venv-r75-clean/Lib/site-packages/scirel/__init__.py`).
- Gate 7, catalog `build/catalog/r79` (`build/r79-catalog-build.log`):
  `complete`, declared_total 166, root digest
  `sha256:a4e7abe9b74f57f797a1a1018d9a38cdd0d7b65fdfd69b62722e3a28917dba64`.

## Test delta (collect-verified)

- 23 new tests in
  `tests/operator_contracts/test_neutral_merge_family.py` (saved probes
  for all four assets, the source-quirk pins — lazy init,
  W-update-before-horizon, strict float32 both-full selection, the
  res2=res1 broadcast, the append walk's first-record slot rewrite —
  the registered hardenings, and the end-to-end witness merging two
  NDMC-produced six-level population grids).
- Count-sync edits: `tests/test_asset_documentation.py` (166/167),
  `tests/test_affected_test_selection.py` (166),
  `tests/test_thin_mcp_adapter.py` (declared_total=166).
- Source full tree 1634 (r78-v2) + 23 = 1657, matching the measured
  receipt.
- Affected-mode selection on the working tree returned
  `full_suite_required: true` (pyproject.toml is in FULL_SUITE_PATHS),
  consistent with running the full tree as the gate.

## Boundary

No qualified L1 consumption, no external physical correctness claim, no
expert approval, no trusted promotion, no public release are claimed.
Deferred from this round: real-HDF5 table drivers, the NPA/FIDA
weight-production chain, MC marker production, the parallel (MPI-rank)
reservoir merge graphs, and the neutral-bank lifecycle.

## r79-v2 successor evidence addendum — source-free usage gate (no science change)

r79-v1 (freeze commit `ef095e2`, science HEAD `987c7f2`, snapshot
`build/verification/review-2026-09-27-r79-neutral-merge-family-v1`) is
preserved untouched. Read-only review of the v1 freeze verified the
manifest digests (166 documents, wheel, catalog root) and confirmed a
review-scope gap in the usage evidence: gates 5/6 import from the venv
site-packages but run with the repository checkout as the working
directory, so they do not by themselves demonstrate that the four new
assets are callable outside the source tree.

### Gate 10 — source-free public API usage (final pwsh 7+ receipt)

`build/r79-gate-10-sourcefree-usage.ps1` (PARSE-OK first, log
`build/r79-pwsh-sourcefree-usage.log`): the clean venv's
`build/venv-r75-clean/Scripts/python.exe` (numpy 2.5.3 / scipy 1.18.1 /
pytest 9.1.1, no system site-packages) ran
`-I -B r79_sourcefree_usage.py` from the isolated directory
`C:\Users\26569\.claude\jobs\d48db198\tmp\scirel-r79-sourcefree`
(outside the repository), with `PYTHONPATH` unset (verified None at
runtime), `PYTHONDONTWRITEBYTECODE=1`, and the installed dev56 wheel
(SHA-256 `1a30d6582ac98478790c3712ea0914aabab3918c13a6f73e5249498343df9df6`,
byte-identical to the frozen v1 wheel). Recorded at runtime: cwd =
the isolated directory; `scirel.__file__` =
`...\build\venv-r75-clean\Lib\site-packages\scirel\__init__.py`;
sys.path carries no repository-root or `/src` entry and the repo
`tests` package is not importable (a first attempt failed with exit
code 1 on an over-broad sys.path assertion that banned the venv root
path too; the corrected check is entry-wise and the failure record is
retained). Representative calls, all asserting saved-oracle values:
`merge_neutral_population_density` (signed componentwise addition +
source ownership), `merge_neutral_population_cells` (cell shape/count),
`merge_neutral_reservoirs` (both_nonfull append with the
source-prefix slot rewrite and the res2=res1 broadcast), and the
composition task graph `merge_neutral_population_state`
(source_empty branch, graph_order diagnostics, non-mapping
reservoir-state fail-closed). **Exit code 0**
(`R79-SOURCE-FREE-USAGE-PASSED`).

### Reuse basis for the other gates

No code, exact-document, wheel or catalog byte changed for v2: all 166
exact documents re-hashed against the frozen v1 manifest (zero
mismatches), the dev56 wheel re-hashed (unchanged), and the catalog
root digest re-read (unchanged), measured by
`build/r79v2-byte-identity.ps1` after the v1 freeze. The measured
gates 1-7 in the shell record above therefore remain the receipts for
r79-v2; no test population or runtime changed and the full scientific
suite is not re-run.

### Boundary

No qualified L1 consumption, no expert approval, no trusted promotion,
no public release are claimed. r79-v1 remains frozen and preserved;
r79-v2 is the current pending_unapproved successor and differs from
r79-v1 in the test-evidence text only (the dossier and every exact
document are unchanged bytes).
