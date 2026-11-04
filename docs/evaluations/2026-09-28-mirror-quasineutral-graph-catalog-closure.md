# Mirror quasineutral graph catalog closure

Status: development catalog documentation, not new scientific admission,
expert approval or public release. SciRel comparison base: `10ed9ae`.
The current graph implementation and scientific tests were compared with the
historical Pleiades graph YAML, migration mapping and pending intake candidate.
Intake r81-v1 remains `pending_unapproved`. The qualified D1 delivery root
`D:/Users/26569/Desktop/归档_项目/codefusion/最小闭环压测环境` was read-only checked
and contains zero entries, including hidden entries; no qualified D1 input
was consumed.

`solve_mirror_quasineutral_closure` now has an independent
`scirel.asset-document.v1` TaskGraph record with all five documented leaf
dependencies. Its ordinary data dependencies remain acyclic; three edges
explicitly describe one bounded potential-root feedback state. The solver
owns bracket expansion and bisection, while the graph owns the active mask,
composed ion/electron residual and final state assembly. After the solver
returns, the graph reevaluates ion moments and electron response at the final
potential before assembling pressures. A failed solver returns no terminal
state or fallback. No scientific source module or public API changed.

New graph regressions protect that final reevaluation order, an injected
solver failure without pressure assembly, the explicit electron-reference
override, and the zero-density branch's zero iterations and final state.
The historical YAML calls `quadrature_order` an integer although the moment
leaf accepts finite noninteger values with `int(value) >= 8`; it also permits
`max_iterations >= 1` although the bound potential operator requires at
least two. The exact document states the effective current public behavior
instead of silently strengthening the graph's validation.

The graph document has 11 nodes, 77 edges, three feedback edges, one bounded
feedback contract and five direct dependencies. Current catalog coverage is
`partial: 73/114`; a structured callable comparison with the 52-entry
historical ledger leaves 41 ledger assets without exact documents.
The direct graph and selector focus passed 10 tests; all 73 exact documents
passed runtime-signature and executable-example validation. `pwsh
./scripts/check.ps1 -Mode affected -BaseRef 10ed9ae` passed 78 tests in both
the isolated worktree and main checkout. Two outer consumer test files passed
10 more tests in the main checkout. These checks establish bounded behavior
for selected inputs and failures, not arbitrary root uniqueness, physical
model applicability, flux-convention compatibility, expert approval or
distribution licensing. No wheel or release was built.
