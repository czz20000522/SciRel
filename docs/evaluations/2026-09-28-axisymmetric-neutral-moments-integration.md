# KN1DPy axisymmetric neutral moments development integration

Status: development baseline candidate for expert review, not qualified
whole-source D1 intake, expert approval or public release. The comparison
base is SciRel `f23c1143036e90dc4e2f0381e168cb4f145d15b5`; the clean
intake snapshot is `647d5dbd36404bc5e76d934a875984787e789644`
(`pending_unapproved`). The qualified D1 delivery root was empty at the
start of this batch.

## Scientific boundary

The [exact document](../../catalog/examples/scirel.kinetic.axisymmetric-neutral-moments.json)
defines one leaf reduction from an H or H2 `(nvr, nvx, nx)` distribution and
caller-supplied cylindrical cell volumes to nine density, flow, pressure,
temperature, stress and heat-flux profiles. It does not construct a mesh,
normalize the caller's distribution or advance transport state. The saved
`sigma_zz = sigma_yy` identification and `source_default` zero-density
values remain explicit, unresolved expert questions. The default still
rejects nonpositive-density slices.

`isotope_mass_amu` is a historical parameter name: it multiplies the saved
hydrogen mass `1.6726231e-27 kg`, not the standard atomic mass unit. A direct
test composes the current cylindrical quadrature, shifted-Maxwellian seed and
this reduction through their actual volume and distribution ports. This is
an observed port composition, not a TaskGraph dependency or a compensated
Maxwellian claim.

## Source and failure differences

The read-only archive implementation at
`D1待重审历史产物/KN1DPy-631d0bf1/operators/轴对称中性分布矩归约/scientific_operator.py`
matched the intake SHA-256 pin
`02b58e9447e632d071877b15da871e07a5032654d6d79db8e2945dc8e3f9987e`.
With the isolated SciRel `src/` path asserted, three valid cases (default,
explicit quadrature and `source_default`) matched all nine saved outputs
with `assert_array_equal`. This is bounded historical comparison; it does
not restore the source project's strict D1 qualification.

The intake implementation cast boolean and numeric-string arrays to float,
discarded complex parts after emitting warnings, accepted boolean scalar
temperature/mass and noninteger molecularity, and could raise a raw
`ZeroDivisionError` when the derived mass denominator underflowed. SciRel
rejects those inputs under its declared real-array, scalar and finite-output
contracts. The accepted finite real-valued formula and the two saved
summation orders were retained. Regression additions failed first: the
initial type batch had 26 failures and one pass; the mixed-boolean and
derived-scale witnesses both failed before repair. Existing numerical
assertions and tolerances were retained.

## Verification boundary

- Source-free direct contract tests: 40 passed, including the quadrature and
  seed composition, the two empty-slice policies and strict quadrature
  reconstruction.
- `pwsh ./scripts/check.ps1 -Mode affected` selected six files and passed
  120 tests without full-suite fallback.
- All 28 exact documents passed source-runtime and executable-example
  validation. The catalog is a partial `28/75` development pilot at
  `0.1.0.dev5`.
- The release gate's stale static `24/71` counts were corrected to the
  current `28/75` document/asset union, and its maintained test passed.
  No release was executed or certified.

These observations establish a bounded discrete moment relation and valid
saved-point agreement. They do not settle whether the saved stress
identification, empty-slice defaults or distribution normalization are
appropriate in a larger neutral transport model. Licensing, expert review
and release remain pending.
