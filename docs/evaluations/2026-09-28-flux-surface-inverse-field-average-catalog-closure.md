# Inverse-field polyline quadrature catalog closure

Status: development catalog documentation, not new scientific admission,
expert approval or public release. SciRel comparison base: `6c010e8`.
The current implementation and direct tests were compared with the
historical Pleiades development mapping and pending intake candidate;
SciRel and intake source text matched after LF normalization. Intake
r81-v1 remains `pending_unapproved`; the previously checked qualified
D1 delivery root contained zero entries. No qualified D1 input was
consumed.

`compute_flux_surface_inverse_field_average` now has a current-version
`scirel.asset-document.v1` record. It samples the magnetic-field
magnitude and optional scalar at caller-provided R-Z polyline points
with a cubic rectangular-grid spline, then applies trapezoidal
`dl/B` quadrature. The optional average is the ratio of the weighted
quantity and inverse-field integrals. It does not trace a field line,
close a contour or prove a physical flux surface. No scientific source
module or public API changed.

Catalog coverage is `partial: 93/114`; structured public-callable
comparison with the 52-entry historical ledger finds 31 matches and
21 assets without exact documents. All 93 runtime signatures and
examples validated in the isolated worktree. The direct scientific
contract tests passed 5/5; isolated and main affected checks each
passed 14/14, with the main checkout using
`pwsh ./scripts/check.ps1 -Mode affected -BaseRef 6c010e8`.

The tests cover small grids and selected discrete paths, not
interpolation convergence or physical completeness of a supplied
contour. They do not imply expert approval or public distribution
licensing. No wheel or release was built.
