# r75 test evidence — FIDASIM N2 source-geometry family and trajectory-initialization graph

Base r74-v2 `8c20a2b` (148 assets, `0.1.0.dev49`, frozen snapshot
`build/verification/review-2026-09-27-r74-firehose-tension-wording-v2`)
-> r75 `0.1.0.dev50` (151 assets), final science HEAD `dd3a366`
(commits `a1c212c` family, `96fbd37` pair-semantics bounding, `dd3a366`
candidate-ray doc alignment). Three new fusion assets from the saved
FIDASIM bundle (framework node N2 `neutral_beam_source_sampling`):
`scirel.fusion.nbi-source-plane-ray` (mc_nbi source-plane ray +
aperture acceptance), `scirel.fusion.beam-grid-ray-intersection`
(grid_intersect finite rectilinear branch), and the task graph
`scirel.fusion.nbi-trajectory-initialization` (saved NBI轨迹初始化图
caller-random paths) composing five integrated leaves
(`nbi-injected-neutrals-normalization`, the two new leaves,
`nbi-energy-component-velocity`, `nbi-cell-directed-ray`).

## Shell record

All counted gates, builds and validations ran under pwsh 7+ in
`D:\software\PyCharm 2025.3.3\workspace\SciRel-intake-20260925` with
`PYTHONDONTWRITEBYTECODE=1`, `python -B`, explicit `PYTHONPATH=src` for
source-mode test runs, and `SCIREL_KN1DPY_REVIEW_ROOT` pointed at the
saved KN1DPy bundle in the sibling main SciRel checkout
(`D:\software\PyCharm 2025.3.3\workspace\SciRel\build\verification\neutral-harness-baseline-v3\inputs\l1\KN1DPy`),
used only by the pre-existing replay tests. The qualified L1 delivery
root (`D:/Users/26569/Desktop/归档_项目/codefusion/最小闭环压测环境`)
was re-checked empty (0 items) during this batch. The FIDASIM saved
bundle was read (zero writes) at
`D:\software\PyCharm 2025.3.3\workspace\SciRel\build\verification\neutral-harness-baseline-v3\inputs\l1\FIDASIM`
as provisional evidence only.

Saved-implementation content digests recorded per asset in the exact
documents' provenance sections:

- `NBI源面射线与孔径接受/scientific_operator.py` sha256 `2647ae3c…d7a32d4`; its operator.md `bd13f0d5…a320f1`.
- `有限直角束网格射线交点/scientific_operator.py` sha256 `e7e7294e…6c675`; its operator.md `9564c461…545a`.
- `NBI轨迹初始化图/graph.py` sha256 `f7eb0cca…1649af`; task_graph.yaml `3152e4c8…2b8d57`; task_graph.md `01d11bcb…74acb9`.

## Pre-freeze review findings and resolutions (recorded, not hidden)

Three independent pre-freeze review findings were resolved before the
freeze; no Codex edits were made (single-writer flow):

1. **Unit-ray norm overflow** (`nbi_source_plane_ray`): with
   `source_uniform=[1,0.5]`, `half_width_y=1e200`, `focus_y=1` the
   beam-ray squared norm overflows to Inf and `beam_ray / Inf` collapses
   to the zero vector, which passed the finiteness-only gate with
   `accepted=True`. Regression added first (red), then the gate now
   requires a finite and nonzero ray norm before dividing (registered
   hardening). The reviewer's exact call now raises
   `ValueError("…registered hardening")`. Ordinary-domain parity is
   byte-identical to the saved arm.
2. **NumPy-bool source shape**: `np.bool_(True)` passed the Python-bool
   check and satisfied `in (1, 2)`; regression added first (red), then
   the scalar contract rejects `(bool, np.bool_)`. Genuine ints/floats
   keep saved tuple-membership parity.
3. **Beam-grid pair semantics**: `f([2,0,0],[1,0,0],[0,0,0],[2,2,2])`
   reports `intersects_grid=True` with the pair entirely behind the
   origin. This is the saved arm's infinite-line face-pair enumeration
   (no origin-side check) and the same ordering rule that lets an origin
   inside the grid legitimately report its entry behind the origin, so
   the arithmetic is preserved verbatim and pinned by a new regression;
   the exact document's identity.relation, output description and
   known_limitations were bounded (no forward-only guarantee; forward-
   only callers must validate).
4. **Graph candidate-ray wording**: the trajectory graph computes the
   velocity scaling and optional grid handoff regardless of the aperture
   flag (saved caller-random parity); the graph document was aligned to
   candidate/diagnostic geometry ("accepted" overclaims removed),
   downstream consumers are directed to gate on `accepted`, the caller
   retry boundary is preserved, and a distinguishing regression pins the
   rejected-ray candidate velocity and grid handoff against direct leaf
   calls.

## Test delta (collect-verified)

- 24 new tests: 15 in
  `tests/operator_contracts/test_nbi_source_geometry.py` (saved probes,
  closed-form mappings, aperture bounds, registered hardenings, pinned
  pair semantics) and 9 in
  `tests/graph_contracts/nbi_trajectory_initialization/test_graph_nbi_trajectory_initialization.py`
  (composition order, branch exclusivity, grid handoff, replay
  determinism, RNG-boundary rejection, rejected-candidate parity).
- Count-sync edits: `tests/test_asset_documentation.py` (151/152),
  `tests/test_affected_test_selection.py` (151),
  `tests/test_thin_mcp_adapter.py` (declared_total=151).
- Source full tree 1573 passed at the intermediate HEAD (before the two
  pinning/parity regressions) and 1574 at final HEAD, matching
  1550 (r74) + 24.

## Gates (final bytes at `dd3a366`, returncode-checked)

- Affected selection (working tree, pre-commit): one earlier run
  fail-closed to a broad selection because the three new exact documents
  were not yet valid; after document fixes the documentation/catalog
  tests were rerun directly and passed (14 passed). The freeze gate
  requires full-tree evidence, so the full suite ran.
- Source-mode full tree, replay root active: **1574 passed, 43 skipped,
  0 failed**, pytest returncode 0, 276.29 s (r74: 1550/43; +24 new).
- Document validation, source state: **151/151**, `runtime_origin:
  source`, `examples_executed: true`, returncode 0 (receipt
  `build/r75-source-doc-validation.json`).
- Clean venv `build/venv-r75-clean` (Python 3.14; numpy 2.5.3, scipy
  1.18.1, pytest 9.1.1, setuptools 84.0.0 installed offline from
  `build/dependency-wheelhouse` with dependency resolution; no system
  site-packages), dev50 wheel installed `--no-index --no-deps
  --force-reinstall`; `-I` import check: `scirel.__file__` resolves
  inside the venv prefix, installed distribution version reads
  `0.1.0.dev50`, and `scirel.fusion.initialize_nbi_trajectory` is
  exported.
- Installed document validation from the clean venv (`-I`,
  `--installed-runtime`): **151/151**, `runtime_origin: installed`,
  `examples_executed: true`, returncode 0 (receipt
  `build/r75-installed-doc-validation.json`).
- Installed full tree (`-I`, `SCIREL_INSTALLED_RUNTIME=1`,
  `-o pythonpath=`, replay root active): **1573 passed, 44 skipped,
  0 failed**, pytest returncode 0, 283.41 s. Receipt note: unlike the
  r74 installed receipt (1398/195, replay roots unset), this run
  inherited an active KN1DPy replay root, so the KN1DPy replay
  comparisons executed in installed mode and passed; the +152
  passed / -151 skipped delta versus r74's installed receipt is that
  configuration difference, not a test-population change.
- Catalog `build/catalog/r75`: `complete: 151/151`, root digest
  `sha256:fa189331c58158df3e3c1d8fdd82a212dfc3735fcd3175e9fe4e6335023750a3`
  (rebuilt at final HEAD after the review-correction commits). Prior
  catalog builds are preserved and unreferenced by this freeze.
- Internal wheel `build/wheel-r75/scirel-0.1.0.dev50-py3-none-any.whl`,
  SHA-256
  `95515acce6684198bc7b57b5090bdd1a88c9c3c84223c549a82f238fafcb454d`
  (rebuilt at final HEAD; the pre-review wheel
  `9c2479b1…24412b` was discarded on rebuild).

## Boundary

No qualified L1 consumption, no external physical correctness claim, no
expert approval, no trusted promotion, no public release are claimed.
The saved FIDASIM bundle supports bounded historical development
comparison only; the serial RNG paths of the saved trajectory graph are
a declared non-ported runtime boundary. Deferred from this round:
NPA/FIDA weight-production chain and DCX spectrum state (closures need
MPI gate packages and the colrad core not yet integrated).
