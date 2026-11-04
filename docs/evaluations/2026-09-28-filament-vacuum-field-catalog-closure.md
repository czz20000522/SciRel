# Filament vacuum field catalog closure

Status: development catalog documentation, not new scientific admission,
expert approval or public release. SciRel comparison base: `b6ec4e2`.
The maintained implementation and direct tests were compared with the
frozen historical Pleiades mapping and pending intake candidate. SciRel
and intake implementation text matched. Intake r81-v1 remains
`pending_unapproved`; the qualified D1 delivery root was read-only checked
and contained zero entries. No qualified D1 input was consumed.

`integrate_filament_vacuum_field` now has a current-version
`scirel.asset-document.v1` record. It superposes ideal circular-filament
fields on a rectilinear grid and integrates `R B_Z` along the uniformly
spaced radial axis by trapezoids. Returned psi is zero at the first radial
grid point, which need not be the physical axis. The implementation accepts
either array axis as radial, forces `B_R=0` near R=0 and rejects coincident
source/target points. No scientific source or public API changed.

A new direct regression compares the integrated flux on one fine grid with
the circular-filament `psi=R A_phi` kernel after subtracting its first-radius
reference. The comparison uses `rtol=3e-5` and `atol=3e-9`; it does not
establish arbitrary-grid quadrature accuracy. Existing direct tests cover
field superposition, the analytic axial-field limit, transposed layout,
radial quadrature increments and an invalid radial grid.

Catalog coverage is `partial: 84/114`. Structured callable comparison with
the historical 52-entry ledger finds 22 matches and 30 assets without exact
documents. The isolated worktree and main checkout each passed 86 affected
tests, with the latter using `pwsh ./scripts/check.ps1 -Mode affected
-BaseRef b6ec4e2`. Runtime signatures and examples executed for all 84
documents; the deterministic catalog partition test passed.

This flux is relative to the first radial grid point and carries the
implemented `psi=R A_phi` convention in `Wb/rad`; existing vacuum-field
documents still label psi as `Wb`. Direct cross-asset public wiring remains
for science-owner adjudication. These checks do not establish resolved
self-fields, material effects, expert recognition or distribution licensing.
No wheel or release was built.
