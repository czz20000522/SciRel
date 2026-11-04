# Free-boundary anisotropic Picard graph catalog closure

Status: development catalog documentation, not new scientific admission,
expert approval or public release. SciRel comparison base: `9d56a2f`.
The maintained graph, historical Pleiades development mapping and YAML,
pending intake candidate, direct graph tests and five dependency records
were compared. SciRel and intake source differ in one validation order:
SciRel checks grid and mask before required ports, while intake checks
required ports first. The new regression retains current SciRel behavior.
Intake r81-v1 remains `pending_unapproved`; the qualified D1 delivery
root was recently checked read-only and contained zero entries. No
qualified D1 input was consumed.

`solve_free_boundary_anisotropic_picard` now has a current-version
`scirel.asset-document.v1` TaskGraph record. Its five direct dependencies
have exact documents. The graph owns evolving psi, BR/BZ, prior relaxed
currents, residual history and update count; the caller owns the pressure
closure, vacuum state, Green matrices and optional mask. A finite
`maxiter` bounds updates. New tests cover a one-step nonconverged last
state, zero-step infinite residual and empty history, and validation
precedence. Prior numerical assertions and tolerances remain intact.
No scientific source or public API changed.

The pending candidate claimed no-wall circular-filament Green comparisons
and a real Frank-Egedal caller run that current direct graph tests do not
contain; those claims were removed. The historical graph YAML labels
flux as `Wb`, while the field chain's callable documents use `Wb/rad`.
The residual has a fixed `1e-30 Wb` denominator floor, and the wall
record also uses `Wb`. Numerical execution does not settle these public
unit contracts or authorize direct cross-asset wiring. The optional wall
branch changes psi without recomputing BR/BZ, so their derivative
consistency is not guaranteed.

Catalog coverage is `partial: 90/114`; structured public-callable
comparison with the 52-entry historical ledger finds 28 matches and 24
assets without exact documents. All 90 runtime signatures and examples
validated in the isolated worktree. Its 16 direct graph tests and 30
affected tests passed; the main checkout passed 30 affected tests using
`pwsh ./scripts/check.ps1 -Mode affected -BaseRef 9d56a2f`.
These checks do not establish a physically converged equilibrium,
general Green normalization, the caller closure's validity, expert
approval or distribution licensing. No wheel or release was built.
