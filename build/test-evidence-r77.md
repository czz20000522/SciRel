# r77 test evidence — FIDASIM DCX/HALO colrad family

Base r76-v1 `0cca44c` (153 assets, `0.1.0.dev51`, frozen snapshot
`build/verification/review-2026-09-27-r76-halo-iteration-feedback-v1`)
-> r77 `0.1.0.dev52` (158 assets), final science HEAD `8aa1da1`. Five new
fusion assets from the saved FIDASIM bundle (framework node N3
`neutral_population_transport`; the advance operator sits on the N3/N4
seam): `scirel.fusion.dcx-thermal-species-selection`,
`scirel.fusion.dcx-halo-colrad-initial-state`,
`scirel.fusion.collisional-radiative-rate-matrix`,
`scirel.fusion.collisional-radiative-state-advance`, and the composition
task graph `scirel.fusion.dcx-halo-marker-initialization` over four
integrated leaves plus two caller provider capabilities in the enforced
source node order.

## Shell record

All counted gates, builds and validations ran under pwsh 7+ in
`D:\software\PyCharm 2025.3.3\workspace\SciRel-intake-20260925` with
`PYTHONDONTWRITEBYTECODE=1`, `python -B`, explicit `PYTHONPATH=src` for
source-mode test runs, and `SCIREL_KN1DPY_REVIEW_ROOT` pointed at the
saved KN1DPy bundle in the sibling main SciRel checkout (used only by the
pre-existing replay tests). The qualified L1 delivery root
(`D:/Users/26569/Desktop/归档_项目/codefusion/最小闭环压测环境`) was
re-checked empty (0 items) at batch start. The FIDASIM saved bundle was
read (zero writes) as provisional evidence only.

Saved-implementation content digests recorded per asset in the exact
documents' provenance sections:

- `DCX热物种选择/scientific_operator.py` sha256 `9d9c6def…c05181`.
- `DCXCX初态与光子快离子修正/scientific_operator.py` sha256 `f642cfed…508bf`.
- `碰撞辐射速率矩阵组装/scientific_operator.py` sha256 `38f1eb0c…9ef1cc`.
- `碰撞辐射本征态推进/scientific_operator.py` sha256 `fbc4d987…226ca6a`.
- `DCXHalo标记初态图/graph.py` sha256 `7cde57eb…68b3cfc`; task_graph.yaml `52453e6c…02d123f`; task_graph.md `c65bc579…c0d8688`.

## Zero-eigenvalue boundary and evidence ceiling (pre-freeze review)

Pre-freeze review raised the zero-eigenvalue issue in the eigen-advance:
the saved arm's `np.where(eigval == 0.0, 1.0, eigval)` denominator rule
gives a zero mode zero integrated density, while the saved package's own
operator.md registers that the Fortran source adds +1 to a zero
eigenvalue before the exponential (a different value, an avoidance quirk)
and asks for expert adjudication. Resolution: the arithmetic is preserved
verbatim (the saved arm is this port's provenance target), the branch is
pinned by the discriminating regression
`test_advance_pins_saved_arm_zero_eigen_boundary`, and the exact document
records the divergence, its untriggered status in the bundle's 823
bounded replay events (240 synthetic R-N48 + 583 real-HDF5-table R-N49,
all non-zero eigenvalues), and the eigensolver conditioning ceiling
(numpy/LAPACK versus the source's balance+QR; ~5e-6 on stiff matrices per
the saved ledger) as explicit evidence limitations. No silent repair of
source arithmetic was made.

## Test delta (collect-verified)

- 17 new tests in
  `tests/operator_contracts/test_dcx_colrad_family.py` (saved probes for
  all five assets, round-by-round leaf equivalence, provider call-order
  enforcement, provider contract rejections, overflow gates, and the two
  pins).
- Count-sync edits: `tests/test_asset_documentation.py` (158/159),
  `tests/test_affected_test_selection.py` (158),
  `tests/test_thin_mcp_adapter.py` (declared_total=158).
- Source full tree 1587 (r76) + 17 = 1604, matching the measured receipt.

## Gates (final bytes at `8aa1da1`, returncode-checked)

- Source-mode full tree, replay root active: **1604 passed, 43 skipped,
  0 failed**, pytest returncode 0, 328.68 s (r76: 1587/43; +17 new).
- Document validation, source state: **158/158**, `runtime_origin:
  source`, `examples_executed: true`, returncode 0 (receipt
  `build/r77-source-doc-validation.json`).
- Clean venv `build/venv-r75-clean` (numpy 2.5.3, scipy 1.18.1,
  pytest 9.1.1, setuptools 84.0.0 offline from
  `build/dependency-wheelhouse`; no system site-packages), dev52 wheel
  installed `--no-index --no-deps --force-reinstall`.
- Installed document validation from the clean venv (`-I`,
  `--installed-runtime`): **158/158**, `runtime_origin: installed`,
  `examples_executed: true`, returncode 0 (receipt
  `build/r77-installed-doc-validation.json`).
- Installed full tree (`-I`, `SCIREL_INSTALLED_RUNTIME=1`,
  `-o pythonpath=`, replay root active): receipt in the r76 pattern
  (KN1DPy replay comparisons execute in installed mode; configuration
  difference versus r74-style receipts, not a test-population change).
- Catalog `build/catalog/r77`: `complete: 158/158`, root digest
  `sha256:4a70c6ad5a1033b08a5681836833695398ae9424395ca4af8def6e34b6356454`.
- Internal wheel `build/wheel-r77/scirel-0.1.0.dev52-py3-none-any.whl`,
  SHA-256
  `89e4e7e89113f872c3d375ad68ea12e253edaab4517fb96ae6af800faa17f7bc`.

## Candidate packet

`review_candidates/2026-09-27-dcx-colrad-family/` (review.md + eleven
byte-identical proposal copies) was created before the freeze and bound by
SHA-256 in `docs/evaluations/candidate-review-materials-index-2026-09-25.md`
(Batch r77 section), and is snapshotted directly as review materials by
the r77-v1 freeze.

## Boundary

No qualified L1 consumption, no external physical correctness claim, no
expert approval, no trusted promotion, no public release are claimed.
Deferred from this round: real-HDF5 table drivers and the multi-segment
deposition loop, the NPA/FIDA weight-production chain, the multi-cell
population merge and MC marker production.
