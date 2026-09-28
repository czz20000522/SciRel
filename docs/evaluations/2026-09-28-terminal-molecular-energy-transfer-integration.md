# KN1DPy terminal molecular energy-transfer development integration

Status: development candidate for expert review, not a qualified whole-source
D1 intake, expert approval or public release. SciRel comparison base:
`cb39500`; the clean intake snapshot is `647d5db` and remains
`pending_unapproved`. Its latest frozen review records an empty qualified D1
delivery root. The saved KN1DPy bundle supports bounded historical comparison
only.

## Relationship and disposition

The saved terminal H2 relation consumes a caller-owned `(nvr,nvx,nx)`
distribution and signed Boltzmann RHS, a signed external molecular source,
normalized velocity nodes, a hydrogen-mass factor, explicit thermal speed and
radial/axial quadrature. It returns loss, thermal-energy, axial-momentum and
total-energy transfer profiles. SciRel has a separate RHS assembly callable,
but this reduction does not invoke it or bind a particular RHS producer. No
existing public relation returns these four moments; this is a new leaf
relation with no callable dependency.

On tested finite carriers, the saved centered-moment decomposition of total
energy transfer agrees with an independent raw RHS energy integral of
`(vr^2+vx^2)*RHS`. Varying the external molecular source changes loss only;
it cancels from total transfer in exact arithmetic. The saved `operator.md`
describes a two-dimensional cylindrical weight, a scalar/profile RHS and an
incompatible-shape example; the callable instead requires one-dimensional
radial and axial weights and a signed RHS matching the distribution shape.
The source's `momentum_transfer_rate_profile_n_m2` name labels N/m^2, while a
volumetric reading of the RHS may imply another dimension. That physical
unit and absolute normalization remain open for expert review. The maintained
real-numeric contract rejects boolean and numeric-string coercions accepted
by the saved implementation; finite real arithmetic keeps source order. The
saved implementation SHA-256 is
`da8da87c2030fadcb2c21cd7ae064398dbf91aeb461a591d11a641ccdc5b44b3`.

## Evidence and limits

Thirteen direct tests passed. They cover independent centered and raw RHS
moments, signed RHS and external source, external-source variation, zero
quadrature cells with positive density, non-real input rejection, one empty
spatial slice and non-finite output rejection. Three optional SHA-gated
saved-arm replays passed: ordinary and zero-weight finite carriers match
exactly, and a boolean-weight witness distinguishes the maintained failure
contract. All 61 exact documents passed runtime-signature and executable-
example validation. The first worktree `affected` run exposed a stale
complete-catalog negative fixture at the new included count; the fixture was
bound to the declared total of 108 and its two targeted tests passed. The
subsequent `affected` gate selected this asset, both direct test files, the
public export and the asset-document/check-script contracts: 101 passed and
3 optional saved-root replays skipped. The catalog target is
`partial: 61/108`.

These checks do not establish the upstream terminal distribution or RHS,
absolute source units, full KN1D terminal diagnostics, whole-source D1
qualification, expert approval or public distribution licensing. No wheel or
release was built.
