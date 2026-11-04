# Kinetic mirror Hall graph catalog closure

Status: development catalog documentation, not new scientific admission,
expert approval or public release. SciRel comparison base: `31c656a`.
The maintained outer wrapper, two nested TaskGraph documents and direct
tests were compared with the frozen historical Pleiades mapping and pending
intake candidate. SciRel and intake implementation text matched. Intake
r81-v1 remains `pending_unapproved`; the qualified D1 delivery root was
read-only checked and contained zero entries. No qualified D1 input was
consumed.

`solve_kinetic_mirror_hall_equilibrium` now has a current-version
`scirel.asset-document.v1` TaskGraph record. The outer graph is an acyclic
binding of the grid mirror kinetic closure into the reduced Hall Picard
graph's `pressure_closure(B, psi)` port. It copies `kinetic_config`,
overrides its grid and current `B/psi` values, passes other Hall inputs
through and returns the Hall mapping unchanged. The outer wrapper owns no
feedback state; bounded flux feedback and optional local inertia remain in
the nested Hall graph. Child failures propagate, while successful outer
Picard exhaustion can return `converged=false`. No scientific source or
public API changed.

New direct regressions cover public wrapper binding and two actual nested
numerical runs. A radial-profile case uses manufactured `psi=R^2/2` and a
nonzero diagonal Green response. A second case combines two circular
filament vacuum sources, the mirror-plasma Green response and one active
plasma cell; selected terminal flux and off-source field increments are
compared with direct filament evaluations. The latter comparison uses a
10% finite-grid derivative tolerance and does not show grid convergence.
An existing kinetic child regression shows fixed-profile invariance only
under consistent `2*pi` rescaling of the interpolation coordinate; an
unadjusted psi-dependent callback is a counterexample.

Catalog coverage is `partial: 81/114`. Structured callable comparison with
the historical 52-entry ledger finds 19 matches and 33 assets without exact
documents. The isolated worktree's initial affected selection had one
outdated test-path count; after correcting that count, its selector suite
passed 63 tests. Its outer graph suite passed five tests and historical
direct suite passed two. The main checkout passed 82 affected tests using
`pwsh ./scripts/check.ps1 -Mode affected -BaseRef 31c656a` and separately
passed the two historical direct tests. Runtime signatures and examples
executed for all 81 documents, and the catalog builder's deterministic
partition test passed.

The wrapper does not check agreement between Hall ion mass/charge and
`kinetic_config`, convert flux coordinates, or certify caller profiles.
The kinetic child accepts a caller-consistent flux-profile coordinate, but
the Hall child supplies `psi=R A_phi` in `Wb/rad`, while vacuum-field public
documents still label psi as `Wb`. Direct public cross-asset wiring remains
for science-owner adjudication. These selected manufactured inputs do not
establish real-device validity or arbitrary convergence. Distribution
licensing and expert recognition remain pending. No wheel or release was
built.
