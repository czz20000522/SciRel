# Candidate document: KN1DPy Johnson-Hinnov coefficient B-spline family

Status: development candidate prepared for expert review. Nothing here is
expert approval, a trusted version, or a public release. The development
integration lives on branch `codex/kn1dpy-maxwellian-rate-intake` on top of
SciRel base `93bb7cc` (r56).

## Incoming capability

One saved KN1DPy operator package, `原子氢JH-r系数B样条评价`, whose three
coefficient-evaluation callables form the Johnson-Hinnov hydrogen
coefficient family (source anchors as recorded by the saved bundle's own
extraction report; the raw source tree was not re-read):

1. `evaluate_h_jh_r_coefficient` (anchor `KN1DPy/jh_related/jhr_coef.py:12-66`,
   payload anchor `common/JH_Coef.py:5-29`): the r coefficient for principal
   levels 2-6 and ion channels {0, 1}, a cubic B-spline over
   `(log Te, log n)` evaluated on an explicitly passed payload (knots, order,
   `(n, 2, 5)` log-space tensor) with the source's endpoint clipping.
2. `evaluate_h_jh_s_coefficient` (anchor `KN1DPy/jh_related/jhs_coef.py:24-60`):
   the s coefficient, same spline form, reading `LogS_BSCoef` from an
   exact-field validated payload.
3. `evaluate_h_jh_alpha_coefficient` (anchor
   `KN1DPy/jh_related/jhalpha_coef.py:10-64`): the alpha (recombination)
   coefficient, same spline form, reading `LogAlpha_BSCoef`.

## Current SciRel capability

The collisions domain holds the hydrogen collision-data families integrated
in r49-r56 (CX, elastic, COLLRAD, dissociation, Janev ionization, Storey
recombination, Saha population) plus the Maxwellian average and momentum
scales. No baseline asset evaluates a coefficient through a caller-supplied
B-spline payload, and the unpublished candidate pool has none either. All
three incoming leaves are therefore proposed as **new capabilities**. The
package's internal Saha relation is already integrated (r56,
`scirel.kinetic.hydrogen-saha-equilibrium-population`) and is not re-added.

## Proposed dispositions and identities

- `scirel.collisions.hydrogen-jh-r-coefficient`, callable
  `evaluate_h_jh_r_coefficient(density_m3, temperature_ev, ion,
  principal_level, density_knots, temperature_knots, spline_order,
  log_r_bscoef, no_null=1)`
- `scirel.collisions.hydrogen-jh-s-coefficient`, callable
  `evaluate_h_jh_s_coefficient(density_m3, temperature_ev, jh_payload,
  no_null=1)`
- `scirel.collisions.hydrogen-jh-alpha-coefficient`, callable
  `evaluate_h_jh_alpha_coefficient(density_m3, temperature_ev, jh_payload,
  no_null=1)`

All in the `collisions` domain: each is a hydrogen collision/radiation
rate-coefficient evaluation. The saved signatures are preserved exactly so
the two payload forms (explicit r tensor vs whole-payload S/alpha) and the
`no_null=1` fail-closed branch selector remain the published contracts.

## Material scientific differences (documented in the exact documents)

1. **The `no_null=1` density overwrite (r and alpha).** The raw source
   initializes `result = Density; result[:] = 1e32` before taking the
   logarithm (r: `jhr_coef.py:42-43`; alpha likewise, as documented by the
   saved formal implementation), so on the admitted branch the spline's
   density coordinate is the clipped null sentinel and the output does not
   depend on the caller's density values beyond shape and validation. The
   saved formal implementation deliberately preserved this observable
   behavior; this integration preserves it too, asserts it as a witness
   test, and records it as an **open expert-review question**: is this the
   intended published contract, or a source defect that a successor should
   repair by consuming density? The sibling s branch consumes density, so
   the split is real and testable on both arms.
2. **Input immutability (alpha).** The saved implementation guarantees the
   caller's arrays are never mutated despite the internal overwrite; the
   test suite asserts this on both arms.
3. **Payload validation (s and alpha).** The exact field set, source cubic
   order 4, and the 77-coefficient knot geometry are enforced before any
   evaluation, as saved.
4. **No repair anywhere in this batch.** Unlike the r56 rate leaves, no
   saved document/implementation gap was found that a repair could close:
   each saved formal implementation already enforces its declared contract.
   Error messages are preserved verbatim.

## Evidence

Source-free maintained tests (30 total, `pytest --collect-only` verified:
direct 7 + 5 + 6 = 18, replay 4 + 4 + 4 = 12) establish each relation
against an independent FITPACK evaluation of the same spline
(`RectBivariateSpline.ev` at the clipped coordinates, rtol 1e-12), the
endpoint clipping, the channel selection (r), the density-dependence witness
(s) / density-independence and input-immutability witnesses (r, alpha), the
payload validation contract, and the fail-closed rejections. The
environment-gated replays pin the saved implementation by SHA-256
(`253cda22…`) and reproduce its arithmetic exactly — including all
(ion, level) channels of the packaged coefficient payload for r — with
rejection-behavior agreement witnesses. The failing-regression-first
sequence was demonstrated: with the three new modules removed, the six new
test files fail collection with 6 ImportErrors, and pass (30) once
restored. Numerical details and gates are in
`docs/evaluations/intake-2026-09-25-jh-coefficients.md`.

Evidence ceiling: KN1DPy's strict D1 qualification is withdrawn and the
bundle sits in the re-review archive, so the replays are bounded historical
development comparison only. The coefficient tables themselves are
caller-supplied data here (the packaged payload producer is deferred), so
no table physics is claimed; no test establishes any table against an
external atomic-physics reference (the saved package records that residual
as `validation_oracle_gap`).

## Public API and dependency impact

Three new public callables, exported from `scirel.collisions` and the root
namespace; three new exact documents; development version moves
`0.1.0.dev28` -> `0.1.0.dev29` with one new internal wheel. The other 93
exact documents change only in their mechanical `implementation_version`
bump; no scientific callable, document contract or test of theirs changes.

## Decision requested from the expert

1. Whether the three identities and contracts are acceptable for their
   relations, in particular the preserved-rather-than-repaired
   `no_null=1` density overwrite in the r and alpha branches: is that the
   intended published contract, or should a successor repair the relations
   to consume the caller's density (which would change outputs and require
   new evidence)?
2. Whether the two payload forms (explicit knots/tensor for r; whole-payload
   mapping for s and alpha) may coexist as the published contracts, or
   whether the family should be normalized to one form.
3. Whether the packaged JH coefficient payload (77-coefficient cubic
   geometry, Einstein A vectors) should eventually be admitted as a SciRel
   data artifact so the deferred radiation diagnostics can be composed
   against real data, or whether the relations must stay data-free.
4. Whether the domain-boundary difference between the saved package's
   internal Saha copy (positive finite only) and the integrated r56 Saha
   asset (positive finite below 1e32) needs reconciliation before the
   radiation diagnostics batch composes them.
5. Whether treating the replays as bounded historical evidence only
   (strict D1 withdrawn) remains the correct reflection of the source's
   qualification status.
