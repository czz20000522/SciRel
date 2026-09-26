# Candidate: r59 successor — KN1DPy Johnson-Hinnov hydrogen radiation diagnostics family (three task graphs)

Status: development candidate prepared for expert review. Nothing here is
expert approval, a trusted version, or a public release. The development
integration lives on branch `codex/kn1dpy-maxwellian-rate-intake` on top of
SciRel base `2d3a89c` (r58, dev30). This batch closes the radiation-diagnostics
composition that the r57 candidate explicitly deferred (r57 expert questions
#3 and #4).

## Incoming capability

One saved KN1DPy operator package, `原子氢JH-r系数B样条评价`, whose remaining
callables are the hydrogen line-radiation relations over the already-integrated
JH coefficient assets (source anchors as recorded by the saved bundle's own
extraction report; the raw source tree was not re-read):

1. `evaluate_lyman_alpha` (anchor `KN1DPy/jh_related/lyman_alpha.py:42-64`):
   the Lyman-alpha photon rate `A_Lyman[0] * (r02 + r12 * n0 / saha1) * saha2`
   and emissivity with the frozen factor `13.6057 * (0.25 - 1/9)` eV.
2. `evaluate_balmer_alpha` (anchor `KN1DPy/jh_related/balmer_alpha.py:40-64`):
   the Balmer-alpha photon rate `A_Balmer[0] * (r03 + r13 * n0 / saha1) * saha3`
   and emissivity with the same frozen factor.
3. `invert_balmer_alpha_to_ground_state` (anchor
   `KN1DPy/jh_related/N0_from_balmer_alpha.py:12-70`): the inversion of an
   observed Balmer-alpha emissivity into ground-state neutral density, n=3
   population, photon rate, ionization, recombination and net source.

The packaged payload producer (`create_jh_bscoef.py:11-248`) stays **deferred**:
it materializes coefficient data, and admitting that data as a SciRel artifact
is the still-open r57 expert decision (#3). All three relations consume the
caller-supplied `jh_payload` exactly like the r57 coefficient assets; no table
physics is claimed.

## Current SciRel capability

No baseline asset composes hydrogen line radiation from population and
coefficient assets, and the unpublished candidate pool has none. All three
incoming relations are therefore proposed as **new capabilities**, integrated
as task graphs over the bound SciRel assets (r57 JH r/s/alpha, r56 Saha) —
the composition the r57 deferral intended.

## Proposed dispositions and identities

- `scirel.diagnostics.hydrogen-jh-lyman-alpha-emission`, callable
  `solve_hydrogen_jh_lyman_alpha_emission(inputs=None, **kwargs)`,
  dependencies: hydrogen-jh-r-coefficient, hydrogen-saha-equilibrium-population.
- `scirel.diagnostics.hydrogen-jh-balmer-alpha-emission`, callable
  `solve_hydrogen_jh_balmer_alpha_emission(inputs=None, **kwargs)`,
  dependencies: hydrogen-jh-r-coefficient, hydrogen-saha-equilibrium-population.
- `scirel.diagnostics.hydrogen-jh-balmer-alpha-ground-state-inversion`, callable
  `solve_hydrogen_jh_balmer_alpha_ground_state_inversion(inputs=None, **kwargs)`,
  dependencies: hydrogen-jh-r/s/alpha-coefficient,
  hydrogen-saha-equilibrium-population.

Domain `diagnostics`: these are spectroscopic line-emission and inversion
diagnostics, not collision coefficients. The saved port names
(`density_m3`, `temperature_ev`, `n0_m3`, `balmer_alpha_w_m3`, `jh_payload`,
`no_null`) are preserved as the graph input ports; the frozen constants
(`1.602177e-19` C, `13.6057 * (0.25 - 1/9)` eV) and the saved operation order
are preserved bit for bit.

## Material scientific differences (documented in the exact documents)

1. **Composed domain narrowing (declared; r57 expert question #4).** The saved
   radiation callables admit any positive finite electron density and
   temperature; the bound r56 Saha asset enforces its documented `< 1e32`
   domain, so the graphs declare density and temperature in `(0, 1e32)`. `n0`
   is bounded `< 1e32` by the saved contract itself on both arms. On the
   shared domain the outputs are bit-identical (replay-verified); above `1e32`
   the graphs fail closed where the saved arm returns a value, and the replay
   tests witness that divergence explicitly.
2. **Exact eight-field payload validation (pre-review correction).** A
   read-only pre-review caught that the first draft validated only the fields
   each branch consumes, so a payload missing e.g. `A_Balmer` for the Lyman
   graph would have been accepted where the saved `_validate_payload` raises.
   The graphs now enforce the saved exact-field contract (field set, knots,
   order 4, 77-coefficient geometry, all-fields finiteness) before any
   evaluation, through a shared `scirel._validation.validate_jh_payload` that
   reproduces the saved messages; both-arm counterexamples are pinned in the
   replay tests.
3. **Finiteness-only output gate (pre-review correction).** The same
   pre-review caught that the first draft rejected nonpositive photon rates,
   while the saved branch gates finiteness only: `A[0] = 0` returns zero rates
   (no emission) and a negative `A[0]` returns negative values on the saved
   arm. The graphs keep that semantics exactly, the exact documents declare
   it, and the zero-coefficient case is pinned bit-for-bit on both replay
   arms. The inversion keeps its strict-positive observed-emissivity input, so
   its recovered photon rate is strictly positive as saved.
4. **The saved Lyman energy factor is preserved, not repaired.** The saved
   implementation multiplies BOTH line photon rates by the n=3 -> 2 photon
   energy `13.6057 * (0.25 - 1/9)` eV, so the returned Lyman emissivity
   carries that factor rather than the physical n=1 -> 2 energy. The photon
   rate is unaffected. Whether a successor should repair the Lyman factor is
   an open expert-review question (new in this batch).
5. **No repair anywhere in this batch.** The s/alpha density-semantics split of
   the r57 assets carries into the returned ionization/recombination pair
   unchanged, the r/alpha sentinel overwrite is consumed as-is, and error
   messages from the bound assets propagate verbatim.

## Evidence

Source-free maintained tests (24 direct graph tests + doc-catalog engineering
tests; per-file counts `pytest --collect-only`-verified at freeze time)
establish each relation against an independent recomputation from the bound
SciRel assets with the saved operation order (bit-exact `assert_array_equal`),
the frozen constants, the channel/level selection, the dependency-binding
witness through the declared asset loader, the round-trip recovery of a known
`n0` through the forward Balmer graph, the s/alpha density-semantics split in
the returned source terms, and the full composed-domain and payload failure
contracts. The environment-gated replays pin the saved implementation by
SHA-256 (`253cda22…`) and reproduce the saved composition bit for bit on the
packaged coefficient payload — all six inversion fields, both forward lines on
three profile shapes — plus the shared rejection behavior, the declared
above-1e32 divergence, and the zero-coefficient parity case. The
failing-regression-first sequence is demonstrated by collection failure when
the new modules are absent.

Evidence ceiling: KN1DPy's strict D1 qualification is withdrawn and the bundle
sits in the re-review archive, so the replays are bounded historical
development comparison only. The coefficient and Einstein tables are
caller-supplied data here (the packaged payload producer stays deferred), so
no table physics is claimed; no test establishes any table against an external
atomic-physics reference (the saved package records that residual as
`validation_oracle_gap`).

## Public API and dependency impact

Three new public callables, exported from `scirel.diagnostics` and the root
namespace; three new exact documents (kind `task_graph`, the first graphs in
the diagnostics domain); one new shared validation helper in
`scirel._validation` (contract-identical to the r57 s-asset copy, which is
untouched); four new `tests/_review_bindings.py` operator entries (additive).
Development version moves `0.1.0.dev30` -> `0.1.0.dev31` with one new internal
wheel. The other 96 exact documents change only in their mechanical
`implementation_version` bump; no scientific callable, document contract or
test of theirs changes.

## Decision requested from the expert

1. Whether the three task-graph identities, the preserved saved operation
   order, and the declared composed-domain narrowing (`< 1e32` via the bound
   Saha asset) are acceptable (r57 question #4 resolution path).
2. Whether the saved Lyman emissivity energy factor (the n=3 -> 2 energy
   applied to the Lyman line) is the intended published contract or should be
   repaired by a successor (would change emissivity outputs, not photon
   rates, and require new evidence).
3. Whether the exact-field payload contract enforcement (including unused
   fields) and the finiteness-only output gate faithfully reflect the saved
   contract, or whether the published contract should diverge (e.g. reject
   nonpositive Einstein coefficients).
4. Whether the packaged JH coefficient payload should be admitted as a SciRel
   data artifact (carried over from r57 question #3), which would unblock a
   packaged payload producer and let these diagnostics run against real data.
5. Whether treating the replays as bounded historical evidence only (strict
   D1 withdrawn) remains the correct reflection of the source's qualification
   status.
