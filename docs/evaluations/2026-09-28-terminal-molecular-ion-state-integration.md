# KN1DPy terminal molecular-ion state development integration

Status: development candidate for expert review, not a qualified whole-source
D1 intake, expert approval or public release. SciRel comparison base:
`a600632`; the clean intake snapshot is `647d5db` and remains
`pending_unapproved`. Its latest frozen review records an empty qualified D1
delivery root. The saved KN1DPy bundle supports bounded historical comparison
only.

## Relationship and disposition

The saved terminal H2+ relation consumes caller-owned one-dimensional H2 and
neutral densities, ion temperature, ionization and loss profiles, a scalar
mass ratio and an eleven-channel reaction table. It returns H2+ density,
temperature, dissociation frequency and energy-exchange frequency. Its H2+
density can be supplied by a caller to the existing molecular Alpha
contraction; that asset does not calculate the H2+ state and there is no
internal callable dependency. This is a new algebraic leaf relation, not a
terminal feedback or reaction-table assembly.

The saved function uses only reaction-table columns `7:11` with zero-based
indexing. The saved `operator.md` allows generic broadcast profiles and gives
an incompatible-shape example, whereas the callable requires aligned `(nx,)`
profiles, a scalar mass factor and an `(nx,11)` table. Its input names label
ionization and reaction rates `s_inv`, yet both are multiplied by neutral
density. Their physical coefficient dimensions and the resulting absolute
H2+ density require expert review; the maintained exact document preserves
the numerical relation and records this unit gap. The saved implementation
accepts boolean and numeric-string coercions; the maintained real-numeric
contract rejects them before arithmetic. Finite real arithmetic keeps source
order. The saved implementation SHA-256 is
`a04b3049e4d33af713eb5632f88135777e683f7df257dfc061c8a853c06edb57`.

## Evidence and limits

Eleven direct tests passed. They cover independent per-cell recomputation of
all four fields, invariance to the first seven reaction-table columns, zero
H2 density with a positive denominator, non-real input rejection, zero
denominator and non-finite output rejection. Three optional SHA-gated
saved-arm replays passed: ordinary and zero-density finite carriers match
exactly, and a boolean-loss witness distinguishes the maintained failure
contract. All 62 exact documents passed runtime-signature and executable-
example validation. The worktree `affected` gate selected this asset, both
direct test files, the public export and the asset-document/check-script
contracts: 100 passed and 3 optional saved-root replays skipped. The catalog
target is `partial: 62/109`.

These checks do not establish the rate-table producer, absolute physical
units, H2+ distribution seeding, full KN1D terminal closure, whole-source D1
qualification, expert approval or public distribution licensing. No wheel or
release was built.
