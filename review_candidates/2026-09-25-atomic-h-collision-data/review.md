# Candidate document: KN1DPy atomic-hydrogen collision data family

Status: development candidate prepared for expert review. Nothing here is
expert approval, a trusted version, or a public release. The development
integration lives on branch `codex/kn1dpy-maxwellian-rate-intake` on top of
SciRel base `dbb4385b2ec428c04c8706a484694d598ad14412` (r48).

## Incoming capability

Three saved KN1DPy operators of one relation family -- atomic-hydrogen
collision data for neutral kinetics:

1. `原子氢电荷交换截面` (source anchor `KN1DPy/sigma/sigma_cx_h0.py:7-32` with
   `KN1DPy/poly.py:3-10`): the H + H+ charge-exchange cross section as a Janev
   nine-coefficient logarithmic polynomial, with a Freeman--Jones analytic
   alternative branch, both source-clipped in energy.
2. `原子氢电荷交换Maxwellian速率系数` (source anchor
   `KN1DPy/sigma/sigmav_cx_h0.py:8-95`, ledger N25
   `EQ-N25-N4-H-CX-RATE`): the atomic-H charge-exchange Maxwellian rate
   coefficient as a nine-by-nine bivariate logarithmic polynomial in log(T)
   and log(E), evaluated in the saved source's summation order after clipping
   both inputs to [0.1, 2.01e4] eV.
3. `COLLRAD_H0电子碰撞电离率` (source anchor
   `KN1DPy/collrad_sigmav_ion_h0.py:16-217`, reachable from
   `KN1DPy/kinetic_h.py:841-855`): the COLLRAD (DEGAS-2) H0 Maxwellian-averaged
   electron-impact ionization rate by bilinear interpolation of log(rate) on a
   frozen 15x60 log(n)/log(T) table with endpoint clamping.

## Current SciRel capability

The collisions domain holds the Maxwellian relative-speed rate average (a
mesh-integration machinery, r41-r48), the momentum scales and the
relativistic Bessel closure. No baseline asset evaluates a hydrogen collision
cross section, rate coefficient or ionization rate. The unpublished candidate
pool (52 Pleiades units and two additional snapshots) has none either. All
three are therefore proposed as **new capabilities**; no reuse, variant,
duplicate or merge applies.

## Proposed dispositions and identities

- `scirel.collisions.atomic-hydrogen-charge-exchange-cross-section`, public
  callable `evaluate_atomic_hydrogen_charge_exchange_cross_section(energy_ev,
  freeman=False)` in `scirel.collisions.atomic_hydrogen_charge_exchange_cross_section`.
- `scirel.collisions.atomic-hydrogen-charge-exchange-rate-coefficient`, public
  callable `evaluate_atomic_hydrogen_charge_exchange_rate(temperature_ev,
  energy_ev)` in `scirel.collisions.atomic_hydrogen_charge_exchange_rate`.
- `scirel.collisions.collrad-h0-ionization-rate`, public callable
  `evaluate_collrad_h0_ionization_rate(electron_density_m3,
  electron_temperature_ev)` in `scirel.collisions.collrad_h0_ionization_rate`.

Relations kept distinct: (1) and (2) are sibling fits of one process, not one
relation -- (2) is a fit evaluation, not the Maxwellian average of (1), and
the averaging relation remains `maxwellian-relative-speed-rate-average`, whose
`cross_section_m2` port (1) can serve directly (composition test included).
(3) is a different process (electron impact) and dataset.

## Material scientific differences (all documented in the exact documents)

1. **Cross section, negative-energy rejection.** The saved document declares
   nonnegative energies; the saved implementation silently clipped negatives
   to the 0.1 eV endpoint. The successor rejects them. In-domain values keep
   the declared endpoint clipping bit for bit.
2. **Cross section, scalar branch selector.** The saved document declares a
   scalar `freeman` selector; the saved implementation reduced arrays with
   `np.any` (its own example even passed an array). The successor requires a
   scalar.
3. **Rate coefficient, nonpositive-temperature and negative-energy rejection.**
   Same declared-vs-implemented gap and same resolution: reject; keep the
   clipping of in-domain values and the exact source summation order.
4. **COLLRAD, shape contract.** The saved document declares the output shaped
   like the broadcast inputs; the saved implementation flattened everything to
   one dimension and compared flattened sizes only, silently accepting
   same-size differently-shaped arrays. The successor requires equal shapes
   and returns the input shape; one-dimensional values are unchanged bit for
   bit.
5. **Error messages** name the quantity, consistent with the maintained
   library's failure style. The rejection domain is otherwise unchanged, and
   no existing numerical assertion is weakened.
6. The COLLRAD table is carried bit for bit (verified by an array-equality
   probe against the saved implementation after a mechanical re-extraction of
   the table line, which corrected nine hand-transcription slips found by the
   same probe).

## Evidence

Source-free maintained tests (63 total: 21 direct + 4 environment-gated replay
per asset) establish each relation against an independent evaluation in the
saved package's own oracle style (polyval2d for the rate fit, geometric-mean
midpoint and grid anchors for the COLLRAD table, closed-form reevaluation for
both cross-section branches), the clipping contracts, the full input/failure
contracts including the repairs, and the composition with the retained rate
average. The environment-gated replays pin each saved implementation by
SHA-256 and reproduce the saved arithmetic exactly, including repair
witnesses (the saved implementation clips a negative energy / nonpositive
temperature into the fit, reduces an array selector, and flattens a
two-dimensional COLLRAD profile, where the successors reject or keep shape).
The saved extraction ledger records ACCEPT_OPERATOR for all three; the
COLLRAD row adds a source-runtime dataset validation (nine partitions,
max_rel 1.45e-14). Numerical details and gates are in
`docs/evaluations/intake-2026-09-25-atomic-h-collision-data.md`.

Evidence ceiling: KN1DPy's strict D1 qualification is withdrawn and the bundle
sits in the re-review archive, so the replays are bounded historical
development comparison only. No test establishes any of the three fits or the
COLLRAD table against an external atomic-physics reference (the saved package
records that residual as `validation_oracle_gap`); the source-project
correctness outside the compared domain is not claimed.

## Public API and dependency impact

Three new public callables, exported from `scirel.collisions` and the root
namespace; three new exact documents; development version moves
`0.1.0.dev23` -> `0.1.0.dev24` with one new internal wheel. The other 71 exact
documents change only in their mechanical `implementation_version` bump; no
scientific callable, document contract or test of theirs changes. The full
gate re-ran clean: 1059 passed, 43 skipped (the L1 replay root was configured,
so 9 historical replays run for real).

## Decision requested from the expert

1. Whether the three identities and contracts are acceptable for their
   relations, in particular whether the four documented repairs (negative
   energy x2, nonpositive temperature, scalar selector, COLLRAD shape) are the
   right resolutions of the saved document-vs-implementation gaps, and whether
   the error-message restyle is acceptable.
2. Whether keeping the source's endpoint-clipping conventions (silent endpoint
   repetition outside each fit/table range) as the published contract is
   acceptable, rather than rejecting out-of-range values.
3. Whether the nondecreasing paired-coordinate contract of the COLLRAD leaf
   (rejecting non-monotone sample sequences, the source's monotone-sweep
   semantics) should remain the published contract.
4. Whether the two charge-exchange assets may stay separate identities given
   that neither is derived from the other, and whether the COLLRAD
   validation_oracle_gap residual (external atomic-physics reference unbound)
   is acceptable for a `pending_unapproved` development version.
5. Whether the withdrawal of KN1DPy's strict D1 qualification is correctly
   reflected by treating the replays as bounded historical evidence only.
