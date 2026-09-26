# r68 test evidence — KN1DPy Omega aggregation family

Base r67 `3554469` (130 assets, dev41, frozen snapshot
`build/verification/review-2026-09-27-r67-collision-matrix-assembly-v1`) -> r68
`0.1.0.dev42` (132 assets). Two new operators in `scirel.kinetic`:
`atomic-omega-aggregation` and `molecular-omega-aggregation`, closing the
Omega-aggregation edge declared missing by the baseline's
`elastic-frequency-channels` / `elastic-regeneration-aggregation` consumers and
consuming the r66 contraction and r67 assembly outputs. The r67 snapshots are
untouched.

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

- `test_omega_aggregation.py`: 19 direct tests — independent closed-form
  reduction oracles for all six outputs per arm (saved packages' 1e-12
  relative / 1e-9 absolute budgets) over both Wperp branch fixtures, the
  branch-selector asymmetry discriminator (atomic `<= 0` vs molecular
  `< 0` at zero accumulator), the source-exact inside/outside-the-sum
  division ordering (molecular H2-H vs H2-P), the Fortran-order vs C-order
  SIG carrier discriminator, zero clamps, the exact `Omega_EL` channel sum,
  channel-switch gating, input immutability, the registered scalar
  `Vth`/tolerance hardenings (zero/negative/NaN/array `Vth`; NaN/array
  tolerances), the non-finite output gate (extreme-`Vth` overflow probe), and
  the shape fail-closed boundaries. Fixture random sources are freshly seeded
  per call (`_RNG_SEED` constants) so single affected-test runs see
  byte-identical carriers to the whole-file run — verified by running one
  parametrized case alone, a `-k` selection, and the whole files in both
  orders.
- `test_omega_aggregation_l1.py`: 5 environment-gated replay tests —
  SHA-256-pinned saved-arm parity, all six outputs bit for bit per arm on
  both branch-path fixtures (weight totals 0.5 / -0.5), plus rejection
  agreement restricted to boundaries where the saved arm itself raises
  (non-square SIG, density length mismatch).
- Total 24 new tests; full-tree delta reconciles exactly (1462 -> 1486
  source with replay; 1313/192 -> 1332/197 installed).

## Registered divergences exercised by tests

- Density gating: non-positive `nH`/`nH2` with any elastic channel enabled
  raises where the saved arm silently skips to zeros (documented hardening;
  zero density with all channels disabled remains admissible in both).
- Scalar gates: `Vth`/`DeltaVx_tol`/`Wpp_tol` must be finite positive scalars;
  the saved arm validates none and returns NaN/Inf silently on those paths.
- Non-finite output gate: a finite but extreme `Vth` (1e308) overflows the
  bulk-velocity product; the port raises `ValueError` where the saved arm
  returns Inf. The legitimate-input `sign(0)=0` degeneracy (symmetric drift
  difference -> zero floored denominator -> NaN) is likewise rejected and is
  registered in both exact documents' known limitations; the exact documents'
  examples use nonzero flow targets to stay on the defined domain.

## Gates (final bytes)

- Source-mode full gate (replay active):
  **1486 passed, 43 skipped, 0 failed** (r67 full tree: 1462, +24).
- Without the replay root the Omega replay tests skip — an expected state,
  not a failure.
- Document validation, source state: **132/132**, `runtime_origin: source`,
  `examples_executed: true`.
- Clean venv `build/venv-r68-clean` (own numpy 2.5.3 / scipy 1.18.1 /
  pytest 9.1.1, `include-system-site-packages = false`), wheel installed
  `--no-index --no-deps`.
- Document validation from the clean venv with `--installed-runtime`:
  **132/132**, `runtime_origin: installed`, `examples_executed: true`.
- Installed full tree: **1332 passed, 197 skipped, 0 failed**
  (`SCIREL_INSTALLED_RUNTIME=1`, venv python `-I -B -m pytest -q -o
  pythonpath= -p no:cacheprovider tests/`; r67: 1313 passed, 192 skipped).
- Catalog `build/catalog/r68`: `complete: 132/132`, root digest
  `sha256:d622280dce145ae53d1e10eac748a9e6697779db038ee1dc6c06be66408037f9`.
  Prior catalog builds (`r67`, `r66-v2`, `r66`,
  `r66-stale-placeholder-docs`) are preserved and unreferenced by this
  freeze.
- Internal wheel `scirel-0.1.0.dev42-py3-none-any.whl`, SHA-256
  `28271440e006d9ee6f460fdd3153824cc42338634bdca7b22a082d309ad50a55`.
- Candidate review-material index: batch r68 added (7 entries covering
  review.md and 6 proposal files under
  `review_candidates/2026-09-27-omega-aggregation/`).
