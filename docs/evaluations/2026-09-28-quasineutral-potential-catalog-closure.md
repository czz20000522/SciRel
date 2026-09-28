# Quasineutral potential catalog closure

Status: development catalog documentation, not new scientific admission,
expert approval or public release. SciRel comparison base: `1ea1eab`.
The prior quasineutral leaf review records the historical Pleiades ledger and
clean intake snapshot `647d5db`; intake r81-v1 remains `pending_unapproved`.

The existing `solve_quasineutral_potential` callable now has an independent
`scirel.asset-document.v1` record. It documents the caller-owned decreasing
logarithmic charge residual, finite positive thermal and charge inputs,
eight-round bracket expansion, shared vectorized bisection stopping rule,
inactive reference potentials, final callback evaluation and failure paths.
No scientific source module or public API changed. A direct regression now
asserts that an all-inactive call evaluates its final residual exactly once.

The domain navigation and coverage references are `partial: 70/114`; a
structured callable comparison with the historical 52-entry ledger leaves
44 ledger assets without exact documents.
The selector test confirms the solver's canonical asset identity and retains
the mirror quasineutral graph and its two outer graphs as reverse dependents.
The mirror graph still consumes two undocumented kinetic leaves and needs its
own state, feedback and failure-propagation review before it can be represented
as an exact documented TaskGraph.

In the isolated worktree, `pwsh ./scripts/check.ps1 -Mode affected -BaseRef
1ea1eab` selected the solver, selector and asset-documentation tests: 77
passed. The main checkout ran the same affected selection after integration:
77 passed. All 70 exact documents passed runtime-signature and executable-
example validation through that gate. These checks establish the stated
current SciRel behavior on tested inputs. They do not establish arbitrary
residual-model physics, physical coordinate alignment, expert approval,
qualified D1 provenance or distribution licensing. No wheel or release was
built.
