# GSEQ filament-coil Green development integration

Status: SciRel development integration, not qualified D1 consumption, expert
approval or public release. Comparison base: `e5ba42d`; intake snapshot:
`647d5db` (`pending_unapproved`). The designated qualified D1 delivery root
was read-only checked at batch start and contained zero entries, including
hidden entries. The saved GSEQ package and original MATLAB files were used
only as bounded historical comparison material.

Three public relations form an ordered caller composition: coil geometry
produces a radius with the original `1e-8 m` axis offset and per-coil squared
moduli; the polynomial-log operator evaluates K/E; the Green response consumes
that radius and matching per-coil values to sum `psi = R A_phi` (`Wb/rad`),
`B_r` and `B_z`. The response is a declared variant of the existing
scipy-elliptic circular-filament relation. It accepts caller-supplied K/E and
one target, and rejects singular/nonfinite results; it does not replace the
existing arbitrary-point API. No new dependency was introduced.

## Source comparison

- Original GSEQ `fun_ellipEK.m` (SHA-256
  `13e0b5662e7924a8bda70ed62d9d50203457aa34651b2654e8714542484768ae`)
  contains the whole-array `if (k2 == 1.0)` guard. The frozen saved L1 Python
  package (SHA-256
  `1fb09545af5684ba69340a0e0c8f18bfac9df38680af7f5354dc991ee0ccb55c`)
  instead substitutes K=Inf, E=1 element-wise for `m=1`. SciRel follows the
  MATLAB branch: a mixed array has K=Inf, E=NaN at its `m=1` element. The
  original `fun_Bfield.m` calls the function one coil at a time, so this
  discrepancy concerns the new public vector call, not an observed mismatch
  on that scalar call path. No MATLAB runtime replay or package equivalence is
  claimed.
- Original `fun_Bfield.m` (SHA-256
  `64620f831dbb239608d1d617f0280f55b7b5ad2db933a5bfffbfed6f38a288`)
  gives the axis offset and imethod=1 Green formulas. Direct tests compare
  the accepted formula with an independent recomputation and with the
  maintained circular-filament relation at equal scipy K/E values.
- The candidate geometry accepted a finite positive configuration whose
  computed modulus underflowed to zero, despite its `(0,1]` output contract.
  A failing regression preceded a two-line fail-closed check. The exact
  document records this additional SciRel boundary; the saved implementation
  is not claimed to reject it.

All three exact documents bind the current `0.1.0.dev5` callable signatures,
input/output units, failure behavior and limited provenance. The 117/117
catalog count describes development documentation coverage only. Source
coverage claims, scientific correctness, expert recognition and licensing
remain separate decisions.

## Main checkout verification

The integration was applied to the main SciRel checkout as `ab8189f`, with
the three README count updates committed separately as `a0d7284`. Against
`e5ba42d`, `pwsh ./scripts/check.ps1 -Mode affected -BaseRef e5ba42d`
selected the three new relations and their public/documentation tests:
39 passed, with three expected NumPy overflow/invalid warnings from the
nonfinite-output rejection test. `python scripts/validate_asset_documents.py
catalog/examples --check-runtime --execute-examples` validated all 117 exact
documents, including runtime signatures and examples. `git diff --check
e5ba42d..HEAD` passed before this record update. Other owners' uncommitted
README and extraction-skill changes remained outside these commits.
