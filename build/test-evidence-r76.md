# r76 test evidence — FIDASIM DCX/HALO iteration-feedback family

Base r75-v2 `2b922fb` (151 assets, `0.1.0.dev50`, frozen snapshot
`build/verification/review-2026-09-27-r75-nbi-source-geometry-v2`) -> r76
`0.1.0.dev51` (153 assets), final science HEAD `60804c4` (commits
`eda95d7` family, `60804c4` review fixes). Two new fusion assets from the
saved FIDASIM bundle (framework node N3 `neutral_population_transport`):
`scirel.fusion.halo-iteration-feedback` (one halo density-feedback round:
growth guard, population merge, seed_dcx fraction, Fortran-truncated
marker count) and the bounded explicit feedback-sequence task graph
`scirel.fusion.halo-iteration-feedback-sequence` over a caller-provided
current-density sequence, composing the operator.

## Shell record

All counted gates, builds and validations ran under pwsh 7+ in
`D:\software\PyCharm 2025.3.3\workspace\SciRel-intake-20260925` with
`PYTHONDONTWRITEBYTECODE=1`, `python -B`, explicit `PYTHONPATH=src` for
source-mode test runs, and `SCIREL_KN1DPY_REVIEW_ROOT` pointed at the
saved KN1DPy bundle in the sibling main SciRel checkout (used only by the
pre-existing replay tests). The qualified L1 delivery root
(`D:/Users/26569/Desktop/归档_项目/codefusion/最小闭环压测环境`) was
re-checked empty (0 items) at batch start. The FIDASIM saved bundle was
read (zero writes) at
`D:\software\PyCharm 2025.3.3\workspace\SciRel\build\verification\neutral-harness-baseline-v3\inputs\l1\FIDASIM`
as provisional evidence only.

Saved-implementation content digests recorded per asset in the exact
documents' provenance sections:

- `DCXHalo迭代反馈/scientific_operator.py` sha256 `627743a9…686753f`; its operator.md `2a163a60…3d32d1`.
- `DCXHalo迭代反馈序列图/graph.py` sha256 `a48424e0…c31f33c`; task_graph.yaml `385833eb…cd9acab`; task_graph.md `1fbad7ff…721292a69`.
- `DCXHalo迭代反馈图/graph.py` sha256 `59a0d902…8284137a` (single-step delegation layer; deliberately folded into the operator contract, decision recorded in the sequence graph document).

## Pre-freeze review findings and resolutions (recorded, not hidden)

Three independent pre-freeze review findings were resolved regression-first
at commit `60804c4` (each reproduced red before the fix); no Codex edits
were made (single-writer flow):

1. **budget*seed product overflow**: `f(1.0, 1e308, 1e308, 0.0, 40)`
   reached a finite seed but `int(budget * seed)` raised a bare
   OverflowError at inf despite the documented finite-output hardening.
   The product is now computed inside the registered hardening: a
   non-representable product (OverflowError) or a non-finite product
   raises ValueError. Documented numerical bound: the marker product is
   computed in double precision (the source's counting arithmetic) and
   must stay representable.
2. **Bool budget acceptance in the sequence**: `requested=[True]` passed
   the float64 roundtrip as 1.0 although the scalar budget rejects bools.
   The sequence's integer-vector parser now rejects bools elementwise.
3. **Spurious drift for exact integers beyond 2^53**: the parser converted
   through float64, so `9007199254740993` rounded and mismatched its own
   base budget. The parser now preserves int entries exactly at any
   magnitude, accepts float entries only when finite and exactly integral,
   and the exact document states the bound (a 2^53+-magnitude integer
   given as a float cannot match its exact base and drifts fail-closed).

## Test delta (collect-verified)

- 13 new tests in
  `tests/operator_contracts/test_halo_iteration_feedback.py` (11 covering
  the one-round operator and the sequence graph, plus the
  budget-product-overflow and big-integer-preservation regressions).
- Count-sync edits: `tests/test_asset_documentation.py` (153/154),
  `tests/test_affected_test_selection.py` (153),
  `tests/test_thin_mcp_adapter.py` (declared_total=153).
- Source full tree 1574 (r75) + 13 = 1587, matching the measured receipt.

## Gates (final bytes at `60804c4`, returncode-checked)

- Source-mode full tree, replay root active: **1587 passed, 43 skipped,
  0 failed**, pytest returncode 0, 280.18 s (r75: 1574/43; +13 new).
- Document validation, source state: **153/153**, `runtime_origin:
  source`, `examples_executed: true`, returncode 0 (receipt
  `build/r76-source-doc-validation.json`).
- Clean venv `build/venv-r75-clean` (numpy 2.5.3, scipy 1.18.1,
  pytest 9.1.1, setuptools 84.0.0 offline from
  `build/dependency-wheelhouse`; no system site-packages), dev51 wheel
  installed `--no-index --no-deps --force-reinstall`; `-I` import check
  passed (wheel resolves inside the venv, version reads 0.1.0.dev51).
- Installed document validation from the clean venv (`-I`,
  `--installed-runtime`): **153/153**, `runtime_origin: installed`,
  `examples_executed: true`, returncode 0 (receipt
  `build/r76-installed-doc-validation.json`).
- Installed full tree (`-I`, `SCIREL_INSTALLED_RUNTIME=1`,
  `-o pythonpath=`, replay root active): **1586 passed, 44 skipped,
  0 failed**, pytest returncode 0, 269.36 s. As in r75, the replay root
  was active for this installed run, so the KN1DPy replay comparisons
  executed in installed mode and passed (configuration difference versus
  the r74-style receipt, not a test-population change).
- Catalog `build/catalog/r76`: `complete: 153/153`, root digest
  `sha256:9e81738fd810bc1c0a15bc854377b0cc6e1b29278b3e615458d2eee4849f2970`
  (rebuilt at final HEAD after the review-fix commit). Per the r75
  corrections addendum: scratch/development builds may be superseded by
  in-place rebuilds; only frozen round material is preserved.
- Internal wheel `build/wheel-r76/scirel-0.1.0.dev51-py3-none-any.whl`,
  SHA-256
  `bc6bce8b89ddbf720fbd002fabd838cca86f8a7c0ed53f355f4875a3b74b764a`
  (rebuilt at final HEAD; the pre-review wheel `9e064629…` was discarded
  on rebuild).

## Candidate packet

`review_candidates/2026-09-27-halo-iteration-feedback/` (review.md + five
byte-identical proposal copies) was created before the freeze and bound by
SHA-256 in `docs/evaluations/candidate-review-materials-index-2026-09-25.md`
(Batch r76 section), and is snapshotted directly as review materials by the
r76-v1 freeze — closing the gap that r75 needed a post-freeze successor
for.

## Boundary

No qualified L1 consumption, no external physical correctness claim, no
expert approval, no trusted promotion, no public release are claimed.
Deferred from this round: DCX/CX initial state and photon fast-ion
correction (needs the six-level colrad core), the NPA/FIDA
weight-production chain, the multi-cell population merge and MC marker
production. The saved bundle's runtime observation (unbounded-stack
SIGSEGV on the halo/dcx generate path without `ulimit -s unlimited`) is
recorded for expert evaluation and is not a behavior of these assets.
