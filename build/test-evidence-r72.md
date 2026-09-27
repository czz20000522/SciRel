# r72 test evidence — FIDASIM cross-node leaf family

Base r71 `f1f07e6` (142 assets, dev45, frozen snapshot
`build/verification/review-2026-09-27-r71-nbi-birth-leaves-v2`) -> r72
`0.1.0.dev46` (147 assets). Five new operators in `scirel.fusion` spanning
three framework nodes of the saved program_framework_map: N2
neutral_beam_source_sampling (`nbi-injected-neutrals-normalization`,
`nbi-cell-directed-ray`), N7 fast_ion_fida_response
(`mc-marker-weight-allocation`), N9 neutron_response
(`dd-rate-table-interpolation`, `fast-ion-relative-energy`). Cross-node
independent leaves; no composed source pipeline is asserted. The r71
snapshots are untouched.

## Shell record

All counted gates, builds and the freeze ran under pwsh 7+ with
`PYTHONDONTWRITEBYTECODE=1` and explicit `PYTHONPATH` /
`SCIREL_KN1DPY_REVIEW_ROOT` set in-process. The qualified L1 delivery root
(`D:/Users/26569/Desktop/归档_项目/codefusion/最小闭环压测环境`) was re-checked
empty (0 items) at batch start.

## Source mapping (content digests, reference records only)

The FIDASIM bundle lives in the sibling main SciRel checkout (read-only
imports, zero writes; not inside this intake worktree). Per-file SHA-256 of
the saved implementations, with the asset IDs on adjacent lines:

- `operators/DD反应率表插值/scientific_operator.py` ->
  `scirel.fusion.dd-rate-table-interpolation` -- sha256
  `2a63275b1ecb68f67354409239758de097a4689073b39dceaf07cc2e6fb36648`
- `operators/快离子相对能量/scientific_operator.py` ->
  `scirel.fusion.fast-ion-relative-energy` -- sha256
  `24ff46151da3fb019880738a264816f154e53d2af2db74c70fb158e53be68a08`
- `operators/MC标记按权重分配/scientific_operator.py` ->
  `scirel.fusion.mc-marker-weight-allocation` -- sha256
  `5bdfe6b11c9d39bc0d2c726d6de8b36a1a668fe47e157f86b4404c27c66bbc17`
- `operators/NBI注入粒子数与初始态归一化/scientific_operator.py` ->
  `scirel.fusion.nbi-injected-neutrals-normalization` -- sha256
  `3c4df8c23177edea67b19931679898b27ae84e2c8663f5363667912450489b5a`
- `operators/NBI单元定向射线与概率/scientific_operator.py` ->
  `scirel.fusion.nbi-cell-directed-ray` -- sha256
  `0d3b9526b8fd805d0d0e41843daee00a217f50e6fc1cd3e3d702f6502c3c81ac`

No automated drift detection runs against the saved bytes.

## Test delta (collect-verified)

- `test_cross_node_leaves.py`: 16 direct tests — independent bilinear
  recomputation for the DD rate, beyond-table zero return, min_log_rate
  gate, strict branch-index contract (bool/float rejected), the
  exponentiation overflow witness; the relative-energy closed form
  (zero-at-rest identity) and the max-finite overflow witness; the
  F-order CDF recomputation for marker allocation with count conservation,
  the remainder early-return semantics and the exclusive draw domain; the
  NBI normalization source formula, zero-power identity, sign contracts
  and overflow witnesses; the saved package's own ray probes (centerline
  acceptance, theta_z-uses-focy quirk), the Float32 divisor identity, and
  the finite-output witness. Per-call seeded fixtures.
- 16 new tests; full-tree delta reconciles exactly (1524 -> 1540 source
  with replay; 1370/197 -> 1386/197 installed).

## Gates (final bytes, returncode-checked)

- Source-mode full gate (replay active): **1540 passed, 43 skipped, 0
  failed**, pytest returncode 0 (r71-v2 full tree: 1524, +16).
- Document validation, source state: **147/147**, `runtime_origin: source`,
  `examples_executed: true`.
- Clean venv `build/venv-r72-clean` (own numpy 2.5.3 / scipy 1.18.1 /
  pytest 9.1.1), wheel installed `--no-index --no-deps`.
- Installed document validation: **147/147**, `runtime_origin: installed`,
  `examples_executed: true`, subprocess returncode 0.
- Installed full tree (dev47 wheel in clean venv): **1386 passed,
  197 skipped, 0 failed**, pytest returncode 0 (r71: 1370 passed,
  197 skipped; the dev46 installed receipts were superseded by the dev47
  rebuild).
- Catalog `build/catalog/r72`: `complete: 147/147`, root digest
  `sha256:bf0e24fce337d56dbc8974aebb56ce110baff60961ab0de34ed101d97b33cfd6`
  (rebuilt at dev47 alongside the wheel).
  Prior catalog builds are preserved and unreferenced by this freeze.
- Internal wheel `scirel-0.1.0.dev47-py3-none-any.whl`, SHA-256
  `11f6f6149208b52ea0774686ccc6b9fb9b315d9f700333f23113ae8059a780ca`
  (rebuilt at dev47 after the density-misnomer key rename and prose cleanup;
  the earlier dev46 wheel `85742b79...` was superseded).
- Candidate review-material index: batch r72 added (12 entries covering
  review.md, 6 proposal modules/tests and 5 proposal exact documents),
  every entry resolves and matches its recorded SHA-256
  (script-verified).

## Correction history within this batch (successor commits after initial r72 development commit)

- `017ca39`: fixed the three independently reproduced blockers (marker
  allocation contract, ray py*pz overflow, DD rate OverflowError→ValueError
  contract normalization); renamed `initial_state_density_cm_inv3` to
  `initial_state_rate_per_volume_cm_inv3_s_inv`; added regression tests.
- `5a61c1d`: systematically cleaned the density misnomer across both exact
  documents, source modules, review.md and test comments; bumped to dev47.
- This file (test evidence) updated to bind the dev47 wheel/catalog.
