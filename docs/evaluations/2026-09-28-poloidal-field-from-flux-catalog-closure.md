# Poloidal field from flux catalog closure

Status: development catalog documentation, not new scientific admission,
expert approval or public release. SciRel comparison base: `3227f7a`.
The current implementation and direct tests were compared with the frozen
historical Pleiades mapping, pending intake candidate and the existing
2026-09-25 flux-convention audit. SciRel and intake implementation text
matched. Intake r81-v1 remains `pending_unapproved`; the qualified D1
delivery root was read-only checked and contained zero entries, including
hidden entries. No qualified D1 input was consumed.

`poloidal_field_from_flux` now has a current-version
`scirel.asset-document.v1` record. It interprets its input as
`psi = R A_phi`, applies discrete R-Z derivatives for `B_R` and `B_Z`, and
uses a stated rule at R=0. New direct regressions cover a nonuniform grid
with an analytic quadratic flux and the field response to a `2*pi` input
rescaling. These tests protect the operator's own numerical convention;
they do not authorize feeding a vacuum-field output labelled `Wb` into a
consumer requiring `Wb/rad`. That cross-asset public-unit boundary remains
for science-owner adjudication, as recorded in the earlier audit. No
scientific source or public API changed.

The selector regression retains the reduced Hall graph and outer kinetic
mirror Hall composition as reverse consumers. Catalog coverage is
`partial: 77/114`; structured callable comparison with the historical
52-entry ledger leaves 37 assets without exact documents. The isolated
worktree `pwsh ./scripts/check.ps1 -Mode affected` passed 79 tests, and the
main checkout `pwsh ./scripts/check.ps1 -Mode affected -BaseRef 3227f7a`
also passed 79. The reduced Hall graph's eight tests and outer composition's
two tests passed separately in the isolated worktree. The document suite
executed runtime signatures and examples for all 77 records. These checks
establish selected discrete identities and failure behavior, not arbitrary
derivative convergence, cross-asset flux normalization, expert approval or
distribution licensing. No wheel or release was built.
