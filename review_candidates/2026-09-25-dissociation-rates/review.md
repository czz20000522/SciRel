# Candidate document: KN1DPy dissociation-rate family

Status: development candidate prepared for expert review. Nothing here is
expert approval, a trusted version, or a public release. The development
integration lives on branch `codex/kn1dpy-maxwellian-rate-intake` on top of
SciRel base `e3f2ebe559e57e35eff2e23170211377db24b0a8` (r53).

## Incoming capability

Nine saved KN1DPy operators of the hydrogen dissociation/recombination rate
family: the electron-impact channels of H2 (five leaves, source anchors in
`KN1DPy/sigma/sigmav_*.py` with caller evidence in `kinetic_h2.py:938-993`)
and of H2+ (four leaves, `sigmav_p_h1s_hp.py`, `sigmav_p_hn2_hp.py`,
`sigmav_h1s_hn_hp.py`, and a derived two-proton channel anchored at
`kinetic_h2.py:977-983`). All nine share one relation shape: a temperature-only
nine-coefficient logarithmic polynomial in log(T), evaluated in the saved
source's Horner order on the clipped domain [0.1, 2.01e4] eV and scaled by
1e-6 to m^3/s.

## Current SciRel capability

The collisions domain holds the Maxwellian relative-speed rate average, the
momentum scales, the relativistic Bessel closure, the r49 atomic-H collision
data (CX cross section, CX rate coefficient, COLLRAD ionization), the r51
molecular-H2 CX pair and the r53 elastic momentum-transfer family. No baseline
asset evaluates a dissociation or dissociative-recombination rate. The
unpublished candidate pool has none either. All nine are therefore proposed as
**new capabilities**; no reuse, variant, duplicate or merge applies.

## Proposed dispositions and identities

Nine sibling assets (IDs in the README inventory table), callables preserved
from the source names:
`evaluate_hydrogen2_h1s_h1s_dissociation_rate`,
`evaluate_hydrogen2_h1s_h2s_dissociation_rate`,
`evaluate_hydrogen2_h1s_hn3_dissociation_rate`,
`evaluate_hydrogen2_h2p_h2s_dissociation_rate`,
`evaluate_hydrogen2_p_h1s_dissociation_rate`,
`evaluate_h2_plus_two_proton_dissociation_rate`,
`evaluate_h2_plus_p_h1s_dissociation_rate`,
`evaluate_h2_plus_p_hn2_dissociation_rate`,
`evaluate_h2_plus_h1s_hn_dissociative_recombination_rate` — all in
`scirel.collisions`, exported from the root namespace.

The nine remain separate sibling identities: each channel is a physically
distinct rate with its own frozen coefficient table; none derives from
another (the two-proton leaf's anchor is a caller site, but the saved formal
leaf is still a standalone fit with its own coefficients).

## Material scientific differences (documented in every exact document)

1. **Nonpositive-temperature rejection (all nine).** Every saved document
   declares a positive temperature; every saved implementation silently
   clipped a nonpositive temperature into the fit domain. The successors
   reject it. In-domain values keep the declared endpoint clipping bit for
   bit. (The saved documents also carry an "energy must be nonnegative"
   boilerplate sentence although no energy port exists; the successor declares
   the temperature-only contract and does not invent an energy port.)
2. **Error messages** name the quantity, consistent with the maintained
   library's failure style. No existing numerical assertion is weakened.

## Evidence

Source-free maintained tests (81 total, `pytest --collect-only` verified:
54 direct + 27 environment-gated replay; 6 direct + 3 replay per asset)
establish each fit against an independent `polyval` evaluation of its frozen
coefficients (rtol 1e-12), the domain clipping, the scalar and
zero-dimensional contracts, and the repair. The environment-gated replays pin
each saved implementation by SHA-256 and reproduce the saved arithmetic
exactly — one- and two-dimensional grids, plus the repair witness (the saved
implementation returns the endpoint-clamped value for a nonpositive temperature
where the successor rejects). The failing-regression-first sequence was
demonstrated: with the nine new modules removed, the eighteen new test files
fail collection with 18 ImportErrors, and pass (81) once restored. Numerical
details and gates are in `docs/evaluations/intake-2026-09-25-dissociation-rates.md`.

Evidence ceiling: KN1DPy's strict D1 qualification is withdrawn and the bundle
sits in the re-review archive, so the replays are bounded historical
development comparison only. No test establishes any fit against an external
atomic-physics reference (the saved package records that residual as
`validation_oracle_gap`); the source-project correctness outside the compared
domain is not claimed.

## Public API and dependency impact

Nine new public callables, exported from `scirel.collisions` and the root
namespace; nine new exact documents; development version moves
`0.1.0.dev26` -> `0.1.0.dev27` with one new internal wheel. The other 81 exact
documents change only in their mechanical `implementation_version` bump; no
scientific callable, document contract or test of theirs changes. The full
gate re-ran clean: 1209 passed, 43 skipped.

## Decision requested from the expert

1. Whether the nine identities and the shared temperature-only contract are
   acceptable for their relations, in particular whether the
   nonpositive-temperature rejections are the right resolution of the saved
   document-vs-implementation gap, and whether the error-message restyle is
   acceptable.
2. Whether keeping the source's endpoint-clipping convention as the published
   contract is acceptable, rather than rejecting out-of-range values.
3. Whether the nine channel assets may stay separate sibling identities given
   that each has its own frozen coefficient table, and whether the
   `validation_oracle_gap` residual (external atomic-physics reference
   unbound) is acceptable for a `pending_unapproved` development version.
4. Whether the generated-from-template provenance (proposal includes the four
   generator scripts, coefficients extracted by float-repr round-trip) is
   acceptable as audit evidence for nine uniformly-shaped leaves.
5. Whether the withdrawal of KN1DPy's strict D1 qualification is correctly
   reflected by treating the replays as bounded historical evidence only.
