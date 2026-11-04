# Flux-surface profile catalog closure

Status: development catalog documentation, not new scientific admission,
expert approval or public release. SciRel comparison base: `f2bacff`.
The historical Pleiades descriptor and migration mapping, pending intake
development candidate, current implementation and direct SciRel tests were
compared independently. Intake r81-v1 remains `pending_unapproved`; the
qualified D1 delivery root was read-only checked and contains zero entries.
No qualified D1 input was consumed for this change.

The existing `evaluate_flux_surface_profile` callable now has an independent
`scirel.asset-document.v1` record. It sorts and deduplicates paired scalar
samples, interpolates linearly in a caller-selected flux coordinate, and
applies default or explicit constant endpoint values. It neither constructs
a physical flux surface nor converts `Wb` and `Wb/rad`. Duplicate coordinates
retain the first occurrence after NumPy sorting; conflicting values have no
physical reconciliation or guaranteed original-input tie order.

New direct regressions cover a selected consistent positive coordinate
rescaling, nonfinite explicit endpoint rejection and rejection when only one
unique coordinate remains. The selector retains the consuming grid mirror
graph and its outer composition as reverse dependencies. No scientific
source module or public API changed.

Current catalog coverage is `partial: 74/114`; a structured callable
comparison with the 52-entry historical ledger leaves 40 assets without
exact documents. All 74 documents passed runtime-signature and executable-
example validation. `pwsh ./scripts/check.ps1 -Mode affected -BaseRef
f2bacff` passed 75 tests in both the isolated worktree and main checkout.
The checks establish selected numerical interpolation behavior, not physical
flux-profile validity, general coordinate equivalence, expert approval or
distribution licensing. No wheel or release was built.
