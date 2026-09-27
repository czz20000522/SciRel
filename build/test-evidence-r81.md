# r81 test evidence — FIDASIM NPA store_npa energy-bin leaf + multi-coil clarification

Base r80-v3 `2999ac5` (repair/tree commit `935c17f`, 168 assets,
`0.1.0.dev57`, frozen snapshot
`build/verification/review-2026-09-27-r80-fida-spectral-family-v3`)
-> r81 `0.1.0.dev58` (169 assets), science HEAD `f07af46`. One new
fusion operator from the saved FIDASIM bundle:
`scirel.fusion.npa-energy-bin-increment` (the stateless `store_npa`
scalar slice, `NPA能量通道通量增量`, src/fidasim.f90:10600-10724).
Same batch: the `scirel.field.multi-coil-vacuum-field` exact document
gains both conditional `current_a` readings plus one discriminating
numeric test (default behavior, algorithm, and frozen r80 bytes
unchanged), and `doppler-stark-zeeman-wavelengths` gains the
nonpositive-wavelength fail-closed repair from the r80-v3 review
(module, tests, exact document, proposal copies).

## Evidence ceiling (recorded before the gates)

The saved bundle's ledger claims `source_behavior_verified` for this
leaf via an external native microprobe
(`../FIDASIM_evidence/source_probe/npa_store_flux_audit/`, three real
`store_npa` replays, `max_abs = 0`). That directory is not adjacent to
the frozen saved input and its receipt could not be re-verified; the
package's own test header marks itself `source_unavailable`. The
review ceiling is therefore the package-level equation/boundary oracle
plus the historical ledger claim — not re-verified Fortran runtime
parity. The frozen saved input's live bytes were re-verified this
batch: 1253 files, per-file SHA-256 and sizes, ordinal recipe scope
digest `sha256:cd0010b8...` reproduced (`source_byte_verified: true`
is a snapshot property, not a qualified-L1 claim).

## Pre-freeze review corrections (all fixed before any gate ran)

1. The saved arm's `isinstance(value, int)` semantics were corrected in
   module messages, exact document, review.md and dossier: it accepts
   `True` but rejects whole-number floats and `np.integer`; float
   rejection is continuity, `np.integer` acceptance + bool rejection
   are the hardening.
2. The r81 review scope now explicitly lists the doppler
   nonpositive-wavelength fail-closed repair as substantive science
   delta (not hidden in the mechanical version bump), alongside the
   multi-coil clarification as the two non-mechanical document changes.
3. A second review finding: boolean entries in `velocity_cm_s` /
   `energy_centers_kev` are now detected *before* numpy coercion (mixed
   containers such as `[True, 2.0]` become float64 at `asarray` time);
   three new discriminating inputs all fail closed. The duplicated
   `astype` block was also removed, and the module docstring's
   increment constraint was corrected to nonnegative finite
   (`flux = 0` legitimately returns 0).

## Gates (final bytes at science HEAD `f07af46`, real captured exit codes)

- Gate 1, source full tree, replay root active
  (`build/r81-gate-1-source-fullsuite.ps1`, log
  `build/r81-pwsh-source-fullsuite.log`, junit
  `build/r81-source-fullsuite-junit.xml`): **1701 passed, 43 skipped,
  0 failed**, exit code 0, 254.60 s (r80-v3: 1685/43; +14 NPA family
  tests, +1 multi-coil weights test, +2 doppler nonpositive tests —
  net +16; junit confirms 1744 tests, 0 errors, 43 skipped).
- Gate 2, document validation, source state (receipt
  `build/r81-source-doc-validation.json`): **169/169**,
  `runtime_origin: source`, `examples_executed: true`, exit code 0.
- Gate 3, internal wheel build: `scirel-0.1.0.dev58-py3-none-any.whl`,
  SHA-256
  `60ce811067e2c808b7ed0176bdb4572bf8bea322badc40b7eca3e8f42bc7090a`
  (built into `build/wheel-r81`).
- Gate 4, clean venv install (`build/venv-r75-clean`,
  `--no-index --no-deps --force-reinstall`), exit code 0.
- Gate 5, installed document validation (receipt
  `build/r81-installed-doc-validation.json`): **169/169**,
  `runtime_origin: installed`, `examples_executed: true`, exit code 0.
- Gate 6, installed full tree: **1700 passed, 44 skipped, 0 failed**,
  exit code 0, 268.70 s; junit confirms 1744 tests, 0 errors, 44
  skipped; `scirel.__file__` inside the venv site-packages.
- Gate 7, catalog `build/catalog/r81`: `complete`, declared_total 169,
  root digest
  `sha256:61bb7e828098e244a0285bfb772f59a9f43e3d3576caa907d9ca769c09e5ae4d`.
- Gate 10, source-free public API usage (log
  `build/r81-pwsh-sourcefree-usage.log`): the clean venv interpreter
  ran `-I -B r81_sourcefree_usage.py` from the isolated directory
  `C:\Users\26569\.claude\jobs\d48db198\tmp\scirel-r81-sourcefree`
  with `PYTHONPATH` unset and `PYTHONDONTWRITEBYTECODE=1`; the script
  (SHA-256
  `6fb75742aee8953588c8ca0f7f2686e35a573305cd25c6f6fc247049832ad10c`,
  preserved as `build/r81-sourcefree-usage-script.py`) exercises the
  doppler and binning leaves of the previous family against the
  installed dev58 wheel. **Exit code 0**
  (`R80V2-SOURCE-FREE-USAGE-PASSED` marker printed by the script;
  gate wrapper recorded `R81-GATE-10-PASSED`).

## Test delta (collect-verified)

- 14 new tests in `tests/operator_contracts/test_npa_store_family.py`
  (saved probes, quirk pins, hardening regressions, N8 accumulation
  witness), 1 new test in
  `tests/graph_contracts/multi_coil_vacuum_field/`
  (weights discrimination), 2 new tests in
  `tests/operator_contracts/test_fida_spectral_family.py`
  (nonpositive-wavelength fail-closed; plus the r80-v2 repairs).
- Count-sync edits: `tests/test_asset_documentation.py` (169/170),
  `tests/test_affected_test_selection.py` (169),
  `tests/test_thin_mcp_adapter.py` (declared_total=169).
- Source full tree 1685 (r80-v3) + 16 = 1701, matching the measured
  receipt.

## Boundary and handoff

No qualified L1 consumption (delivery root re-checked empty, 0 items),
no external physical correctness claim, no expert approval, no trusted
promotion, no public release are claimed. Deferred pool unchanged:
`fida_weights_los` phase producer, NPA stage-B weight producer, MPI
weight reductions, real-HDF5 table drivers, MC marker production,
parallel reservoir merge graphs, neutral-bank lifecycle. Per the
owner-rotation handoff, this file records the last gates of this
session; the freeze snapshot follows at the evidence commit's HEAD.
