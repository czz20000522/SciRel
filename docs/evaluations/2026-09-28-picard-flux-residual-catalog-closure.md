# Picard flux residual catalog closure

Status: development catalog documentation, not new scientific admission,
expert approval or public release. SciRel comparison base: `309193a`.
The maintained implementation and direct tests were compared with the
historical Pleiades development mapping and pending intake candidate;
SciRel and intake implementation text matched. Intake r81-v1 remains
`pending_unapproved`; the qualified D1 delivery root was recently checked
read-only and contained zero entries. No qualified D1 input was consumed.

`compute_picard_flux_residual` now has a current-version
`scirel.asset-document.v1` record. It measures a relative L2 change between
two same-shape finite two-dimensional flux states, using a `1e-30 Wb`
denominator floor and scaled arithmetic for selected numerical extremes.
The direct tests retain their prior numerical assertions and tolerances;
new checks cover mismatched shapes and nonfinite entries. No scientific
source or public API changed.

The free-boundary anisotropic Picard graph calls this diagnostic after an
optional wall correction, and the selector regression checks that the graph
remains a reverse test consumer. The historical residual contract labels
its inputs `Wb`. Its fixed denominator floor means a numerical comparison
cannot approve direct use of a `Wb/rad` state; the field chain's flux
convention still needs science-owner adjudication. At the smallest
subnormal magnitudes, scaling may overflow the floor and return zero rather
than the ideal mathematical ratio. The exact document states this limit.

Catalog coverage is `partial: 86/114`; structured public-callable
comparison with the 52-entry historical ledger finds 24 matches and 28
assets without exact documents. All 86 runtime signatures and examples
validated in the isolated worktree. Focused direct and selector tests
passed (77); affected tests passed in the isolated worktree and main
checkout (91 each), with the latter using
`pwsh ./scripts/check.ps1 -Mode affected -BaseRef 309193a`.
These checks do not certify physical equilibrium convergence, unit
normalization across assets, expert approval or distribution licensing.
No wheel or release was built.
