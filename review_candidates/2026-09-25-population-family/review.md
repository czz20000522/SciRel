# Candidate document: KN1DPy atomic-hydrogen population family

Status: development candidate prepared for expert review. Nothing here is
expert approval, a trusted version, or a public release. The development
integration lives on branch `codex/kn1dpy-maxwellian-rate-intake` on top of
SciRel base `7222f2b584e368c7399182f6227117930005f9d8` (r55).

## Incoming capability

Three saved KN1DPy operators of the atomic-hydrogen population-data family:

1. `Janev电子碰撞电离率` (source anchors `KN1DPy/sigma/sigmav_ion_h0.py:1-22`
   and `sigmav_ion_hh.py:1-27`, shared evaluation `poly.py:1-10`): the
   Maxwellian electron-impact ionization rate coefficient for two declared
   target species (H, H2), each a temperature-only nine-coefficient
   logarithmic polynomial clipped to [0.1, 2.01e4] eV.
2. `原子氢1s辐射复合速率` (source anchor `KN1DPy/sigma/sigmav_rec_h1s.py:3-25`,
   caller `kinetic_h.py:862,867-881`): the H+ + e -> H(1s) + hv radiative
   recombination rate coefficient, a Storey-type analytic form with the
   saved source's frozen constants (Ry = 13.58 eV, A_nl = 3.92, x_nl = 0.35,
   n = 1).
3. `原子氢Saha平衡人口密度` (source anchor
   `KN1DPy/jh_related/nh_saha.py:25-46`): the Saha equilibrium population
   density of principal level n, closed form with frozen constants
   (Saha 3.310e-28, chi = 13.6057 eV), exposing only the scientific branch of
   the source's sentinel-filled computation.

## Current SciRel capability

The collisions domain holds the Maxwellian relative-speed rate average, the
momentum scales, the relativistic Bessel closure and the hydrogen collision
data integrated in r49–r54 (CX, elastic, COLLRAD ionization, dissociation).
No baseline asset evaluates a temperature-only ionization or radiative-
recombination rate, or an equilibrium population density. The unpublished
candidate pool has none either. All three are therefore proposed as **new
capabilities**; no reuse, variant, duplicate or merge applies.

## Proposed dispositions and identities

- `scirel.collisions.janev-electron-impact-ionization-rate-coefficient`,
  callable `evaluate_janev_electron_impact_ionization_rate(
  electron_temperature_ev, target_species)` — species enum {"H", "H2"} kept
  as the saved source's declared dispatch (the two branches are different
  physical systems and disagree numerically).
- `scirel.collisions.atomic-hydrogen-1s-radiative-recombination-rate-coefficient`,
  callable `evaluate_atomic_hydrogen_1s_radiative_recombination_rate(
  electron_temperature_ev)` — ground state only, as saved.
- `scirel.kinetic.hydrogen-saha-equilibrium-population`, callable
  `evaluate_h_saha_equilibrium_population(electron_density_m3,
  electron_temperature_ev, principal_level)` — placed in the `kinetic`
  domain because it is an equilibrium population (m^-3), not a rate
  coefficient.

## Material scientific differences (all documented in the exact documents)

1. **Janev leaf, nonpositive-temperature rejection.** The saved document
   declares a positive temperature; the saved implementation folded the
   temperature and species checks into one generic error and silently clipped
   nonpositive values into the fit. The successor rejects a nonpositive
   temperature with a message naming the quantity, and rejects undeclared
   species values with a message naming the enum.
2. **Recombination leaf, nonpositive-temperature rejection.** Same
   declared-vs-implemented gap and same resolution; the frozen constants and
   closed form are kept bit for bit.
3. **Saha leaf, no repair.** The saved formal implementation already enforced
   its declared contract (scientific-branch-only exposure so the source's
   1e32 sentinel is never promoted to data, one-dimensional paired inputs,
   positive finite domain below 1e32, scalar integer level >= 1, finite
   positive result). The contract is reproduced bit for bit. The saved
   document's boilerplate ("scalar or profile array") is broader than the
   implementation's one-dimensional contract; the discrepancy is kept in
   favor of the implementation and recorded as an open expert-review
   question.
4. **Error messages** name the quantity, consistent with the maintained
   library's failure style. No existing numerical assertion is weakened.

## Evidence

Source-free maintained tests (32 total, `pytest --collect-only` verified:
21 direct + 11 environment-gated replay; per-file counts in the README
inventory table) establish each relation against an independent evaluation of
its frozen constants/coefficients (rtol 1e-12/1e-15), the domain clipping,
the input and failure contracts including the repairs, the species
distinction, and the Saha level scaling. The environment-gated replays pin
each saved implementation by SHA-256 (`ff9b5f5c…`, `ad71a46c…`, `38fa28ac…`)
and reproduce the saved arithmetic exactly, including repair witnesses for
the two rate leaves and exact agreement on the Saha leaf's rejection
behavior. The failing-regression-first sequence was demonstrated: with the
three new modules removed, the six new test files fail collection with
6 ImportErrors, and pass (32) once restored. One example-level defect was
caught during bring-up: a drafted Saha assertion guessed that level-2
populations exceed level-1 populations on cold inputs; the actual relation
suppresses level 2 there, and both the direct test and the exact-document
example were rewritten to assert the oracle equality instead of the wrong
monotonicity guess. Numerical details and gates are in
`docs/evaluations/intake-2026-09-25-population-family.md`.

Evidence ceiling: KN1DPy's strict D1 qualification is withdrawn and the bundle
sits in the re-review archive, so the replays are bounded historical
development comparison only. No test establishes any fit against an external
atomic-physics reference (the saved package records that residual as
`validation_oracle_gap`); the source-project correctness outside the compared
domain is not claimed.

## Public API and dependency impact

Three new public callables, exported from their domain packages and the root
namespace; three new exact documents; development version moves
`0.1.0.dev27` -> `0.1.0.dev28` with one new internal wheel. The other 90 exact
documents change only in their mechanical `implementation_version` bump; no
scientific callable, document contract or test of theirs changes. The full
gate re-ran clean: 1241 passed, 43 skipped.

## Decision requested from the expert

1. Whether the three identities and contracts are acceptable for their
   relations, in particular whether the two nonpositive-temperature
   rejections are the right resolution of the saved document-vs-implementation
   gaps, and whether the error-message restyle is acceptable.
2. Whether the Janev leaf's closed two-species enum ({"H", "H2"}) should
   remain the published contract, or whether the species should be split into
   separate assets.
3. Whether the Saha leaf's one-dimensional paired-sample contract (the saved
   implementation's behavior, contradicting the saved document's boilerplate)
   should remain the published contract.
4. Whether keeping the source's endpoint-clipping conventions as the
   published contract is acceptable, and whether the `validation_oracle_gap`
   residual (external atomic-physics reference unbound) is acceptable for a
   `pending_unapproved` development version.
5. Whether the withdrawal of KN1DPy's strict D1 qualification is correctly
   reflected by treating the replays as bounded historical evidence only.
