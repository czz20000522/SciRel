# r67 test evidence — KN1DPy collision-matrix assembly family

Base r66 `6240995` (128 assets, dev40, frozen snapshot
`build/verification/review-2026-09-27-r66-alpha-contraction-v3`) -> r67
`0.1.0.dev41` (130 assets). Two new operators in `scirel.kinetic`:
`atomic-collision-matrix-assembly` and `molecular-collision-matrix-assembly`,
closing the r66 contraction's declared upstream edge. The cross-section fits
are reused from the integrated `scirel.collisions` leaves instead of a second
embedded copy (see the reuse/divergence record in the r67 dossier and
candidate review.md). The r66 snapshots are untouched.

## Shell record

All counted gates, builds and the freeze ran under pwsh 7+ with
`PYTHONDONTWRITEBYTECODE=1` and explicit `PYTHONPATH` /
`SCIREL_KN1DPY_REVIEW_ROOT` set in-process. The replay arm's
`SCIREL_KN1DPY_REVIEW_ROOT` points at
`SciRel/build/verification/neutral-harness-baseline-v3/inputs/l1/KN1DPy`
(the `KN1DPy-631d0bf1` bundle; strict D1 withdrawn, provisional). Saved-tree
imports read-only; zero writes. The qualified L1 delivery root
(`D:/Users/26569/Desktop/归档_项目/codefusion/最小闭环压测环境`) was re-checked
empty (0 items) at batch start.

## Test delta (collect-verified)

- `test_collision_matrix_assembly.py`: 14 direct tests — independent
  broadcasting-geometry oracle per arm (source's own embedded formulas,
  rtol=1e-12, canonical + holdout carriers), predecessor-state capture and
  `Vth2` shape/value, `SIG_CX` nonnegativity, bounded elastic negative cells
  with deterministic canonical counts (atomic 8/4/4; molecular 4/4/8 — see
  the registered conflict with the saved molecular operator.md's 2/2/4 note),
  the molecular `SIG_CX` energy-factor discriminator, fail-closed carrier
  contracts including the scalar `Tnorm`/`mu` tightening and empty-array
  rejection, input read-only behavior, and composition into the r66
  contraction ports.
- `test_collision_matrix_assembly_l1.py`: 3 environment-gated replay tests —
  SHA-256-pinned saved-arm parity (bitwise for elastic families and
  predecessor state; rtol=1e-14 for the CX families) on canonical + holdout,
  and rejection-behavior agreement.
- Total 17 new tests; full-tree delta reconciles exactly (1445 -> 1462 source,
  1290/189 -> 1313/192 installed).

## Sigma reuse probe (pre-review evidence, recorded)

Method: direct bitwise/relative comparison of the saved packages' embedded
fits against the integrated public `scirel.collisions` callables. Grid:
200,011 points — `linspace(1e-3, 1.2e5, 200001)` plus the explicit points
`{0, 0.001, 0.03, 0.1, 1, 9.999999999, 10, 10.000000001, 1.01e4, 2.01e4,
1e5}`. Observed: five elastic families bitwise identical (after normalizing
the public leaves' two declared output-shape conventions); CX families differ
with max relative deviation 2.22e-15 (atomic) / 2.21e-15 (molecular).
Root-cause probe: `np.exp(poly)` vs `np.e ** poly` on a 1,000,001-point
log-grid — 2.06e-15 max relative, up to 17 double-precision ulp by
`np.spacing`, differing on every sampled cell. These are sampled
measurements over the declared fit domains, not bounds over the continuous
domain; the replay tolerance for the CX families is rtol=1e-14.

## Gates (final bytes)

- Source-mode full gate (replay active):
  **1462 passed, 43 skipped, 0 failed** (r66-v3 full tree: 1445, +17).
- Without the replay root the assembly replay tests skip — an expected state,
  not a failure.
- Document validation, source state: **130/130**, `runtime_origin: source`,
  `examples_executed: true`.
- Clean venv `build/venv-r67-clean` (own numpy 2.5.3 / scipy 1.18.1 /
  pytest 9.1.1, `include-system-site-packages = false`), wheel installed
  `--no-index --no-deps`: isolated `-I` import resolves inside the venv
  prefix; assembly import and run verified installed.
- Document validation from the clean venv with `--installed-runtime`:
  **130/130**, `runtime_origin: installed`, `examples_executed: true`.
- Installed full tree: **1313 passed, 192 skipped, 0 failed**
  (`SCIREL_INSTALLED_RUNTIME=1`, venv python `-I -B -m pytest -q -o
  pythonpath= -p no:cacheprovider tests/`; r66: 1290 passed, 189 skipped).
- Catalog `build/catalog/r67`: `complete: 130/130`, root digest
  `sha256:6c0f4ea2ea227ff70a60756be401114f730527f0bcc0e0cc956c0b444d89f3e5`.
  Prior catalog builds (`r66-v2`, `r66`, `r66-stale-placeholder-docs`) are
  preserved and unreferenced by this freeze.
- Internal wheel `scirel-0.1.0.dev41-py3-none-any.whl`, SHA-256
  `494e67e2df060a3c5071b23cb298b6a915a3e4975ecd6943ccc8c1cd0e13f2e6`.
- Candidate review-material index: batch r67 added (7 entries covering
  review.md and 6 proposal files under
  `review_candidates/2026-09-27-collision-matrix-assembly/`), every entry
  resolves and matches its recorded SHA-256 (script-verified).
