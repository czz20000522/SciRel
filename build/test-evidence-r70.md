# r70 test evidence — FIDASIM fast-ion kinematics family

Base r69 `33fa7db` (135 assets, dev43, frozen snapshot
`build/verification/review-2026-09-27-r69-gseq-green-v2`) -> r70
`0.1.0.dev44` (137 assets). Two new operators in `scirel.fusion`:
`dd-neutron-emission-anisotropy` and `first-order-larmor-correction`. The
D-D neutron lab-energy relation of the saved FIDASIM package is a registered
REUSE of the integrated `scirel.fusion.dd-neutron-lab-energy` asset (same
physics, same inputs/output, integrated asset carries the documented repair;
the constant angular_weight field is not a capability) — no third public
identity. The r69 snapshots are untouched.

## Shell record

All counted gates, builds and the freeze ran under pwsh 7+ with
`PYTHONDONTWRITEBYTECODE=1` and explicit `PYTHONPATH` /
`SCIREL_KN1DPY_REVIEW_ROOT` set in-process. The qualified L1 delivery root
(`D:/Users/26569/Desktop/归档_项目/codefusion/最小闭环压测环境`) was re-checked
empty (0 items) at batch start.

## Source mapping (content digests, reference records only)

The FIDASIM bundle lives in the sibling main SciRel checkout at
`D:/software/PyCharm 2025.3.3/workspace/SciRel/build/verification/neutral-harness-baseline-v3/inputs/l1/FIDASIM`
(read-only imports, zero writes; not inside this intake worktree). Per-file
SHA-256 of the saved implementations, with the asset IDs on the same line:

- `operators/DD中子运动学各向异性/scientific_operator.py` ->
  `scirel.fusion.dd-neutron-emission-anisotropy` -- sha256
  `f3bb91df84e8a10af9f0725a64f602c1d37a7362ede8b12f994b1a1e6831c16a`
- `operators/一阶Larmor引导中心修正/scientific_operator.py` ->
  `scirel.fusion.first-order-larmor-correction` -- sha256
  `60fb8ad0f2e9cf6ef5cc5f53bb215a1857fd184ff49813f25bc1cf64516fce7b`
- `operators/DD中子运动学能量/scientific_operator.py` -> REUSED as
  `scirel.fusion.dd-neutron-lab-energy` (integrated asset, no new identity)

No automated drift detection runs against the saved bytes; the FIDASIM saved
packages ship package-level oracles rather than a pinned source-runtime
replay target, and the saved forward probe (rtol 1e-14) plus these digests
provide the provenance linkage. An earlier draft of the r69 evidence that
overstated this as test-module pinning was corrected before the r69-v2
freeze; the same discipline is applied here.

## Test delta (collect-verified)

- `test_fast_ion_kinematics.py`: 10 direct tests — the saved package's
  frozen forward anisotropy probe (rtol 1e-14), transverse rotational
  symmetry, positivity over in-domain random fixtures, the general
  upper-table boundary (`0.5*scale*|v1-vrot|^2 < 116.909 keV`) rejection
  including the extreme-ion-velocity overflow path into it, documented
  norm-overflow containment (extreme neutron velocities yield finite
  kappa == 1 through the angle fallback), FLR order-0 identity, order-1
  exact cross-product radius with perpendicularity and position
  displacement plus the historical flr_enabled contract, order-2
  uniform-field scale exactly 1 and the outside-(0,2) rejection, on-axis
  undefinedness, missing-state rejection, and the recorded
  position-subtraction overflow chain (finite 1e308 position with finite
  radius about -1.04e308 raises instead of returning Inf). Per-call seeded
  fixtures; no module-level RNG.
- 10 new tests; full-tree delta reconciles exactly (1498 -> 1508 source with
  replay; 1344/197 -> 1354/197 installed).

## Registered divergences exercised by tests

- Anisotropy: non-finite output gate (registered hardening; on the declared
  domain the angle algebra contains norm overflow, verified by probes).
- FLR: radius and returned-field non-finite gates (registered hardening;
  the saved arm returns Inf silently on the recorded overflow chain).
- Preserved verbatim: the source interpolator's uniform-spacing assumption
  on a non-uniform table, the (0, 2) scale window, on-axis undefinedness,
  flr_order type strictness.

## Gates (final bytes, returncode-checked)

- Source-mode full gate (replay active): **1508 passed, 43 skipped, 0
  failed**, pytest returncode 0 (r69 full tree: 1498, +10).
- Document validation, source state: **137/137**, `runtime_origin: source`,
  `examples_executed: true`.
- Clean venv `build/venv-r70-clean` (own numpy 2.5.3 / scipy 1.18.1 /
  pytest 9.1.1), wheel installed `--no-index --no-deps`.
- Installed document validation: **137/137**, `runtime_origin: installed`,
  `examples_executed: true`, subprocess returncode 0.
- Installed full tree: **1354 passed, 197 skipped, 0 failed**, pytest
  returncode 0 (r69: 1344 passed, 197 skipped). Both installed subprocess
  return codes are propagated by the gate script (`installed_gates_r70.py`
  exits non-zero on any non-zero child returncode).
- Catalog `build/catalog/r70`: `complete: 137/137`, root digest
  `sha256:bce5623814d94469cf103b019db730c5c4f192a971bb415108c2697e7b0451f9`.
  Prior catalog builds (`r69`, `r68`, `r67`, `r66-v2`, `r66`,
  `r66-stale-placeholder-docs`) are preserved and unreferenced by this
  freeze.
- Internal wheel `scirel-0.1.0.dev44-py3-none-any.whl`, SHA-256
  `d72e89f26022018ae04957b5eb6daa1e8aafa3cd5a325df3dd343eb9969403f5`.
- Domain draft `docs/domains/fusion.md` extended with the two relations and
  the explicit reuse disposition.
- Candidate review-material index: batch r70 added (6 entries).
