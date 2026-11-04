# Ideal conductor boundary catalog closure

Status: development catalog documentation, not new scientific admission,
expert approval or public release. SciRel comparison base: `8b416d0`.
The maintained implementation and direct tests were compared with the
frozen historical Pleiades mapping and pending intake candidate. SciRel
and intake implementation text matched. Intake r81-v1 remains
`pending_unapproved`; the qualified D1 delivery root was read-only checked
and contained zero entries. No qualified D1 input was consumed.

`correct_ideal_conductor_boundary_flux` now has a current-version
`scirel.asset-document.v1` record. It samples an uncorrected field-flux
vector, solves for equivalent boundary-source currents using a truncated
SVD of the boundary Green matrix, and reports corrected field flux and
boundary residual. The cutoff retains singular values strictly above
`rcond` times the largest singular value. Rank truncation can leave a
nonzero residual. The implementation checks dimensions, but does not
establish the physical coupling `S @ Gbf = Gbb`. No scientific source or
public API changed.

A new direct regression scales the flux vector and both Green matrices by
`2*pi`: equivalent currents stay fixed while the flux corrections and
residual scale. Existing direct tests cover full-rank cancellation in one
sampling-consistent system, rank truncation and invalid negative `rcond`.
The selector regression retains the free-boundary anisotropic Picard graph
as a reverse consumer. Catalog coverage is `partial: 85/114`; structured
callable comparison with the historical 52-entry ledger finds 23 matches
and 29 assets without exact documents. The isolated worktree and main
checkout each passed 85 affected tests, with the latter using
`pwsh ./scripts/check.ps1 -Mode affected -BaseRef 8b416d0`. Runtime
signatures and examples executed for all 85 documents; the deterministic
catalog partition test passed.

This algebra does not validate caller geometry, the physical wall model or
consistent sampling and Green matrices. Scaling only some flux ports is not
a unit conversion. Existing vacuum-field `Wb` and equilibrium `Wb/rad`
labels still need science-owner adjudication before public cross-asset
wiring. Distribution licensing and expert recognition remain pending.
No wheel or release was built.
