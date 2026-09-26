# Candidate: KN1DPy collision frequency contraction family (two operators)

Status: development candidate prepared for expert review, to be frozen as the
pending_unapproved r66 successor of r65. Nothing here is expert approval, a
trusted version, or a public release.

## Base and comparison scope

- SciRel base: `c8c3a988` (r64-v3 frozen, 120 assets dev38) plus the r65
  batch; the r65 freeze
  (`build/verification/review-2026-09-27-r64-convergence-v3`) is untouched.
  r66 increments the catalog to 128 exact documents, version
  `0.1.0.dev39` -> `0.1.0.dev40`.
- Unpublished candidate pool: re-checked by relation for Alpha collision
  frequency contraction — none exists; the baseline has the SIG matrix
  assembly inputs and the downstream CX scattered-source consumer but no
  contraction leaf. This is a **new capability** pair.
- Incoming source (read only): the saved KN1DPy bundle
  `D1待重审历史产物/KN1DPy-631d0bf1` (provisional; strict D1 withdrawn),
  implementations pinned by SHA-256 `6a30883d44d3fee77add57a09617e9621e728c7e984f3e4394f3b372683d4839`
  (atomic) and `bbf1f1edc4c82ddda57ac7cb32730d4bfb5749670151f73ff2de370313366915`
  (molecular). The bundle root used for the environment-gated replay is
  `SciRel/build/verification/neutral-harness-baseline-v3/inputs/l1/KN1DPy`.
- Qualified L1 consumption: none (delivery root re-checked empty; strict D1
  withdrawn). Bounded historical development evidence only.

## Proposed identity

- `scirel.kinetic.atomic-alpha-contraction`, callable
  `contract_atomic_hydrogen_alpha_frequencies(SIG_CX, SIG_H_H, SIG_H_H2,
  SIG_H_P, fi_hat, ni, fH2, fH)` — four Alpha frequency fields
  (Alpha_CX, Alpha_H_H2, Alpha_H_P, Alpha_H_H), each `(nvr,nvx,nx)`.
- `scirel.kinetic.molecular-alpha-contraction`, callable
  `contract_molecular_hydrogen_alpha_frequencies(SIG_CX, SIG_H2_H, SIG_H2_P,
  fH, fHp_hat, fi_hat, n, nHP, ni_correct=False)` — three Alpha frequency
  fields (Alpha_CX, Alpha_H2_H, Alpha_H2_P), each `(nvr,nvx,nx)`.

## Material scientific differences and declared divergences

1. **Registered Alpha_CX reshape repair (molecular arm).** The raw source
   `kinetic_h2.py:1204` writes `Alpha_CX[:,:,k] = SIG_CX @ Work` without the
   Fortran-order restore reshape, which fails on the canonical
   `nvr*nvx != nvx` carrier. The saved formal implementation applies the
   minimal `.reshape(..., order='F')` repair; this port reproduces the
   repaired saved implementation bit for bit, and the original defect stays
   registered verbatim in the immutable source for expert review. The atomic
   arm is verbatim: no repair is claimed.
2. **Fail-closed validation added by the formal implementation.** Both ports
   reject non-square or misordered SIG matrices, misaligned distributions
   and density profiles, and any non-finite input or output with named
   `ValueError`s; the replay test additionally verifies the saved arm's
   rejection behavior agrees exactly.
3. **No positivity gate on densities.** Negative or zero densities are not
   rejected at runtime; the contraction uses each finite value as given. The
   molecular `ni_correct` branch clamps `n - nHP` at zero cell-wise — a
   source-defined density correction, not a positivity gate.
4. **Negative cells preserved.** Bounded negative output cells inherited
   from the signed elastic SIG families (`vx_vx` / `vr2_vx2` factors) are
   reproduced as-is, never clamped; `Alpha_CX` is nonnegative on the saved
   domain where SIG_CX is nonnegative. Physical acceptability is an open
   expert question.
5. **Pre-review corrections in this batch.** `SIG_H_H` gained symmetric
   asarray/shape validation that was missing from the first draft; the
   discriminating replay uses asymmetric SIG matrices, distinct
   distributions and a Fortran-order carrier witness (one-hot identity plus
   labelled fH), and both `ni_correct` branches are covered.

## Evidence

- Independent recomputation witness: the direct tests build the Fortran-order
  contraction from first principles (one-hot identity matrices and labelled
  distributions), so a wrong flatten/restore order in either arm surfaces as
  a mismatch.
- Environment-gated replay (5 tests): bit-for-bit saved-arm parity for both
  operators, rejection-behavior agreement, and asymmetric-SIG parity runs
  across both `ni_correct` branches.
- 12 tests total (7 direct + 5 replay); `pytest --collect-only` verified.

## Files

- `proposal/atomic_alpha_contraction.py`, `proposal/molecular_alpha_contraction.py`
- `proposal/test_alpha_contraction.py`, `proposal/test_alpha_contraction_l1.py`
- `proposal/scirel.kinetic.atomic-alpha-contraction.json`,
  `proposal/scirel.kinetic.molecular-alpha-contraction.json`

## Version and impact

Version `0.1.0.dev39` -> `0.1.0.dev40`; catalog 126 -> 128 exact documents.
The other 126 documents change only in the mechanical
`implementation_version` bump.
