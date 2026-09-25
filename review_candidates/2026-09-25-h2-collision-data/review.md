# Candidate document: KN1DPy molecular-hydrogen charge-exchange pair

Status: development candidate prepared for expert review. Nothing here is
expert approval, a trusted version, or a public release. The development
integration lives on branch `codex/kn1dpy-maxwellian-rate-intake` on top of
SciRel base `8b8dd150fe5778da8bd88fdf9c66b05c37f2c954` (r50).

## Incoming capability

Two saved KN1DPy operators of the molecular-hydrogen collision-data family:

1. `分子氢电荷交换截面` (source anchor `KN1DPy/sigma/sigma_cx_hh.py:5-23` with
   `KN1DPy/sigma/poly.py:3-10`, direct caller `KN1DPy/kinetic_h2.py:1036-1049`):
   the H2 + H2+ charge-exchange cross section as a Janev nine-coefficient
   logarithmic polynomial, source-clipped to [0.1, 2.01e4] eV.
2. `分子氢电荷交换Maxwellian速率系数` (source anchor
   `KN1DPy/sigma/sigmav_cx_hh.py:5-95`, ledger N15 `EQ-N15-H2-CX-RATE`,
   direct caller `KN1DPy/kinetic_h2.py:1196-1206`, mesh evidence
   `KN1DPy/kinetic_mesh.py:137`): the H2 charge-exchange Maxwellian rate
   coefficient as a nine-by-nine bivariate logarithmic polynomial in log(T)
   and log(E), evaluated in the saved source's summation order after clipping
   both inputs to [0.1, 2.01e4] eV.

## Current SciRel capability

The collisions domain holds the Maxwellian relative-speed rate average, the
momentum scales, the relativistic Bessel closure and the r49 atomic-hydrogen
collision data (atomic CX cross section, atomic CX rate coefficient, COLLRAD
ionization). No baseline asset evaluates a molecular-hydrogen collision
coefficient. The unpublished candidate pool has none either. Both are
therefore proposed as **new capabilities**; no reuse, variant, duplicate or
merge applies.

## Proposed dispositions and identities

- `scirel.collisions.molecular-hydrogen-charge-exchange-cross-section`, public
  callable `evaluate_molecular_hydrogen_charge_exchange_cross_section(energy_ev)`
  in `scirel.collisions.molecular_hydrogen_charge_exchange_cross_section`.
- `scirel.collisions.molecular-hydrogen-charge-exchange-rate-coefficient`,
  public callable `evaluate_hydrogen2_charge_exchange_rate(temperature_ev,
  energy_ev)` in `scirel.collisions.hydrogen2_charge_exchange_rate`.

Relations kept distinct: the two H2 assets are sibling fits of one process,
not one relation — the rate-coefficient fit is a fit evaluation, not the
Maxwellian average of the cross section; the averaging relation remains
`maxwellian-relative-speed-rate-average` (composition test with the molecular
cross section included). The molecular fits differ from the r49 atomic fits as
physical systems: the disagreement is asserted numerically in both directions
(cross sections and rate coefficients on a shared grid).

## Material scientific differences (all documented in the exact documents)

1. **Cross section, negative-energy rejection.** The saved document declares
   nonnegative energies; the saved implementation silently clipped negatives
   to the 0.1 eV endpoint. The successor rejects them. In-domain values keep
   the declared endpoint clipping bit for bit.
2. **Rate coefficient, nonpositive-temperature and negative-energy rejection.**
   Same declared-vs-implemented gap and same resolution: reject; keep the
   clipping of in-domain values and the exact source summation order.
3. **Error messages** name the quantity, consistent with the maintained
   library's failure style. The rejection domain is otherwise unchanged, and
   no existing numerical assertion is weakened.

## Evidence

Source-free maintained tests (24 total: 17 direct + 7 environment-gated
replay) establish each relation against an independent evaluation in the
saved package's own oracle style (closed-form reevaluation for the
cross-section fit, polyval2d for the rate fit), the clipping contracts, the
full input/failure contracts including the repairs, the numerical distinction
from the atomic siblings, and the composition with the retained rate average.
The environment-gated replays pin each saved implementation by SHA-256
(`2be195e5…`, `8ca54201…`) and reproduce the saved arithmetic exactly,
including repair witnesses (the saved implementation clips a negative energy
or nonpositive temperature into the fit where the successors reject). The
failing-regression-first sequence was demonstrated: with the two new modules
removed, the four new test files fail collection with 4 ImportErrors, and
pass (22) once restored. The saved extraction ledger records ACCEPT_OPERATOR
for both. Numerical details and gates are in
`docs/evaluations/intake-2026-09-25-h2-collision-data.md`.

Evidence ceiling: KN1DPy's strict D1 qualification is withdrawn and the bundle
sits in the re-review archive, so the replays are bounded historical
development comparison only. No test establishes either fit against an
external atomic-physics reference (the saved package records that residual as
`validation_oracle_gap`); the source-project correctness outside the compared
domain is not claimed.

## Public API and dependency impact

Two new public callables, exported from `scirel.collisions` and the root
namespace; two new exact documents; development version moves
`0.1.0.dev24` -> `0.1.0.dev25` with one new internal wheel. The other 74 exact
documents change only in their mechanical `implementation_version` bump; no
scientific callable, document contract or test of theirs changes. The full
gate re-ran clean: 1081 passed, 43 skipped.

## Decision requested from the expert

1. Whether the two identities and contracts are acceptable for their
   relations, in particular whether the three documented repairs
   (negative energy x2, nonpositive temperature) are the right resolutions of
   the saved document-vs-implementation gaps, and whether the error-message
   restyle is acceptable.
2. Whether keeping the source's endpoint-clipping conventions as the
   published contract is acceptable, rather than rejecting out-of-range
   values.
3. Whether the molecular and atomic charge-exchange assets may stay separate
   sibling identities given that neither derives from the other, and whether
   the validation_oracle_gap residual (external atomic-physics reference
   unbound) is acceptable for a `pending_unapproved` development version.
4. Whether the withdrawal of KN1DPy's strict D1 qualification is correctly
   reflected by treating the replays as bounded historical evidence only.
