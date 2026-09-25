# SciRel axisymmetric terminal-field successor r32

Status: development review pending, not expert-approved, trusted, or publicly released. The qualified L1 delivery root remains empty. There is no trusted baseline, so the first expert review still covers all 68 public assets; r31 is only a development comparison.

## Scientific change

`solve_axisymmetric_anisotropic_picard` already rejected a terminal magnetic field below `minimum_field`, but did so after calling the caller-owned pressure closure and force Operator. A low terminal field could therefore reach a singular closure and raise its error before the graph's declared `FloatingPointError`. A new regression reproduced that sequence: its closure was invoked on the low terminal field and raised `AssertionError`.

The graph now checks the returned state's field immediately after recomputing it, before invoking the terminal pressure closure, dynamic mask or force Operator. The iteration field check is unchanged. The final graph test uses a self-consistent zero `B_R/B_Z/B` terminal field and confirms one valid closure call during the iteration, no terminal closure call, and the declared `FloatingPointError`. The exact document updates the failure order and graph edge; its public signature, dependencies, physical equations, numerical defaults and valid-input computation do not change. Existing numerical assertions and tolerances were retained.

The implementation version advances from `0.1.0.dev16` to `0.1.0.dev17` because the wheel source changed. All 68 exact documents carry the new version; only `scirel.equilibrium.axisymmetric-anisotropic-picard` has a non-mechanical scientific contract change. The historical admitted-only ledger and earlier frozen snapshots remain untouched. Experts should review this graph's failure semantics and any affected consumer assumptions; the development comparison does not establish a trusted baseline or authorize the other 67 assets.

## Verification and limits

The new regression failed before the fix, then the graph file passed 12 tests. `scripts/check.ps1 -Mode affected` ran the whole suite because the implementation version changed: 903 passed, 43 skipped. All 68 exact documents passed source-runtime signature and executable-example validation. The development catalog covers 68/68 assets at root digest `sha256:730cd53af29f62f0fc359845afbce8dfc109c47b4d373094abe3bcd18fdd6610`.

The internal dev17 wheel has SHA-256 `f6dc4330fc558609e95df838b0f4a1e1c02dcf358ea39ae6d74204ea7a90a707`. It was installed offline from the local dependency wheelhouse into a Python 3.14.3 Windows venv that does not inherit system site-packages. Under `python -I`, SciRel, NumPy and SciPy resolved to that venv; 627 installed scientific and composition tests passed, 43 source-dependent tests skipped, all 68 documents passed installed-runtime signature/example validation, and the three user acceptance tasks passed. The frozen test evidence contains the exact commands and hashes.

This proves the tested Python/Windows development installation and selected science contracts, not complete source-project reproduction, other platforms, license clearance, physical applicability of arbitrary closures, expert recognition, trusted promotion or public release. The current L1 delivery root remains empty.
