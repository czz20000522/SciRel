# r71 test evidence — FIDASIM NBI birth/geometry leaf family

Base r70 `644b223` (137 assets, dev44, frozen snapshot
`build/verification/review-2026-09-27-r70-fast-ion-kinematics-v3`) -> r71
`0.1.0.dev45` (142 assets). Five new operators in `scirel.fusion`, spanning
three framework nodes of the saved program_framework_map: N2
neutral_beam_source_sampling (`nbi-energy-component-velocity`,
`nbi-component-initial-state`, `beam-grid-cell-sampling`), N3
neutral_population_transport (`thermal-halo-velocity-sampling`), and N7
fast_ion_fida_response (`pitch-gyro-velocity-direction`, whose operator.md
describes a fast-ion diagnostic magnetic frame, not an NBI birth relation).
These are cross-node independent leaves, not a composed source pipeline;
the framework map emits no TaskGraph composing them (e.g. the N7 frame is
the local magnetic frame, not an NBI birth ray), so no cross-node
composition test is included and that composition evidence gap stays
declared. The r70 snapshots are untouched.

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
SHA-256 of the saved implementations, with the asset IDs on adjacent lines:

- `operators/NBI能量分量速度缩放/scientific_operator.py` ->
  `scirel.fusion.nbi-energy-component-velocity` -- sha256
  `234599ca49e06d5fb908f885569c39d70a5245f543008076e119cb20514598a0`
- `operators/NBI能量分量六能级初态物化/scientific_operator.py` ->
  `scirel.fusion.nbi-component-initial-state` -- sha256
  `3558382003ddeefb00c91baaf90dc384948aacfd85890d4565f3c4226a89bd1b`
- `operators/热MaxwellianHalo速度采样/scientific_operator.py` ->
  `scirel.fusion.thermal-halo-velocity-sampling` -- sha256
  `ab8744af352887f780943ed1d0745f8c9351d4c682c6c85e131af202f17c3d8e`
- `operators/主动束网格均匀采样/scientific_operator.py` ->
  `scirel.fusion.beam-grid-cell-sampling` -- sha256
  `1d590eecca6b546dcd7be9e1f04f72ad6525d4283c26c022d8b2c1343bc13729`
- `operators/俯仰陀螺到速度方向/scientific_operator.py` ->
  `scirel.fusion.pitch-gyro-velocity-direction` -- sha256
  `3e6db088f1f6fded322fcfe8f60480ee9113a015b3725d79fb14ff54b2067718`

No automated drift detection runs against the saved bytes; the FIDASIM
saved packages ship package-level oracles rather than a pinned
source-runtime replay target, and the closed-form recomputation tests plus
these digests provide the provenance linkage.

## Test delta (collect-verified)

- `test_nbi_birth_leaves.py`: 9 direct tests — exact closed-form
  recomputation for all five leaves (Float32 divisor quirk by exact array
  equality, full/half/third length ratios, level-1-only population, source
  rate/density formula, thermal-speed formula, zero-mean affine map, pitch
  decomposition in canonical and random QR frames), structural identities
  (unit-norm direction, `dot(direction, b_unit) == pitch` in the canonical
  frame with the tolerance-bounded identity in QR frames, midpoint and
  zero-width collapse, determinism under identical draws, zero-temperature
  collapse), and the registered hardenings: finite positive scalar speed
  (NaN probe), strict integer component (bool/float probes), `nlevels == 6`,
  the weight-factor overflow (three finite max-float fractions -> Inf factor
  in the saved arm returns rate 0 with Inf), the total-rate overflow, the
  per-cell-density overflow (finite rate times tiny volume — the density
  gate catches what the rate gate misses), the halo denominator-underflow
  normalization (saved arm: bare ZeroDivisionError; this port: ValueError;
  domain unchanged), the halo/beam-grid overflow witnesses, and the
  velocity-scaling overflow witness (norm-overflowing finite ray with the
  max finite speed). Per-call seeded fixtures; no module-level RNG.
- 9 new tests. Full-tree delta versus the true r70-v3 baseline
  (commit `644b223`, measured directly in a temporary worktree at that
  commit: **1515 passed, 43 skipped, 0 failed**, returncode 0, replay
  active): +9 collected NBI tests, 1515 -> 1524. The earlier r70 evidence
  numbers (1508 / 1354+197) were taken at the r70-v1 tree (`4969b42`)
  BEFORE the review-scope consumer fix (`acef9c5`), which added exactly
  7 collected scope tests (1 acceptance + 6 parametrized rejections;
  `git show acef9c5`). Relative to the stale r70-v1 numbers (1508/1354)
  the r71 totals appear as +16; the correct like-for-like comparison
  against the r70-v3 baseline is +9 source. The r70-v3 installed baseline
  was not directly re-run, so no derived installed-baseline number is
  claimed; the r71 installed gate (1370 passed / 197 skipped,
  returncode 0) was independently reproduced by the reviewer (the scope
  tests do execute in the installed tree, so they are not source-only).

## Registered divergences exercised by tests

- Weight-factor overflow gate (finite extreme fractions; saved arm: Inf
  factor with rate 0). Density overflow gate (finite rate times tiny
  volume; saved arm: silent Inf).
- Halo denominator-underflow normalization (ZeroDivisionError ->
  ValueError; domain unchanged).
- Finite-output gates on halo velocity/thermal speed, beam-grid position,
  and the velocity scaling (norm-overflowing finite ray witness).
- Pitch identity wording: exact in an exactly-orthonormal frame,
  tolerance-bounded (1e-12) in accepted frames; the earlier draft's
  `sin(gyro)*cos(angle)` formula was a transcription error and is
  corrected to the saved `sqrt(1-pitch^2)` closed form.

## Gates (final bytes, returncode-checked)

- Source-mode full gate (replay active): **1524 passed, 43 skipped, 0
  failed**, pytest returncode 0. Like-for-like delta versus the true
  r70-v3 baseline (measured at commit `644b223` in a temporary worktree:
  1515 passed / 43 skipped, returncode 0): **+9** collected NBI tests.
- Document validation, source state: **142/142**, `runtime_origin: source`,
  `examples_executed: true`.
- Clean venv `build/venv-r71-clean` recreated AFTER the wheel rebuild
  (own numpy 2.5.3 / scipy 1.18.1 / pytest 9.1.1), wheel installed
  `--no-index --no-deps`; the installed
  `scirel/fusion/pitch_gyro_direction.py` is the corrected 1607-byte
  version, matching committed source. The earlier installed receipts
  (1370/197 taken against the superseded `5fc36403...` wheel) were
  discarded, not reused.
- Installed document validation on the rebuilt wheel: **142/142**,
  `runtime_origin: installed`, `examples_executed: true`, subprocess
  returncode 0.
- Installed full tree on the rebuilt wheel: **1370 passed, 197 skipped,
  0 failed**, pytest returncode 0 (coincidentally the same totals as the
  earlier superseded-wheel run; this receipt binds the new wheel by the
  digest above and a fresh venv install).
- Catalog `build/catalog/r71`: `complete: 142/142`, root digest
  `sha256:b7a1e31a7f23b3740b9a095857b4486118d11f6986e1ba8b15f4f193a1aa6144`
  (rebuilt at the corrected HEAD alongside the wheel; the earlier
  `854cc403...` build predated the pitch docstring fix and was replaced
  before freezing).
  Prior catalog builds (`r70`, `r69`, `r68`, `r67`, `r66-v2`, `r66`,
  `r66-stale-placeholder-docs`) are preserved and unreferenced by this
  freeze.
- Internal wheel `scirel-0.1.0.dev45-py3-none-any.whl`, SHA-256
  `40e78fe13c05a1229e1eb54782f6c76becce8563ae8683b36b395a8808e291b8`
  (rebuilt at the corrected HEAD after the pitch docstring formula fix;
  the earlier `5fc36403...` build predated that docstring change and was
  replaced before freezing).
- Candidate review-material index: batch r71 added (12 entries covering
  review.md, 6 proposal modules/tests and 5 proposal exact documents),
  every entry resolves and matches its recorded SHA-256
  (script-verified).
