# r69 test evidence — GSEQ filament-coil Green family + neutral transport domain draft

Base r68 `ad0331e` (132 assets, dev42, frozen snapshot
`build/verification/review-2026-09-27-r68-omega-aggregation-v1`) -> r69
`0.1.0.dev43` (135 assets). Three new operators in `scirel.field`:
`coil-green-geometry`, `complete-elliptic-integrals-approx` and
`filament-coil-green-field` (the last a declared relation VARIANT of
`scirel.field.circular-filament-green`, not a new Green capability). A new
domain draft `docs/domains/neutral-particle-transport.md` indexes the KN1DPy
neutral-transport chain using exact documents as the only contract references.
The r68 snapshots are untouched.

## Source-first intake from a second saved project

The GSEQ bundle (`build/verification/neutral-harness-baseline-v3/inputs/l1/gseq`,
137 operator packages) is the first non-KN1DPy source integrated in this
chain. Saved implementations pinned by SHA-256 (replay):

- 轴对称线圈几何模数 `coil_green_geometry.py` —
  (pinned in `_PINNED` of the replay test)
- 完全椭圆积分近似 / 环形线圈Green场响应 — likewise pinned.

## Deduplication record (review.md §Material differences, dossier)

The response operator's relation is the SAME circular-filament Green physics
as the baseline `scirel.field.circular-filament-green`; it is recorded as a
declared variant, not a new capability. Variant boundary: caller-supplied
per-coil K/E (typically the GSEQ apx==1 approximation) vs internally
evaluated scipy special functions; one scalar observation target with the
source's `r0 + 1e-8` axis regularization applied once upstream vs arbitrary
point arrays; combined `2e-7*N*I` factor; fail-closed singular rejection vs
the baseline's zeroing of non-finite terms. Numerical cross-checks: with
identical scipy K/E the two implementations agree to rtol 1e-12 on probed
geometries; the source polynomial-log K/E approximation agrees with scipy to
at most 1e-8 (K) / 2e-8 (E) relative on a 200,001-point sweep of [1e-6,
0.999999] — sampled evidence, not a continuous bound, and it degrades the
responses by up to ~1e-5 relative on the probed set through closed-form
amplification.

## Registered fail-closed hardenings (all diverging from silent saved behavior)

1. Singular geometry (observation point on a filament ring, `separation == 0`
   ⇔ `modulus == 1`) is rejected at the response operator. Recorded
   pre-review failure chain reproduced by a combination regression:
   `compute_axisymmetric_coil_modulus(0.99999999, 0, [1.0], [0])` →
   regularized R == 1.0, m == [1] → elliptic operator returns the finite
   sentinel K = [1e300], E = [1] (source contract, kept) → the source
   response returned (2e293, NaN, NaN) silently; this port raises.
2. Raw observation radii in (-1e-8, 0) are rejected by the geometry operator
   (the axis offset alone would silently re-label them positive; the saved
   implementation accepts them).
3. Overflow hardening: finite but extreme magnitudes (`r0 = rl = 1e308`
   squaring to Inf; `current = turns = 1e308` overflowing the response
   factor) raise ValueError at both the geometry and response operators
   instead of handing NaN/Inf downstream.
4. The elliptic approximation operator keeps the source's whole-array `m ==
   1` sentinel (`K = 1e300, E = 1`) and mixed-array Inf/NaN path verbatim;
   the response operator refuses the geometry that triggers them.

All four are registered in the exact documents (boundary/constraints,
failure semantics, known limitations).

## Test delta

- `tests/operator_contracts/test_filament_coil_green_gseq.py`: 12 direct
  tests — geometry closed forms (exact offset, rtol=1e-15), the
  polynomial-log K/E evaluation (exact) with sentinel and mixed singular
  paths, response closed forms (exact float equality), linearity, mirrored
  midplane B_r cancellation, scipy-vs-GSEQ cross-implementation agreement
  (rtol 1e-12 at equal K/E; ≤1e-5 relative with the source approximation,
  sampled), the singular coincident-chain regression (per the recorded
  pre-review failure), negative-raw-radius rejection, and overflow
  rejections. Per-call seeded fixtures.
- No replay test file is added for this batch: the gseq saved packages ship
  package-level oracles rather than a pinned source-runtime replay target,
  and the cross-implementation comparison against the baseline scipy asset
  provides the second arm. (The saved implementations are nonetheless
  SHA-pinned in the direct test module docstring for drift detection.)
- 12 new tests; full-tree delta reconciles exactly (1486 -> 1498 source with
  replay; 1332/197 -> 1344/197 installed).

## Gates (final bytes, returncode-checked)

- Source-mode full gate (replay active): **1498 passed, 43 skipped, 0
  failed**, pytest returncode 0 (r68 full tree: 1486, +12).
- Document validation, source state: **135/135**, `runtime_origin: source`,
  `examples_executed: true`.
- Clean venv `build/venv-r69-clean` (own numpy 2.5.3 / scipy 1.18.1 /
  pytest 9.1.1), wheel installed `--no-index --no-deps`.
- Installed document validation: **135/135**, `runtime_origin: installed`,
  `examples_executed: true`, subprocess returncode 0.
- Installed full tree: **1344 passed, 197 skipped, 0 failed**, pytest
  returncode 0 (r68: 1332 passed, 197 skipped). Both installed subprocess
  return codes are propagated by the gate script (`installed_gates_r69.py`
  exits non-zero on any non-zero child returncode); the earlier draft of the
  gate script that did not propagate the pytest returncode was replaced and
  re-run before freezing, per pre-review correction.
- Catalog `build/catalog/r69`: `complete: 135/135`, root digest
  `sha256:fb1cf5257689d19ce67f4b10289d7e3298092f133539d202c555da3b00b4b116`.
  Prior catalog builds (`r68`, `r67`, `r66-v2`, `r66`,
  `r66-stale-placeholder-docs`) are preserved and unreferenced by this
  freeze.
- Internal wheel `scirel-0.1.0.dev43-py3-none-any.whl`, SHA-256
  `4c5c21316ad7a9aa3adca6b28e72522c474bd32841717d9a453c3ba7483ffb0c`.
- Domain draft `docs/domains/neutral-particle-transport.md` added and linked
  from `docs/domains/README.md`; it references exact documents only, states
  the provenance ceiling (KN1DPy provisional, empty qualified L1 root), and
  leaves the registered expert questions open.
- Candidate review-material index: batch r69 added (7 entries).
