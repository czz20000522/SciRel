# Kinetic mirror and Frank-Egedal leaf catalog closure

Status: development catalog documentation, not new scientific admission,
expert approval or public release. SciRel comparison base: `04d996b`.
The six exact documents added in `613a4a6` cover the mirror-invariant
distribution, loss-cone spectrum, Frank-Egedal radial envelope, source
projection, hot-ion moments and pressure state. Their current SciRel callables,
direct tests and pending intake candidates were reviewed individually. The
candidate records remain development evidence; no qualified D1 delivery was
consumed and no candidate admission label was promoted to approval.

The six leaves close the direct dependency set of the Frank-Egedal pressure
closure graph. The loss-cone spectrum is an optional source of degrees for the
source projection; the graph's prescribed pressure model is not itself an
equilibrium solve. Exact documents retain each leaf's units, normalization,
applicability, failure semantics and bounded verification evidence. No
scientific source or public API changed in this batch.

Catalog coverage reached `partial: 107/114`. Structured public-callable
comparison with the 52-entry historical ledger found 45 matches and seven
ledger assets without exact documents. All 107 signatures and examples passed
runtime validation. The isolated worktree and main checkout each passed 14
affected tests; the main check used
`pwsh ./scripts/check.ps1 -Mode affected -BaseRef 04d996b`. Seven relevant
direct scientific test modules passed 34 tests in the isolated worktree.
These checks establish the documented behavior on tested inputs, not physical
validity of arbitrary caller parameters, expert approval, qualified D1
provenance or distribution licensing. No wheel or release was built.
