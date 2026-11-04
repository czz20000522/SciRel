# Firehose and mirror margins catalog closure

Status: development catalog documentation, not new scientific admission,
expert approval or public release. SciRel comparison base: `d084401`.
The current implementation and direct tests were compared with the
historical Pleiades development mapping and pending intake candidate;
SciRel and intake source text matched after LF normalization. Intake
r81-v1 remains `pending_unapproved`; the previously checked qualified
D1 delivery root contained zero entries. No qualified D1 input was
consumed.

`compute_firehose_mirror_margins` now has a current-version
`scirel.asset-document.v1` record. It evaluates the two implemented
sampled pressure margins, using a global B-sorted finite derivative
for the mirror term, and returns their minima and strict-positivity
flags. The diagnostic does not calculate mode growth rates or establish
general plasma stability. The MHD navigation now identifies this
limited capability. No scientific source module or public API changed.

Catalog coverage is `partial: 94/114`; structured public-callable
comparison with the 52-entry historical ledger finds 32 matches and
20 assets without exact documents. All 94 runtime signatures and
examples validated in the isolated worktree. Direct scientific tests
passed 4/4; isolated and main affected checks each passed 14/14, with
the main checkout using
`pwsh ./scripts/check.ps1 -Mode affected -BaseRef d084401`.

The tests establish finite-sample formulas and selected failure
branches, not convergence of the B derivative or a physical stability
theorem. They do not imply expert approval or public distribution
licensing. No wheel or release was built.
