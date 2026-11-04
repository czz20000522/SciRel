# KN1DPy atomic H(1s) radiative recombination development integration

Status: development candidate for expert review, not qualified whole-source
D1 intake, expert approval or public release. SciRel comparison base:
`60d06ad`. The clean intake snapshot `647d5db` contains a development
candidate and exact document, but its r81-v1 freeze is `pending_unapproved`
and records an empty qualified L1 delivery root. The saved KN1DPy package
supports bounded historical comparison only.

## Relationship and disposition

The relation maps electron temperature in eV to the H+ + e -> H(1s) + hv
radiative recombination rate coefficient in m^3/s. It preserves the saved
closed form, Ry=13.58 eV, n=1, A_nl=3.92, x_nl=0.35, the `[0.1, 2.01e4]`
eV endpoint clipping and the original arithmetic order. This is a separate
ground-state recombination leaf, not the Janev ionization fit, an excited-
level recombination model or a density-weighted source term. No TaskGraph
dependency is added.

The saved implementation silently clips nonpositive temperatures and coerces
boolean and numeric-string inputs. The intake candidate rejected nonpositive
temperatures, as its contract declared, but retained those type coercions.
The maintained SciRel callable also rejects boolean, complex and numeric-
string temperatures. These are documented repairs, not historical parity.
The saved implementation SHA-256 is
`ad71a46c865380793ee73e4ae267d536f0e0c8384929b1fff4bb18000c2e2528`.
Source and caller anchors in the exact document are saved-package claims,
not a new qualified-source freeze.

## Evidence and limits

Thirteen direct tests passed. Six fixed saved values, an independent closed-
form reevaluation and a holdout grid retain the intake candidate's `1e-15`
relative tolerance. Direct assertions cover sampled temperature monotonicity,
endpoint clipping, scalar shape, nonpositive and non-finite input rejection,
and non-real coercion rejection. Five SHA-gated historical replays passed:
exact one- and two-dimensional finite grids and three saved-accepts/current-
rejects witnesses. All 67 exact documents passed runtime-signature and
executable-example validation. The isolated worktree and main checkout each ran
`pwsh ./scripts/check.ps1 -Mode affected -BaseRef 60d06ad`: 131 passed,
5 optional saved-root replays skipped. Setting `SCIREL_KN1DPY_REVIEW_ROOT`
and running the main-checkout replay separately yielded 5 passed. The catalog
target is `partial: 67/114`. Main commits `b128d8e` and `3b91947` carry the
asset and three README count changes respectively; other owners' README
edits remain unstaged.

The saved package records an external atomic-physics `validation_oracle_gap`.
Ry=13.58 eV is a frozen fit constant, not a modern re-derivation. Clipping
repeats endpoint values outside the fit interval. These checks do not prove
physical accuracy, whole-source D1 qualification, expert approval or public
distribution licensing. No wheel or release was built.
