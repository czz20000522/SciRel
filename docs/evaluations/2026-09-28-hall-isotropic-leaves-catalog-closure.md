# Hall and isotropic pressure-flux leaves catalog closure

Status: development catalog documentation, not new scientific admission,
expert approval or public release. SciRel comparison base: `67bd018`.
Three public callables were compared individually with current source,
direct tests, historical Pleiades mappings and pending intake
candidates. SciRel and intake source text matched after LF
normalization for each. Intake r81-v1 remains `pending_unapproved`;
the previously checked qualified D1 delivery root contained zero
entries. No qualified D1 input was consumed.

`close_hall_two_fluid_pressure` broadcasts a caller pressure law,
density, electron pressure and potential into a two-fluid state;
explicit ion components are not checked to sum to the supplied total.
`build_pressure_flux_state` requires one exact Z=0 row and a first
exact-zero pressure sample, then returns a clipped pressure spline
derivative and zero-current state. `pressure_flux_picard_step` performs
one area-weighted current and Green-flux update and reports a boundary
flux-normalized residual. The candidate's untested `2*pi` rescaling
verification claim was removed from the pressure-flux state document.
No scientific source module or public API changed.

Catalog coverage is `partial: 101/114`; structured public-callable
comparison with the 52-entry historical ledger finds 39 matches and
13 assets without exact documents. All 101 runtime signatures and
examples validated in the isolated worktree. Direct scientific and
related graph tests passed 19/19; isolated and main affected checks
each passed 14/14, with the main checkout using
`pwsh ./scripts/check.ps1 -Mode affected -BaseRef 67bd018`.

The checks establish selected arithmetic and error paths, not
arbitrary pressure-law consistency, general Green compatibility,
convergence, expert approval or public distribution licensing. No
wheel or release was built.
