# r80 test evidence — FIDASIM FIDA spectral-component family

Base r79-v3 `f562536` (science HEAD `e509afb`, 166 assets,
`0.1.0.dev56`, frozen snapshot
`build/verification/review-2026-09-27-r79-neutral-merge-family-v3`)
-> r80 `0.1.0.dev57` (168 assets), science HEAD `fa80272`. Two new
fusion leaves from the saved FIDASIM bundle (the smallest
well-evidenced slice of the deferred NPA/FIDA weight-production chain):
`scirel.fusion.doppler-stark-zeeman-wavelengths`
(`多普勒StarkZeeman谱线波长`, N5 spectral_component_wavelength_producer)
and `scirel.fusion.fida-wavelength-binning` (`FIDA权重谱线分箱`, the
`store_fw_photons_at_chan` terminal binning). The surrounding saved
`FIDA_LOS权重生产图` is not ported (its nodes bind the heavy
CX/colrad/phase producer this batch does not integrate; registered
deviation).

## Shell record

All gates ran under pwsh 7+ in
`D:\software\PyCharm 2025.3.3\workspace\SciRel-intake-20260925` at
science HEAD `fa80272` (freeze-record commit below), with
`PYTHONDONTWRITEBYTECODE=1`, `python -B`, gate scripts parse-checked
with `Parser::ParseFile` before execution (0 errors for all four gate
scripts). `SCIREL_KN1DPY_REVIEW_ROOT` pointed at the saved KN1DPy
bundle in the sibling main SciRel checkout (used only by the
pre-existing replay tests). The qualified L1 delivery root
(`D:/Users/26569/Desktop/归档_项目/codefusion/最小闭环压测环境`) was
re-checked empty (0 items, including hidden entries) at batch start.
The FIDASIM saved bundle was read (zero writes) as provisional
evidence only. Both leaves are package-level equation oracles
(`source_unavailable` / `independent bin oracle; no Fortran runtime
parity claimed`), so no source-runtime replay exists for this family.

Two gate-10 probe failures are retained here as failure records; both
were fixed before the recorded run:

1. The first gate-10 attempt invoked the isolated script with the
   repository root as the working directory (the gate script's
   `Set-Location` came too late for the child process), failing the
   script's own cwd guard. The gate now `Set-Location`s into the
   isolated directory before invoking the venv interpreter.
2. The second attempt asserted exact float equality between the 20-bin
   accumulation sum and the closed-form conservation factor; the two
   differ in the last ULP (`2.38732414637843` vs
   `2.3873241463784303`). The recorded script compares within
   `1e-12`. The direct pytest witness uses `pytest.approx` from the
   start, so no pytest gate was affected.

## Gates (final bytes at the freeze-record commit, real captured exit codes)

- Gate 1, source full tree, replay root active
  (`build/r80-gate-1-source-fullsuite.ps1`, log
  `build/r80-pwsh-source-fullsuite.log`, junit
  `build/r80-source-fullsuite-junit.xml`): **1676 passed, 43 skipped,
  0 failed**, exit code 0, 271.90 s (r79-v3: 1657/43; +19 family
  tests).
- Gate 2, document validation, source state
  (`build/r80-gate-2-5-build-validate.ps1`, receipt
  `build/r80-source-doc-validation.json`): **168/168**,
  `runtime_origin: source`, `examples_executed: true`, exit code 0.
- Gate 3, internal wheel build (`build/r80-wheel-build.log`):
  `scirel-0.1.0.dev57-py3-none-any.whl`, SHA-256
  `e84ec17640c3ad2710ac48a98a0e6feee415dcbe207414973930fa684be84946`.
- Gate 4, clean venv install (`build/r80-wheel-install.log`):
  `build/venv-r75-clean` (numpy 2.5.3, scipy 1.18.1, pytest 9.1.1,
  setuptools offline from `build/dependency-wheelhouse`; no system
  site-packages), dev57 wheel installed
  `--no-index --no-deps --force-reinstall`, exit code 0.
- Gate 5, installed document validation (`-I`, `--installed-runtime`,
  receipt `build/r80-installed-doc-validation.json`): **168/168**,
  `runtime_origin: installed`, `examples_executed: true`, exit code 0.
- Gate 6, installed full tree (`build/r80-gate-6-7-installed-catalog.ps1`,
  log `build/r80-pwsh-installed-fullsuite.log`, junit
  `build/r80-installed-fullsuite-junit.xml`; `SCIREL_INSTALLED_RUNTIME=1`,
  `PYTHONPATH` cleared, `-I`): **1675 passed, 44 skipped, 0 failed**,
  exit code 0, 272.73 s; junit confirms 1719 tests, 0 errors, 0
  failures, 44 skipped; `scirel.__file__` verified inside the venv
  (`build\venv-r75-clean\Lib\site-packages\scirel\__init__.py`).
- Gate 7, catalog `build/catalog/r80` (`build/r80-catalog-build.log`):
  `complete`, declared_total 168, root digest
  `sha256:2b135cf642dec0aeab88d51b33c7759d4ccbbd966003305271f6e6cc039e4ed5`.
- Gate 10, source-free public API usage
  (`build/r80-gate-10-sourcefree-usage.ps1`, log
  `build/r80-pwsh-sourcefree-usage.log`): the clean venv's
  `build\venv-r75-clean\Scripts\python.exe` (no system site-packages)
  ran `-I -B r80_sourcefree_usage.py` from the isolated directory
  `C:\Users\26569\.claude\jobs\d48db198\tmp\scirel-r80-sourcefree`
  (outside the repository), with `PYTHONPATH` unset (verified None at
  runtime), `PYTHONDONTWRITEBYTECODE=1`, and the installed dev57 wheel
  (SHA-256
  `e84ec17640c3ad2710ac48a98a0e6feee415dcbe207414973930fa684be84946`).
  Recorded at runtime: `scirel.__file__` inside the venv
  site-packages; the repo `tests` package not importable. Representative
  calls with constructed-input expected values — this smoke does not
  assert saved-package parity; the saved-oracle parity claims belong to
  the direct science tests in
  `tests/operator_contracts/test_fida_spectral_family.py` only:
  `doppler_stark_zeeman_wavelengths` (zero-field Doppler degeneracy,
  electric-only Lyman wavenumber symmetry, the float component_count
  hardening rejection), `bin_fida_los_components` (floor binning with
  the conservation factor, out-of-range drop with retained raw
  indices), and the N5 -> N6 combination witness (15-component Balmer
  window). The exact script executed is preserved in the repository as
  the verifiable one-off artifact `build/r80-sourcefree-usage-script.py`
  (SHA-256
  `c4636a3665b189443dcc55392c839a55e9957e2f8389f01407b39d018ea2e0f0`,
  byte-identical to the file run at the isolated path; a one-off
  verification record, not a maintained process script). **Exit code
  0** (`R80-SOURCE-FREE-USAGE-PASSED`).

## Test delta (collect-verified)

- 19 new tests in
  `tests/operator_contracts/test_fida_spectral_family.py` (saved
  probes for both assets, the source-quirk pins — single cm/s -> m/s
  conversion, internal sightline normalization, `E' = ||E + v x B||`
  entry through a nonzero magnetic magnitude, the all-component
  zero-field degeneracy, the half-open-window edge discard and the
  retained raw out-of-range indices — the registered hardenings, and
  the two N5 -> N6 combination witnesses).
- Count-sync edits: `tests/test_asset_documentation.py` (168/169),
  `tests/test_affected_test_selection.py` (168),
  `tests/test_thin_mcp_adapter.py` (declared_total=168).
- Source full tree 1657 (r79-v3) + 19 = 1676, matching the measured
  receipt.

## Boundary

No qualified L1 consumption, no external physical correctness claim, no
expert approval, no trusted promotion, no public release are claimed.
Deferred from this round: the `fida_weights_los` phase producer (CX ->
colrad -> Doppler/Stark/Zeeman -> bin), the NPA stage-B weight
producer, the three MPI weight reductions (NPA five-array, active-FIDA
dual-array, neutron three-array), real-HDF5 table drivers, MC marker
production, the parallel (MPI-rank) reservoir merge graphs, and the
neutral-bank lifecycle.
