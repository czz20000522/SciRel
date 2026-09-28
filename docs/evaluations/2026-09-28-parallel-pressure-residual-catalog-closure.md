# Parallel-pressure residual catalog closure

Status: development catalog documentation, not new scientific admission,
expert approval or public release. SciRel comparison base: `6a81473`.
The current implementation and direct tests were compared with the
historical Pleiades development mapping and pending intake candidate;
SciRel and intake source text matched after LF normalization. Intake
r81-v1 remains `pending_unapproved`; the previously checked qualified
D1 delivery root contained zero entries. No qualified D1 input was
consumed.

`compute_parallel_pressure_residual` now has a current-version
`scirel.asset-document.v1` record. It differentiates the sampled
`p_parallel/max(B, 1e-30)` relation in B-value space, reports the
perpendicular-pressure residual and normalized summary, and raises
on tolerance failure when `strict` is truthy. It is not an R-Z spatial
force-balance residual. No scientific source module or public API
changed.

Catalog coverage is `partial: 95/114`; structured public-callable
comparison with the 52-entry historical ledger finds 33 matches and
19 assets without exact documents. All 95 runtime signatures and
examples validated in the isolated worktree. Direct scientific tests
passed 4/4; isolated and main affected checks each passed 14/14, with
the main checkout using
`pwsh ./scripts/check.ps1 -Mode affected -BaseRef 6a81473`.

The tests establish selected finite-sample and failure behavior, not
spatial derivatives or general equilibrium validity. They do not
imply expert approval or public distribution licensing. No wheel or
release was built.
