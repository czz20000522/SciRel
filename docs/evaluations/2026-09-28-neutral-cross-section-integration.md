# KN1DPy collision cross-section development integration

Status: development baseline candidate for expert review. SciRel base:
`c018339`; intake `647d5db` remains a pending, unapproved source. The seven
cross-section leaves have no direct callable dependencies and close the exact
asset dependencies of both pending collision-matrix assembly candidates.

## Scientific boundary

- Atomic and molecular charge-exchange fits remain separate Janev coefficient
  sets. Atomic charge exchange also retains the Freeman-Jones branch and its
  different upper clipping endpoint.
- H-H elastic retains distinct momentum and viscosity fits. H2-H2
  `viscosity=True` uses the same fit as its default, as in the saved source.
- H-H2 and H+-H return a leading singleton axis. H+-H returns exactly zero at
  10 eV because the saved branches use strict inequalities. The saved document
  shape boilerplate and the breakpoint's physical interpretation remain expert
  questions; neither was silently normalized.
- All seven fits use the saved clipped energy ranges, coefficients, scaling and
  output shapes. The port rejects negative energy as already declared by the
  intake. It additionally rejects complex, boolean and numeric-string energy
  inputs before float conversion, matching each exact document's real dtype.

## Saved comparison

The seven read-only saved implementation files in
`build/verification/neutral-harness-baseline-v3/inputs/l1/KN1DPy` matched
their intake SHA-256 pins, in the order atomic CX, molecular CX, H-H, H-H2,
H+-H, H2-H+ and H2-H2:

1. `af55e393c0e7510a0c1734eabc2a635374c1dfe2ec8dcc3ae87386772a80b099`
2. `2be195e5393454e78a728eee8de53a12974865ad3fef470b8566b61ff3806a5f`
3. `129bc8e2d541e1ecde21584b01c89e6ebfc48115b5c582b0e15452e2f753c42c`
4. `4377ae235fbcc0fb798253c995f44cf1e91aedecc99ce1b6bcbd1418b6c8d1bb`
5. `b92dbb2af1596fa9aa505cb478b3be1cdc4ca92c1bf40321d2b52472c64c6daf`
6. `99ed2176ae8a27bfa7c551d53eec9a3b6c2abcea6acaa526a2201b96cb3239ed`
7. `0c10fbb9364212681e6d8c023b5db707a09b02f73e984948be1d4448e7daccac`

The direct suite first failed at import. The copied scientific tests then passed
47 cases; a new 21-case input-type regression failed against all seven copied
candidate implementations and passed after the common input check. Together
they passed 68 tests. The SHA-gated historical replay passed 23 tests on
finite real inputs, including branch, clipping, shape and source-repair
witnesses. These checks establish bounded arithmetic agreement, not an
external atomic-physics oracle or renewed whole-source D1 qualification.

The isolated `affected` run selected the seven leaves, their shared input
check, direct/replay tests, public exports, the retained momentum namespace
contract, catalog and release-baseline checks without full-suite fallback:
189 passed and 23 optional replay tests skipped when the saved root was not
set. The package-export selector now includes that namespace contract. All 53
exact documents passed source-runtime
and executable-example validation. The development catalog is `partial:
53/100` at `0.1.0.dev5`; no release or wheel was built.

Matrix assembly remains the next scientific relation. Omega aggregation still
depends on the corresponding matrix and Alpha leaves. Expert recognition,
physical validation of the fits and breakpoint, and public distribution
licensing remain open.
