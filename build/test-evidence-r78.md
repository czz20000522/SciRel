# r78 test evidence — FIDASIM beam-neutral multi-segment deposition family

Base r77-v3 `de6b410` (158 assets, `0.1.0.dev54`, frozen snapshot
`build/verification/review-2026-09-27-r77-dcx-colrad-family-v3`)
-> r78 `0.1.0.dev55` (162 assets), final science HEAD `a8ca079`. Four new
fusion assets from the saved FIDASIM bundle (framework node N3
`neutral_population_transport`; the deposition handoff sits on the N3/N4
seam): `scirel.fusion.beam-grid-ray-segment-tracking`,
`scirel.fusion.n3-n4-segment-deposition`,
`scirel.fusion.ndmc-deposition-producer`, and the composition task graph
`scirel.fusion.beam-neutral-segment-deposition-loop` over two integrated
leaves plus graph-internal validation helpers in the enforced source
node order.

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
documents' provenance sections.

## Dimensional reconciliation and public-asset decision (reviewer findings)

Pre-freeze review raised: (1) the rate-density unit semantics of the N3/N4
chain (states cm^-3 s^-1 per the `nneutrals*fraction/dv` seeding and the
integrated `nbi-component-initial-state` asset), with precise
`*_cm_inv3_s_inv` public field names; (2) the frozen r77 colrad advance
document's inconsistent unit labels, corrected in this successor as a
development contract repair with unchanged arithmetic (N4 composition
stays external); (3) the signed N3 segment flux versus the saved NDMC
arm's documented nonnegativity (bounded incompatibility, signed
source-faithful arithmetic kept, colrad population-gain witness added);
(4) the graph-internal placement of the two saved data-edge validation
operators (no standalone promotion until a second consumer exists);
(5) np.bool_/float strictness gaps, negative N4 density/photons gates,
and fractional knot counts. All are documented in the exact documents,
`review.md`, and pinned by discriminating regressions; none is expert
approval, and the unit/e0/nlaunch questions remain open for expert
adjudication.

## Test delta (collect-verified)

- 28 new tests in
  `tests/operator_contracts/test_beam_deposition_family.py` (saved probes
  for all four assets, the end-to-end colrad population-gain witness,
  signed-flux and negative-expected-total cases, record-count and
  snapshot contract rejections, and the registered hardenings).
- Count-sync edits: `tests/test_asset_documentation.py` (162/163),
  `tests/test_affected_test_selection.py` (162),
  `tests/test_thin_mcp_adapter.py` (declared_total=162).
- Source full tree 1606 (r77-v3) + 28 = 1634, matching the measured
  receipt.

## Gates (final bytes at `a8ca079`, returncode-checked)

- Source-mode full tree, replay root active: **1634 passed, 43 skipped,
  0 failed**, pytest returncode 0, 320.06 s (r77-v3: 1606/43).
- Document validation, source state: **162/162**, `runtime_origin:
  source`, `examples_executed: true`, returncode 0 (receipt
  `build/r78-source-doc-validation.json`).
- Clean venv `build/venv-r75-clean` (numpy 2.5.3, scipy 1.18.1,
  pytest 9.1.1, setuptools 84.0.0 offline from
  `build/dependency-wheelhouse`; no system site-packages), dev55 wheel
  installed `--no-index --no-deps --force-reinstall`.
- Installed document validation (`-I`, `--installed-runtime`): **162/162**,
  `runtime_origin: installed`, `examples_executed: true`, returncode 0
  (receipt `build/r78-installed-doc-validation.json`).
- Installed full tree (`-I`, `SCIREL_INSTALLED_RUNTIME=1`,
  `-o pythonpath=`, replay root active): **1633 passed, 44 skipped,
  0 failed**, returncode 0, 327.65 s.
- Catalog `build/catalog/r78`: `complete: 162/162`, root digest
  `sha256:f16f84e0a46e9552b64f0e2e9804bcc3b6ee9135dc390d5d0179b9420d6fbfbf`.
- Internal wheel `build/wheel-r78/scirel-0.1.0.dev55-py3-none-any.whl`,
  SHA-256
  `591a42918a7f15ca12d59ccfd580d1056b6c09ef8b51555906540bec9eedd73b`.

## Candidate packet

`review_candidates/2026-09-27-beam-deposition-family/` (review.md + nine
byte-identical proposal copies) was created before the freeze and bound by
SHA-256 in `docs/evaluations/candidate-review-materials-index-2026-09-25.md`
(Batch r78 section), and is snapshotted directly as review materials by
the r78 freeze.

## Boundary

No qualified L1 consumption, no external physical correctness claim, no
expert approval, no trusted promotion, no public release are claimed.
Deferred from this round: real-HDF5 table drivers, the NPA/FIDA
weight-production chain, the multi-cell population merge (neutral
reservoir merge family) and MC marker production.
