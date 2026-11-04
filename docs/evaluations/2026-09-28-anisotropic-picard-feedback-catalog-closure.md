# Anisotropic Picard feedback catalog closure

Status: development catalog documentation, not new scientific admission,
expert approval or public release. SciRel comparison base: `d420c22`.
The current implementation and direct tests were compared with the
historical Pleiades development mapping, pending intake candidate and
existing flux-convention audit. SciRel and intake source text matched
after LF normalization. Intake r81-v1 remains `pending_unapproved`;
the qualified D1 delivery root was recently checked read-only and
contained zero entries. No qualified D1 input was consumed.

`update_anisotropic_picard_flux` now has a current-version
`scirel.asset-document.v1` record. It clips current density with an
optional exact boolean mask, converts it to cell currents on a uniform
R-Z tensor grid, relaxes against the old current vector and projects
the result through caller-supplied Green matrices. New direct checks
show that `relax=1` retains the old vector while reporting raw plasma
currents, and that `currents_old=None` initializes zero state. Prior
numerical assertions and tolerances remain intact. No scientific
source or public API changed.

The pending document claimed an off-source circular-filament comparison
that the current direct tests do not contain. That claim was removed.
The function's `psi_vac` and `g_psi` use the field chain's `Wb/rad`
convention; public vacuum-field outputs labelled `Wb` are not thereby
approved for direct wiring. The selector regression retains the
free-boundary Picard graph as a reverse consumer.

Catalog coverage is `partial: 89/114`; structured public-callable
comparison with the 52-entry historical ledger finds 27 matches and 25
assets without exact documents. All 89 runtime signatures and examples
validated in the isolated worktree. The isolated worktree and main
checkout each passed 97 affected tests; the latter used
`pwsh ./scripts/check.ps1 -Mode affected -BaseRef d420c22`.
These checks do not establish physical Green normalization, flux-unit
conversion, equilibrium convergence, expert approval or distribution
licensing. No wheel or release was built.
