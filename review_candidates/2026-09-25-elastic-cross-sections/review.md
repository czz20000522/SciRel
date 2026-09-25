# Candidate document: KN1DPy elastic momentum-transfer cross-section family

Status: development candidate prepared for expert review. Nothing here is
expert approval, a trusted version, or a public release. The development
integration lives on branch `codex/kn1dpy-maxwellian-rate-intake` on top of
SciRel base `380cdb1a7f86f4b2690c9d05a380e16a4f06f758` (r52).

## Incoming capability

Five saved KN1DPy operators of one relation family -- elastic
momentum-transfer cross-section fits for the hydrogen species pairs of the
neutral kinetic module:

1. `原子氢弹性动量转移截面` (`KN1DPy/sigma/sigma_el_h_h.py:19-38`, caller
   `kinetic_h.py:957`): H-on-H elastic cross section with the source's
   distinct momentum-transfer and viscosity five-coefficient fits,
   source-clipped to [0.03, 1.01e4] eV.
2. `原子氢质子弹性动量转移截面` (`KN1DPy/sigma/sigma_el_p_h.py:1-42`, caller
   `kinetic_h.py:996-1016`): H+-on-H elastic momentum-transfer cross section,
   piecewise below/above a 10 eV breakpoint, clipped to [0.001, 1.01e5] eV.
3. `原子氢分子氢弹性动量转移截面` (`KN1DPy/sigma/sigma_el_h_hh.py:1-31`,
   caller `kinetic_h.py:970-984`): H-on-H2 elastic momentum-transfer cross
   section, single fit clipped to [0.03, 1.01e4] eV.
4. `分子氢分子氢弹性动量转移截面` (`KN1DPy/sigma/sigma_el_hh_hh.py:1-31`,
   caller `kinetic_h2.py:1099-1125`): H2-on-H2 elastic momentum-transfer cross
   section, single fit clipped to [0.03, 1.01e4] eV.
5. `分子氢质子弹性动量转移截面` (`KN1DPy/sigma/sigma_el_p_hh.py:1-31`, caller
   `kinetic_h2.py:1070-1093`): H2-on-H+ elastic momentum-transfer cross
   section, single fit clipped to [0.03, 1.01e4] eV.

## Current SciRel capability

The collisions domain holds the Maxwellian relative-speed rate average, the
momentum scales, the relativistic Bessel closure, the r49 atomic-H collision
data (CX cross section, CX rate coefficient, COLLRAD ionization) and the r51
molecular-H2 CX pair. No baseline asset evaluates an elastic momentum-transfer
cross section. The unpublished candidate pool has none either. All five are
therefore proposed as **new capabilities**; no reuse, variant, duplicate or
merge applies. The five remain separate sibling identities for five species
pairs; the H–H viscosity branch is a different quantity, not a variant of the
momentum-transfer fit.

## Material scientific differences (all documented in the exact documents)

1. **Negative-energy rejection (all five).** Every saved document declares
   nonnegative energies; every saved implementation silently clipped negatives
   to the lower endpoint. The successors reject them. In-domain values keep
   the declared endpoint clipping bit for bit.
2. **H–H selector requirement.** The saved document declares a scalar
   `viscosity` selector; the saved implementation relied on `bool()`
   coercion, silently accepting 0-d and single-element arrays and failing on
   multi-element arrays with NumPy's generic ambiguity error that does not
   name the quantity. The successor requires a 0-d scalar and names the
   quantity. (Initial repair premise corrected during bring-up after an
   empirical probe of the saved implementation; the witness test records the
   verified saved behavior.)
3. **H+–H breakpoint and output wrapper kept as declared source behavior.**
   The strict-branch selection makes a clipped energy of exactly 10 eV
   exactly zero, and the saved formal implementation preserves the source
   `np.array([E])` wrapper as one extra leading singleton output axis. The
   saved document's boilerplate instead declares the output shaped like the
   input; the discrepancy is kept in favor of the implementation's documented
   behavior and recorded as an open expert-review question rather than
   silently resolved.
4. **H–H2 output wrapper kept**, same reasoning as (3).
5. **H2–H2 selector validation kept**: the saved implementation already
   requires a scalar boolean/integer selector and documents `viscosity=True`
   as a same-fit fallback; both are asserted as the declared contract.
6. **Error messages** name the quantity, consistent with the maintained
   library's failure style. No existing numerical assertion is weakened.

## Evidence

Source-free maintained tests (47 total, verified by `pytest --collect-only`:
31 direct + 16 environment-gated replay; per-file counts in the README
inventory table) establish each fit against an independent closed-form
evaluation of its frozen coefficients, the endpoint clipping, the input and
failure contracts including the repairs, the H–H two-branch distinction, the
H+–H breakpoint zero and leading axis, and the composition of the H–H
momentum-transfer fit with the retained Maxwellian rate average. The
environment-gated replays pin each saved implementation by SHA-256
(`129bc8e2…`, `b92dbb2a…`, `4377ae23…`, `0c10fbb9…`, `99ed2176…`) and
reproduce the saved arithmetic exactly, including repair witnesses (the saved
implementations clip a negative energy into the fit; the H–H implementation
accepts a single-element array selector). The failing-regression-first
sequence was demonstrated: with the five new modules removed, the ten new
test files fail collection with 10 ImportErrors, and pass (47) once restored.
Numerical details and gates are in
`docs/evaluations/intake-2026-09-25-elastic-cross-sections.md`.

Evidence ceiling: KN1DPy's strict D1 qualification is withdrawn and the bundle
sits in the re-review archive, so the replays are bounded historical
development comparison only. No test establishes any fit against an external
atomic-physics reference (the saved package records that residual as
`validation_oracle_gap`); the source-project correctness outside the compared
domain is not claimed.

## Public API and dependency impact

Five new public callables, exported from `scirel.collisions` and the root
namespace; five new exact documents; development version moves
`0.1.0.dev25` -> `0.1.0.dev26` with one new internal wheel. The other 76 exact
documents change only in their mechanical `implementation_version` bump; no
scientific callable, document contract or test of theirs changes. The full
gate re-ran clean: 1128 passed, 43 skipped.

## Decision requested from the expert

1. Whether the five identities and contracts are acceptable for their
   relations, in particular whether the negative-energy rejections and the
   H–H 0-d-scalar selector requirement are the right resolutions of the saved
   document-vs-implementation gaps, and whether the error-message restyle is
   acceptable.
2. Whether the H+–H and H–H2 leading-singleton output-axis wrapper (the
   saved source's `np.array([E])` convention, contradicting the saved
   document's boilerplate output-shape sentence) should remain the published
   contract, or whether a shape-normalizing successor is preferred.
3. Whether the H+–H exactly-zero 10 eV breakpoint (the source's strict-branch
   behavior) should remain the published contract.
4. Whether keeping the source's endpoint-clipping conventions as the
   published contract is acceptable, and whether the `validation_oracle_gap`
   residual (external atomic-physics reference unbound) is acceptable for a
   `pending_unapproved` development version.
5. Whether the withdrawal of KN1DPy's strict D1 qualification is correctly
   reflected by treating the replays as bounded historical evidence only.
