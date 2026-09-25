# Candidate document: KN1DPy Maxwellian relative-speed rate average

Status: development candidate prepared for expert review. Nothing here is
expert approval, a trusted version, or a public release. The development
integration lives on branch `codex/kn1dpy-maxwellian-rate-intake` on top of
SciRel base `465cd8a208579e89cc4ebbd583abad2c218673c1`.

## Incoming capability

The saved KN1DPy operator `Maxwellian相对速度速率平均` (source anchor
`KN1DPy/make_sigmav.py:13-57`) computes an energy-resolved rate coefficient
`<sigma v>`: a monoenergetic particle directed along the axial velocity axis is
averaged, through a caller-supplied cross section, against a discretized
Maxwellian target on a cylindrical `(vr, vx)` velocity mesh with
caller-supplied cell volumes. The collision energy is formed with the particle
mass, the saved source's convention, not the reduced mass. Its saved single-node
consumer graph `粒子靶Maxwellian速率系数图` is an identity composition that
binds the N1 mesh-snapshot ports.

## Current SciRel capability

No baseline asset averages a cross section over relative speed. The nearest
relations differ in model, not in parameters: `bosch-hale-reactivity` is a
temperature-only analytic fusion reactivity fit; the collisions-domain Bessel
and momentum-scale leaves are definitions of other quantities. The unpublished
candidate pool (52 Pleiades units and two additional snapshots, snapshot
digest in `README.md`) has no collision-rate asset. The relation is therefore
proposed as a **new capability**, not a reuse, variant, or merge.

## Proposed disposition and identity

- Add `scirel.collisions.maxwellian-relative-speed-rate-average`, public
  callable `average_cross_section_over_maxwellian` in
  `scirel.collisions.maxwellian_relative_speed_rate_average`, keyword-only
  with the nine saved ports.
- Subsume the single-node consumer graph: its identity edges add no relation;
  its N1-snapshot port/state/failure policy is documented in the exact
  document and protected by a composition test. No SciRel TaskGraph asset is
  proposed for it.

## Material scientific differences (all documented in the exact document)

1. **Non-finite input rejection.** The saved document claims non-finite inputs
   fail closed, but the saved implementation checked neither finiteness of
   inputs nor of results: a NaN mesh point, mass, or temperature propagated
   silently. The SciRel successor rejects non-finite inputs by parameter name
   and rejects a non-representable rate, so the saved document's declared
   finite contract is actually true. This is a repair, not a source-behavior
   claim; the replay test includes the differential witness.
2. **Error messages.** The saved implementation raises two generic messages;
   the successor names the parameter, consistent with the maintained library's
   failure style. The rejection domain is otherwise unchanged.
3. **Calling convention.** Keyword-only ports (library convention); the saved
   signature was positional.
4. **Constants frozen.** `AMU_KG = 1.6726231e-27`,
   `ELEMENTARY_CHARGE_C = 1.602177e-19` are kept bit-compatible with the saved
   source so the replay reproduces its arithmetic; they are not current CODATA
   values.
5. Everything else — formula, normalization by the supplied volumes, volume
   proportionality invariance, collision-energy convention, shape/sign/
   positivity conditions — is preserved.

## Evidence

Source-free maintained tests (44) establish the relation against an
in-file independent loop-per-energy formulation (rtol 1e-14), the rest-beam
limit `<sigma v> -> sigma * vth * 2/sqrt(pi)` with monotone mesh convergence,
the cold-target limit `<sigma v> -> sigma(E_beam) * v_beam`, volume-scale
invariance, and the full input/failure/composition contracts. The
environment-gated replay pins the saved implementation by SHA-256 and
reproduces constant- and linear-sigma cases (rtol 1e-14) plus the repair
witness. The saved bundle's own extraction report records the historical
two-arm source-free replay against the KN1DPy source (maximum relative errors
7.8e-17 and 2.4e-16). Numerical details and gates are in
`docs/evaluations/intake-2026-09-25-kn1dpy-maxwellian-rate.md`.

Evidence ceiling: KN1DPy's strict D1 qualification is withdrawn and the bundle
sits in the re-review archive, so the replay is bounded historical development
comparison only. No test establishes that the particle-mass collision-energy
convention is physically correct, that any caller cross section or mesh is
valid, or that the source project behaves correctly outside the compared
domain.

## Public API and dependency impact

One new public callable, exported from `scirel.collisions` and the root
namespace; one new exact document; development version moves `0.1.0.dev18` ->
`0.1.0.dev19` with a rebuilt internal wheel (the r40 wheel is not reused). The
other 68 exact documents change only in their mechanical
`implementation_version` bump; no scientific callable, document contract, or
test of theirs changes. The affected-mode gate selected the new operator, the
public-surface and documentation gates, and the touched count assertions:
941 passed, 46 skipped.

## Decision requested from the expert

1. Whether `scirel.collisions.maxwellian-relative-speed-rate-average` is an
   acceptable identity and contract for this relation, in particular:
2. whether the two documented repairs (non-finite rejection, finite-output
   rejection) are the right resolutions of the saved document-vs-implementation
   gap, and whether the error-message restyle is acceptable;
3. whether the particle-mass collision-energy convention should remain the
   published contract (a reduced-mass variant is deliberately not provided);
4. whether subsuming the single-node consumer graph without a separate
   TaskGraph asset is acceptable; and
5. whether the withdrawal of KN1DPy's strict D1 qualification is correctly
   reflected by treating the replay as bounded historical evidence only.
