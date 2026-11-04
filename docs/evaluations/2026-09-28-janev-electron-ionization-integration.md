# KN1DPy Janev H/H2 ionization-rate development integration

Status: development candidate for expert review, not qualified whole-source
D1 intake, expert approval or public release. SciRel comparison base:
`19f3ed6`; the clean intake snapshot `647d5db` is `pending_unapproved`.
Its r81-v1 frozen review records an empty qualified L1 delivery root. The
saved KN1DPy package supplies bounded historical comparison only.

## Relationship and disposition

The relation maps electron temperature in eV and an explicit target species
(`H` or `H2`) to a Maxwellian electron-impact ionization rate coefficient in
m^3/s. The saved species-specific nine-coefficient tables, logarithmic
polynomial evaluation, `[0.1, 2.01e4]` eV clipping and `1e-6` conversion
are retained. This is one explicitly branched leaf relation because the saved
callable and its tests jointly define the H/H2 selector. It does not assemble
a density-weighted source or sink, import a radiation table, or add a
TaskGraph dependency. No current SciRel callable defines this same relation.

The saved implementation silently clips zero and negative temperatures and
coerces boolean or numeric-string temperatures to floats. Its operator
document declares positive temperature and fail-closed invalid inputs.
SciRel rejects nonpositive, non-real and non-finite temperatures and unknown
targets while retaining arithmetic on the accepted domain. The saved
implementation SHA-256 is
`ff9b5f5cf854870608ce9e7e7ec8effe8718dbf5ddfa16b1bc90f42df908e3d1`.
The source anchors in the exact document are saved-package claims, not a new
qualified-source freeze.

## Evidence and limits

Twenty direct tests passed: fixed saved reference values cover both target
branches at six temperatures, including fit endpoints; other assertions
cover branch distinction, clipping, scalar shape and invalid input rejection.
Five SHA-gated historical replays passed, including exact two-dimensional
finite grids for both branches and three saved-accepts/current-rejects
witnesses. All 66 exact documents passed runtime-signature and executable-
example validation. The isolated worktree and main checkout each ran
`pwsh ./scripts/check.ps1 -Mode affected -BaseRef 19f3ed6`: 137 passed,
5 optional saved-root replays skipped. Setting `SCIREL_KN1DPY_REVIEW_ROOT`
and running the main-checkout replay separately yielded 5 passed. The catalog
target is `partial: 66/113`. Main commits `c0fb0da` and `92248b3` carry the
asset and three README count changes respectively; other owners' README
edits remain unstaged.

The saved package test evidence is source-derived and records an external
physical-reference `validation_oracle_gap`. Endpoint clipping repeats rates
outside the fit interval. These checks do not establish physical accuracy,
whole-source D1 qualification, expert approval or public distribution
licensing. No wheel or release was built.
