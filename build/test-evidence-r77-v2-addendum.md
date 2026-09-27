# r77-v2 successor evidence addendum — post-freeze review repairs

r77-v1 (commit `c3a1e4b`, `0.1.0.dev52`, snapshot
`build/verification/review-2026-09-27-r77-dcx-colrad-family-v1`) is
preserved untouched. Post-freeze read-only review found three concrete
contract cases, all reproduced with `python -B` before the repair
(commit `d693aca`, `0.1.0.dev53`, 158 assets):

1. **Ballistic finite-output gap**: `advance_collisional_radiative_states(
   [1e308], [[-1.0]], 2.0, False, 0, 7.0)` returned an Inf integrated
   density (`state*dt` overflow) on the ballistic branch, contradicting
   the documented finite-output contract. The ballistic branch now gates
   its outputs (registered hardening; the saved arm returns Inf
   silently).
2. **Ballistic strict-index gap**: `emitting_state_index=99` was accepted
   on the ballistic branch because the saved arm never validates the
   index there. The strict in-range integer contract is now enforced in
   both branches (registered hardening), matching the frozen document's
   claim.
3. **Whole-number float species index**: `prepare_dcx_colrad_initial_state(
   ..., selected_thermal_species_index=0.0, ...)` was accepted because
   `int(0.0) == 0.0` passed the old equality check. The check is now a
   strict integer type test (registered hardening).

The zero-eigenvalue adjudication documentation is untouched. dev52 ->
dev53; the version bump and the two exact-document constraint updates
(emitting index in both branches; whole-number floats rejected) are part
of the same commit. 18 family tests (one net new test), 158 assets.

## Gates (final bytes at `d693aca`, returncode-checked)

- Source-mode full tree, replay root active: **1605 passed, 43 skipped,
  0 failed**, returncode 0, 280.75 s (r77-v1: 1604/43; +1 net new test).
- Document validation, source state: **158/158**, `runtime_origin:
  source`, `examples_executed: true` (receipt
  `build/r77v2-source-doc-validation.json`).
- Clean venv installed document validation (`-I`,
  `--installed-runtime`): **158/158**, `runtime_origin: installed`,
  `examples_executed: true` (receipt
  `build/r77v2-installed-doc-validation.json`).
- Installed full tree (`-I`, `SCIREL_INSTALLED_RUNTIME=1`,
  `-o pythonpath=`, replay root active): **1604 passed, 44 skipped,
  0 failed**, returncode 0, 263.53 s.
- Catalog `build/catalog/r77` rebuilt: `complete: 158/158`, root digest
  `sha256:2e16fa4fb6e56d43f1e1a1bd777a725905f6961e4f6c555b9fff49c8cae7eb31`.
- Internal wheel
  `build/wheel-r77/scirel-0.1.0.dev53-py3-none-any.whl`, SHA-256
  `cdfeb22843f41c7876fe25e0a5337df0609239f8d84ccf6cd465842aadb04fc7`.
- Candidate packet: five corrected proposal copies re-bound by SHA-256 in
  the materials index (r77-v2 corrected bytes; r77-v1 preserved).

## Boundary

No qualified L1 consumption, no expert approval, no trusted promotion, no
public release are claimed. r77-v1 remains frozen and preserved; r77-v2
is the current pending_unapproved successor.
