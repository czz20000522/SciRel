# Grid mirror kinetic graph catalog closure

Status: development catalog documentation, not new scientific admission,
expert approval or public release. SciRel comparison base: `aa15a80`.
The current graph implementation, direct tests and historical Pleiades
mapping were compared with the pending intake candidate. Current SciRel and
intake implementation text matched. Intake r81-v1 remains
`pending_unapproved`; the qualified D1 delivery root was read-only checked
and contained zero entries, including hidden entries. No qualified D1 input
was consumed.

`solve_grid_mirror_kinetic_closure` now has a SciRel-versioned
`scirel.asset-document.v1` TaskGraph record. Its three direct dependencies
are the mirror end-loss operator, flux-profile interpolation operator and
mirror quasineutral TaskGraph. Six declared nodes and 73 data edges form a
DAG with no graph-level feedback; the endpoint and nested potential solvers
own their own bounded iterations. The graph maps nearest ordered grid rows
through a caller-owned flux coordinate, evaluates prescribed or independently
solved endpoint states, calls the nested local quasineutral closure, then
optionally masks selected top-level fields. Original moment fields, endpoint
diagnostics and pitch factors remain full-grid. The top-level electron
density is masked, correcting a contradictory constraint in the pending
candidate document.

New direct regressions cover prescribed endpoints with unbalanced end
current but a converged local charge closure, fixed-profile invariance under
a consistent positive psi rescaling, an unadjusted callback counterexample,
selective masking and failure propagation from both the endpoint and nested
graph. The selector confirms that a source change still selects the outer
kinetic mirror Hall composition. No scientific source or public API changed.
The historical graph YAML describes fixed full-grid reference profiles more
broadly than the actual one-dimensional endpoint plus two-dimensional nested
call chain supports; a supplied profile must work in both contexts.

Catalog coverage is `partial: 76/114`. A structured callable comparison
with the historical 52-entry ledger leaves 38 assets without exact documents.
All 76 documents passed runtime-signature and executable-example validation.
`pwsh ./scripts/check.ps1 -Mode affected` passed 84 tests in the isolated
worktree. In the main checkout, `pwsh ./scripts/check.ps1 -Mode affected
-BaseRef aa15a80` passed 91 tests, including a separate concurrent
documentation change; the outer composition's two direct tests also passed.
These checks support the selected grid, branch, coordinate, masking and
failure examples, not physical flux-convention equivalence, arbitrary
profile domains, expert approval or distribution licensing. No wheel or
release was built.
