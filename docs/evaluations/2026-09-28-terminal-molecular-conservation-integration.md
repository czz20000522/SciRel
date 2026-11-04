# KN1DPy terminal molecular conservation development integration

Status: development candidate for expert review, not a qualified whole-source
D1 intake, expert approval or public release. SciRel comparison base:
`0cfa7ed`; the clean intake snapshot is `647d5db` and remains
`pending_unapproved`. Its latest r81-v1 frozen review records an empty
qualified L1 delivery root. The saved KN1DPy bundle supports bounded
historical comparison only.

## Relationship and disposition

The diagnostic consumes caller-owned aligned one-dimensional axial positions,
total H2 heat flux and total H2 energy-transfer rate. It compares each
interval flux difference quotient with the adjacent-node transfer mean,
normalizes their absolute difference by the global maximum magnitude of both
intermediate profiles, and returns zero at the last node by convention. It
does not calculate either upstream profile. The existing heat-flux and
energy-transfer relations expose compatible named outputs, but are not bound
as callable dependencies; this is a new leaf relation. A composition test
checks port and spatial-shape compatibility, not a complete energy balance.

The saved implementation and direct package tests accept signed profiles and
decreasing or locally nonmonotonic positions when every adjacent spacing is
nonzero. An all-zero normalization is rejected. Individual normalized errors
can exceed one, and the final zero is not evidence of a checked boundary
equation. The saved `operator.md` instead describes nonnegative or broadcast
profiles, incorrect units for flux and error, and a one-node example that the
callable rejects. The maintained exact document follows the callable's
verified discrete contract. It excludes boolean, complex and numeric-string
coercions accepted by the saved implementation; finite real arithmetic keeps
source order. The saved implementation SHA-256 is
`258ef36f7d265f5a7cc08f021cbf91fbd83ad9ce6876a1c56d1064655d4c2af3`.
Its `kinetic_h2.py:2063-2070` source anchor is the saved package's claim,
not a fresh verification against a qualified original source tree.

## Evidence and limits

Fourteen direct tests passed. They cover independent nonuniform residuals,
zero-error linear balance on a decreasing grid, signed profiles, the
source-defined endpoint, input and derived non-finite failures, zero
normalization, non-real input rejection and upstream port composition. Three
optional SHA-gated historical replays passed: two finite carriers match
exactly, and a boolean-position witness distinguishes the maintained input
repair. All 63 exact documents passed runtime-signature and executable-example
validation. The isolated worktree and main checkout each ran
`pwsh ./scripts/check.ps1 -Mode affected -BaseRef 0cfa7ed`: 89 passed and
3 optional saved-root replays skipped. Setting `SCIREL_KN1DPY_REVIEW_ROOT`
and running the main-checkout replay separately yielded 3 passed. The catalog
target is `partial: 63/110`. Main commits are `a7d8382`, `18d3299` and
`8568e70`; the README commit staged only three coverage-count changes, leaving
other owners' edits unstaged.

These checks do not establish physical normalization of either upstream
profile, a complete terminal transport conservation law, whole-source D1
qualification, expert approval or public distribution licensing. No wheel or
release was built.
