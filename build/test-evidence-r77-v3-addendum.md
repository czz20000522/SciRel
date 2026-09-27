# r77-v3 successor evidence addendum — ballistic matrix-validation repair

r77-v2 (commit `e401e1e` freeze record; science HEAD `d693aca`,
`0.1.0.dev53`, snapshot
`build/verification/review-2026-09-27-r77-dcx-colrad-family-v2`) is
preserved untouched. Post-freeze read-only review found one further
contract case, reproduced with `python -B` before the repair (fix commit
`686972e`, index re-binding `de6b410`, `0.1.0.dev54`, 158 assets):

1. **Ballistic matrix-validation gap**: the colrad exact document claimed
   `rate_matrix_s_inv` is "validated in all cases but consumed only when
   `in_plasma` is true", but the ballistic branch returned before the
   matrix conversion and shape/finiteness check, so a misshaped or
   non-finite matrix was silently accepted outside plasma (reviewer
   cases: wrong shape, NaN entries, Inf entries with `in_plasma=False`).
   The ballistic branch now validates matrix shape and finiteness in
   both branches (registered hardening; the saved arm validated only on
   the in-plasma branch). The real-eigenstate 1e-12 gate and the
   eigensolve stay on the in-plasma branch: the ballistic branch still
   never consumes the matrix, preserving the source quirk. The exact
   document now states precisely which checks hold in which branch
   (including the corrected "outside plasma" wording in the
   verification scope).

The zero-eigenvalue adjudication documentation is untouched. dev53 ->
dev54; the version bump, the two exact-document wording updates
(`rate_matrix_s_inv` constraints and `failure_semantics`) and the
verification-scope line are part of the same commit. 19 family tests
(one net new test), 158 assets.

## Gates (final bytes at `de6b410`, returncode-checked)

- Source-mode full tree, replay root active: **1606 passed, 43 skipped,
  0 failed**, returncode 0, 282.18 s (r77-v2: 1605/43; +1 net new test).
- Document validation, source state: **158/158**, `runtime_origin:
  source`, `examples_executed: true` (receipt
  `build/r77v3-source-doc-validation.json`).
- Clean venv `build/venv-r75-clean` (numpy 2.5.3, scipy 1.18.1,
  pytest 9.1.1, setuptools 84.0.0 offline from
  `build/dependency-wheelhouse`; no system site-packages), dev54 wheel
  installed `--no-index --no-deps --force-reinstall`.
- Installed document validation (`-I`, `--installed-runtime`): **158/158**,
  `runtime_origin: installed`, `examples_executed: true`, returncode 0
  (receipt `build/r77v3-installed-doc-validation.json`).
- Installed full tree (`-I`, `SCIREL_INSTALLED_RUNTIME=1`,
  `-o pythonpath=`, replay root active): **1605 passed, 44 skipped,
  0 failed**, returncode 0, 257.17 s.
- Catalog `build/catalog/r77-dev54`: `complete: 158/158`, root digest
  `sha256:2a0641d070071455f2737a9c7828e19a9f4dd2553978fdba532bbb59063b5f68`.
- Internal wheel
  `build/wheel-r77/scirel-0.1.0.dev54-py3-none-any.whl`, SHA-256
  `909d70a5f3cbf72d2b946b14fa60993a167335fa29b21f7d00996f32f246ee9f`
  (built with setuptools 84.0.0 from the offline wheelhouse venv).
- Candidate packet: the advance module, its exact document and the
  family test file re-bound by SHA-256 in the materials index (r77-v3
  corrected bytes; the other nine files keep their r77-v2 digests;
  r77-v1/v2 preserved).

## Boundary

No qualified L1 consumption, no expert approval, no trusted promotion, no
public release are claimed. r77-v2 remains frozen and preserved; r77-v3
is the current pending_unapproved successor.
