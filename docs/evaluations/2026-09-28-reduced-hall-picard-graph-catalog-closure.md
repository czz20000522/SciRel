# Reduced Hall Picard graph catalog closure

Status: development catalog documentation, not new scientific admission,
expert approval or public release. SciRel comparison base: `1daee38`.
The maintained graph, direct tests and three bound leaf documents were
compared with the frozen historical Pleiades mapping and pending intake
candidate. SciRel and intake implementation text matched. Intake r81-v1
remains `pending_unapproved`; the qualified D1 delivery root was read-only
checked and contained zero entries. No qualified D1 input was consumed.

`solve_reduced_hall_anisotropic_picard` now has a current-version
`scirel.asset-document.v1` TaskGraph record. Its ordinary dependencies are
the poloidal-field, reduced-Hall drift and Picard-flux leaves. One explicit
feedback contract owns a copy of evolving psi, prior raw cell currents,
iteration count and history; five feedback edges share that contract. Each
step evaluates field, caller pressure closure, Hall state and Green update
in order. The graph stops at its flux tolerance or maxiter, then reevaluates
field, closure, Hall state and raw cell currents at terminal psi. Outer
nonconvergence can return `converged=false`; local Hall inertia failure
raises instead. The terminal path does not repeat the iteration field-floor
or graph-level nonnegative-pressure checks. No scientific source or public
API changed.

A new manufactured Hall-disabled regression couples circular-filament
vacuum psi, the mirror-plasma Green response and one active plasma cell. It
compares the flux increment and off-source field against direct filament
responses on a finite grid. The existing two-step feedback test now asserts
the outer nonconvergence flag. The selector regression checks that changing
this TaskGraph selects the outer kinetic mirror Hall composition.

Catalog coverage is `partial: 80/114`. Structured callable comparison with
the historical 52-entry ledger finds 18 matches and 34 assets without exact
documents. The isolated worktree and main checkout each passed 85 affected
tests; the latter used `pwsh ./scripts/check.ps1 -Mode affected -BaseRef
1daee38`. The outer composition's two existing tests passed separately in
the isolated worktree. Runtime signatures and examples executed for all 80
documents; the catalog builder's deterministic partition test also passed.

These checks cover selected discrete feedback and one Hall-disabled Green
coupling, not arbitrary nonzero-Hall equilibria, caller pressure models or
convergence. Vacuum-field documents still label psi as `Wb`, while this
graph requires psi=R A_phi in `Wb/rad`; direct cross-asset wiring remains
for science-owner adjudication. Public distribution licensing and expert
recognition remain pending. No wheel or release was built.
