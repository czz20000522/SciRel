# Reduced Hall drift catalog closure

Status: development catalog documentation, not new scientific admission,
expert approval or public release. SciRel comparison base: `c9bb390`.
The maintained implementation and direct tests were compared with the frozen
historical Pleiades mapping and pending intake candidate. SciRel and intake
implementation text matched. Intake r81-v1 remains `pending_unapproved`;
the qualified D1 delivery root was read-only checked and contained zero
entries. No qualified D1 input was consumed.

`close_reduced_hall_drift` now has a current-version
`scirel.asset-document.v1` record. It projects gyrotropic pressure force
onto toroidal current, applies a density/field/mask-limited Hall drift, and
optionally solves a bounded local toroidal-inertia correction. New direct
regressions show that a zero Hall multiplier retains pressure-projection
current, bypassed inertia reports one update, and exhaustion of a one-step
inertia budget raises without returning a state. No scientific source or
public API changed.

The selector regression retains the reduced Hall graph and outer kinetic
mirror Hall composition as reverse consumers. Catalog coverage is
`partial: 79/114`; structured callable comparison with the historical
52-entry ledger finds 17 matches and 35 assets without exact documents.
The isolated worktree and main checkout each passed 83 affected tests, with
the latter using `pwsh ./scripts/check.ps1 -Mode affected -BaseRef c9bb390`.
The reduced Hall graph's eight tests and outer composition's two tests also
passed separately in the isolated worktree. Runtime signatures and examples
executed for all 79 documents.

These checks establish selected discrete pressure, Hall, mask and inertia
behaviors, not arbitrary two-fluid validity, equilibrium convergence or a
physical interpretation of low-density and weak-field cells. The graph's
feedback, terminal checks and cross-asset flux convention require separate
review. The vacuum-field `Wb` versus equilibrium `Wb/rad` connection remains
for science-owner adjudication. Distribution licensing and expert recognition
also remain pending. No wheel or release was built.
