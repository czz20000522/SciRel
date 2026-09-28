# KN1DPy terminal molecular heat-flux development integration

Status: development candidate for expert review, not a qualified whole-source
D1 intake, expert approval or public release. SciRel comparison base:
`2b1351d`; the clean intake snapshot is `647d5db` and remains
`pending_unapproved`. Its latest frozen review records an empty qualified D1
delivery root. The saved KN1DPy bundle supports bounded historical comparison
only.

## Relationship and disposition

The saved terminal H2 relation returns centered random and total axial energy
flux from a `(nvr,nvx,nx)` distribution, normalized velocity nodes, explicit
hydrogen-mass factor and thermal speed, and radial/axial quadrature. SciRel's
`scirel.kinetic.axisymmetric-neutral-moments` computes the random field on
the positive-weight intersection with matching thermal speed and
`molecularity=2`; the terminal relation additionally returns total flux,
allows zero quadrature cells with positive density and does not expose the
intermediate pressure or stress. It is retained as a distinct input, output
and failure variant, with no callable dependency on the nine-moment asset.

The source's total-flux pressure/stress decomposition also agrees on tested
finite carriers with an independent raw third-moment integral of
`(vr^2+vx^2)*vx*f`. The saved `operator.md` labels the energy-flux outputs
as area and gives an incompatible-shape example; the maintained exact
document states the actual W/m^2 output fields and aligned input shapes.
The saved implementation accepts boolean and numeric-string coercions; the
maintained real-numeric contract rejects them before arithmetic. On finite
real inputs the source reduction and decomposition order is unchanged. The
saved implementation SHA-256 is
`46e9c00fb9cce1f2d6e82efa83a176a91500ea06c00de4f224aa2a337bdf7aeb`.

## Evidence and limits

Eleven direct tests passed. They cover independent centered and raw energy
flux oracles, agreement with the existing nine-moment random flux on the
positive-weight intersection, zero-weight acceptance, non-real input
rejection, one empty spatial slice and non-finite output rejection. Three
optional SHA-gated saved-arm replays passed: ordinary and zero-weight finite
carriers match exactly, and a boolean-weight witness distinguishes the
maintained failure contract. All 60 exact documents passed runtime-signature
and executable-example validation. The worktree `affected` gate selected this
asset, both direct test files, the public export and the asset-document/check
script contracts: 98 passed and 3 optional saved-root replays skipped. The
catalog target is `partial: 60/107`. After cherry-pick `2a503e2`, evidence
record `f609dd3` and README count commit `a97846e`, the main checkout ran
`pwsh ./scripts/check.ps1 -Mode affected -BaseRef 2b1351d`: 98 passed and
3 optional saved-root replays skipped. Setting `SCIREL_KN1DPY_REVIEW_ROOT`
and running the main-checkout replay separately yielded 3 passed.

These checks do not establish the upstream terminal distribution, full KN1D
terminal diagnostics, physical distribution normalization, whole-source D1
qualification, expert approval or public distribution licensing. No wheel or
release was built.
