# Bilinear R-Z sampling catalog closure

Status: development catalog documentation, not new scientific admission,
expert approval or public release. SciRel comparison base: `3155120`.
The current implementation and direct tests were compared with the
historical Pleiades mapping and pending intake candidate. SciRel and
intake source text matched after LF normalization. Intake r81-v1 remains
`pending_unapproved`; the previously checked qualified D1 delivery root
contained zero entries. No qualified D1 input was consumed.

`sample_rectilinear_field` now has a current-version
`scirel.asset-document.v1` record. It bilinearly samples one real scalar
field at ordered `[R,Z]` points within a rectilinear `[Z,R]` grid. New
direct tests cover an empty `[0,2]` query and rejection of an invalid
later point. A selector regression protects selection of the consuming
equilibrium diagnostics graph when this Operator's source changes. No
scientific source module or public API changed.

Catalog coverage is `partial: 92/114`; structured public-callable
comparison with the 52-entry historical ledger finds 30 matches and 22
assets without exact documents. All 92 runtime signatures and examples
validated in the isolated worktree. Both the isolated worktree and main
checkout passed 90 affected tests; the latter used
`pwsh ./scripts/check.ps1 -Mode affected -BaseRef 3155120`.

The Operator does not infer the sampled quantity's physical meaning,
extrapolate outside the grid or establish validity of a caller's field.
The tests do not imply expert approval or public distribution licensing.
No wheel or release was built.
