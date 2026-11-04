# Anisotropic force balance catalog closure

Status: development catalog documentation, not new scientific admission,
expert approval or public release. SciRel comparison base: `65989fd`.
The current implementation and direct tests were compared with the
historical Pleiades development mapping and pending intake candidate;
SciRel and intake source text matched after LF normalization. Intake
r81-v1 remains `pending_unapproved`; the qualified D1 delivery root was
recently checked read-only and contained zero entries. No qualified D1
input was consumed.

`compute_anisotropic_force_balance` now has a current-version
`scirel.asset-document.v1` record. It evaluates a discrete cylindrical
gyrotropic pressure force, perpendicular toroidal-current projection,
parallel-force diagnostic and firehose margin on a caller-provided R-Z
grid. Its active mask selects cells for the RMS parallel-force metric;
it does not suppress the returned current. A new direct regression checks
that distinction, along with negative-pressure and nonfinite-field
rejection. Existing numerical assertions and tolerances remain intact.
No scientific source or public API changed.

The affected selector retains the direct toroidal-current wrapper and
both axisymmetric and free-boundary Picard graphs as reverse consumers.
Catalog coverage is `partial: 87/114`; structured public-callable
comparison with the 52-entry historical ledger finds 25 matches and 27
assets without exact documents. All 87 runtime signatures and examples
validated in the isolated worktree. The isolated worktree and main
checkout each passed 88 affected tests; the latter used
`pwsh ./scripts/check.ps1 -Mode affected -BaseRef 65989fd`.

These checks cover selected discrete manufactured states and invalid
inputs. They do not establish a general continuum equilibrium, validate
the caller's pressure closure or physical low-field suitability, or imply
expert recognition and distribution licensing. No wheel or release was
built.
