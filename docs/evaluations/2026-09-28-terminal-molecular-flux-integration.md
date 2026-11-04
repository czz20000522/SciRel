# KN1DPy terminal molecular flux and velocity development integration

Status: development candidate for expert review, not a qualified whole-source
D1 intake, expert approval or public release. SciRel comparison base:
`2392b95`; the clean intake snapshot is `647d5db` and remains
`pending_unapproved`. Its latest frozen review records an empty qualified D1
delivery root. The saved KN1DPy bundle supports bounded historical comparison
only.

## Relationship and disposition

The saved terminal H2 relation returns axial flux and mean velocity from a
`(nvr,nvx,nx)` distribution, normalized `vx`, explicit thermal speed and
radial/axial quadrature. SciRel already has
`scirel.kinetic.axisymmetric-neutral-moments`, whose corresponding two fields
agree on a common positive-weight carrier. That nine-moment relation also
requires radial nodes, derives thermal speed from temperature and mass,
rejects zero volume weights and computes higher moments before returning.
The terminal relation is retained as a distinct input and failure variant;
its exact document binds no callable dependency on the nine-moment asset.

The saved `operator.md` gives generic restrictions on zero velocity nodes and
spatial spacing which the saved callable does not implement. Its example has
misaligned weights. The maintained exact document states the actual five
inputs, two output fields and zero-weight condition instead. On finite real
inputs, the per-cell matrix-vector and radial reduction order is unchanged.
The saved implementation accepts boolean and numeric-string coercions; the
maintained real-numeric contract rejects them before arithmetic. The source
file SHA-256 is
`73dfe7df71e537f35c69d9ac7470303501fb933c43eced6772e915498f873ea9`.

## Evidence and limits

Nine direct tests passed. They cover an independent per-cell reduction,
agreement with the existing nine-moment fields on the positive-weight
intersection, zero-weight acceptance, non-real input rejection, zero-density
rejection and non-finite output rejection. Three optional SHA-gated saved-arm
replays passed: ordinary and zero-weight finite carriers match exactly, and a
boolean-weight witness distinguishes the maintained failure contract.
The 58 exact documents passed runtime-signature and executable-example
validation. The worktree `affected` gate selected this asset, both direct
test files, the public export and the asset-document/check-script contracts:
94 passed and 3 optional saved-root replays skipped. After cherry-pick
`b921e40` and README count commit `d2fe74c`, the main checkout ran
`pwsh ./scripts/check.ps1 -Mode affected -BaseRef 2392b95`: 94 passed and
3 optional saved-root replays skipped. Setting `SCIREL_KN1DPY_REVIEW_ROOT`
and running the replay separately yielded 3 passed. The catalog target is
`partial: 58/105`.

These checks do not establish the upstream terminal distribution, full KN1D
terminal diagnostics, physical flux normalization, whole-source D1
qualification, expert approval or public distribution licensing. No wheel or
release was built.
