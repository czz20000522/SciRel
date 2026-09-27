# KN1DPy Alpha contraction development integration

Status: development baseline candidate for expert review. SciRel base:
`77294b3`. Intake `647d5db` supplied the two pending, unapproved exact
documents and implementations. No qualified whole-source D1 delivery or expert
approval is inferred from these historical saved packages.

## Scientific boundary

- Atomic Alpha contracts four caller-provided SIG matrices with `fi_hat*ni`,
  `fH2`, `fi_hat*ni`, and `fH`, respectively. Molecular Alpha contracts three
  caller-provided matrices with `fHp_hat*nHP`, `fH`, and `fi_hat*ni`.
- Both use the predecessor's Fortran-order velocity flatten/restore. The
  molecular `ni_correct` branch replaces `n` with `max(n-nHP, 0)` only for
  `Alpha_H2_P`. Signed matrix cells and signed densities are not clamped.
- The saved molecular source has a registered `Alpha_CX` reshape defect. The
  saved formal package and this callable use the explicit reshape repair. No
  matrix construction or Omega aggregation is bundled into these leaves.
- Both leaves have no direct callable dependencies. The two candidate matrix
  assemblies require seven distinct collision cross-section exact assets that
  are not yet in the main catalog; Omega additionally requires the matching
  matrix and Alpha assets. Those four later candidates remain outside this
  integration.

## Comparison and verification

The saved `KN1DPy` Alpha implementation SHA-256 values matched the intake pins:

- Atomic: `6a30883d44d3fee77add57a09617e9621e728c7e984f3e4394f3b372683d4839`.
- Molecular: `bbf1f1edc4c82ddda57ac7cb32730d4bfb5749670151f73ff2de370313366915`.

The direct test failed at import before implementation. It now checks exact
small-matrix results for every family, signed cells, Fortran ordering, the
corrected-density branch and zero clipping, plus finite real and shape failures.
It passed 11 tests. The five SHA-gated historical replay tests passed with
`build/verification/neutral-harness-baseline-v3/inputs/l1/KN1DPy` as a
read-only saved input. This is bounded arithmetic parity, not external
atomic-physics validation or renewed D1 qualification.

`pwsh ./scripts/check.ps1 -Mode affected` selected the two Alpha assets,
exact-document and public-surface checks without full-suite fallback: 37
passed and 5 replay tests skipped without the optional saved-root environment
variable. All 46 exact documents passed source-runtime and executable-example
validation. The catalog remains `partial: 46/91` at `0.1.0.dev5`; no release
gate or wheel build was run.

Expert recognition, the molecular reshape interpretation, distribution
licensing, and complete collision-matrix/Omega composition remain open.
