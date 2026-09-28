# KN1DPy terminal molecular pressure and temperature development integration

Status: development candidate for expert review, not a qualified whole-source
D1 intake, expert approval or public release. SciRel comparison base:
`cacdb69`; the clean intake snapshot is `647d5db` and remains
`pending_unapproved`. Its latest frozen review records an empty qualified D1
delivery root. The saved KN1DPy bundle supports bounded historical comparison
only.

## Relationship and disposition

The saved terminal H2 relation returns centered pressure and temperature from
a `(nvr,nvx,nx)` distribution, normalized `vr`/`vx`, explicit hydrogen-mass
factor and thermal speed, and radial/axial quadrature. SciRel already has
`scirel.kinetic.axisymmetric-neutral-moments`; the two corresponding fields
agree on the common positive-weight carrier with matching thermal speed and
`molecularity=2`. The nine-moment relation derives thermal speed from
temperature and mass, rejects zero volume weights and computes stress and heat
moments. The terminal relation is retained as a distinct input and failure
variant, with no callable dependency on the nine-moment asset.

The saved `operator.md` contains generic monotonicity and spatial-spacing
restrictions that its callable does not implement, plus an example whose scalar
and weight shapes are invalid. The maintained exact document states the actual
seven inputs, two output fields and positive-density condition. The saved
implementation accepts boolean and numeric-string coercions; the maintained
real-numeric contract rejects them before arithmetic. On finite real inputs,
the per-cell matrix-vector, radial reduction and centered-moment order is
unchanged. The saved implementation SHA-256 is
`5574ec2415d1df7cddc373432f82553c23595b61620ce9689b093dc39c8a116a`.

## Evidence and limits

Eleven direct tests passed. They cover an independent centered second-moment
oracle, agreement with the existing nine-moment pressure and temperature on
the positive-weight intersection, zero-weight acceptance, non-real input
rejection, one empty spatial slice, and non-finite pressure rejection. Three
optional SHA-gated saved-arm replays passed: ordinary and zero-weight finite
carriers match exactly, and a boolean-weight witness distinguishes the
maintained failure contract. All 59 exact documents passed runtime-signature
and executable-example validation. The worktree `affected` gate selected this
asset, both direct test files, the public export and the asset-document/check
script contracts: 97 passed and 3 optional saved-root replays skipped. The
catalog target is `partial: 59/106`. After cherry-pick `91fc6a1`, evidence
record `7fe1ec2` and README count commit `932adb6`, the main checkout ran
`pwsh ./scripts/check.ps1 -Mode affected -BaseRef cacdb69`: 97 passed and
3 optional saved-root replays skipped. Setting `SCIREL_KN1DPY_REVIEW_ROOT`
and running the main-checkout replay separately yielded 3 passed.

These checks do not establish the upstream terminal distribution, full KN1D
terminal diagnostics, physical distribution normalization, whole-source D1
qualification, expert approval or public distribution licensing. No wheel or
release was built.
