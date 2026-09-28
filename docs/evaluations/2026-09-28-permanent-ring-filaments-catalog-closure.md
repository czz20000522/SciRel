# Permanent-ring filament geometry catalog closure

Status: development catalog documentation, not new scientific admission,
expert approval or public release. SciRel comparison base: `1e507ec`.
The current implementation and direct tests were compared with the
historical Pleiades development mapping and pending intake candidate;
SciRel and intake source text matched after LF normalization. Intake
r81-v1 remains `pending_unapproved`; the qualified D1 delivery root was
recently checked read-only and contained zero entries. No qualified D1
input was consumed.

`discretize_permanent_ring` now has a current-version
`scirel.asset-document.v1` record. It generates two ordered sets of
eight R-Z filament points, with opposite dimensionless relative weights.
Positive rotation follows the maintained row-vector convention. New
direct tests cover rejection of geometry crossing the cylindrical axis
and the near-zero-angle unrotated branch. Existing layout, rotation and
dimension assertions remain intact. No scientific source or public API
changed.

Catalog coverage is `partial: 91/114`; structured public-callable
comparison with the 52-entry historical ledger finds 29 matches and 23
assets without exact documents. All 91 runtime signatures and examples
validated in the isolated worktree. The isolated worktree and main
checkout each passed 21 affected tests; the latter used
`pwsh ./scripts/check.ps1 -Mode affected -BaseRef 1e507ec`.

The returned weights are not amperes and the Operator does not calculate
magnetic fields, magnetization, material response or arbitrary filament
resolution. These tests do not imply expert approval or public
distribution licensing. No wheel or release was built.
