# Mirror constrained-moments catalog closure

Status: development catalog documentation, not new scientific admission,
expert approval or public release. SciRel comparison base: `c79ce17`.
The historical Pleiades descriptor and migration mapping, pending intake
development candidate, current implementation and direct SciRel tests were
compared independently. Intake r81-v1 remains `pending_unapproved`; no
qualified D1 delivery was consumed for this change.

The existing `evaluate_mirror_constrained_moments` callable now has an
independent `scirel.asset-document.v1` record. It states the invariant
bi-Maxwellian density and gyrotropic pressure relation, the untruncated
analytic limit, the optional two-plug loss-cone pitch integrals over `[0,40]`,
the saved `[-700,700]` exponent clip and the absence of a general finite-output
or quadrature-error check. The mass is validated but does not enter these
moment formulas; this leaf accepts signed nonzero charge, while its consuming
quasineutral graph requires a positive ion charge.

Direct regressions now protect signed negative charge, the validation of
`quadrature_order` even when plug integration is bypassed, the refill-one
skip of plug profile evaluation, and fractional order truncation on the
active plug branch. The saved graph YAML calls the quadrature order an integer;
the maintained leaf accepts a finite value with `int(value) >= 8`, and the
graph forwards it without an integer check. The graph review must state the
effective public contract and reconcile that descriptor. No scientific
source module or public API changed.

All five direct leaves consumed by the mirror quasineutral graph now have
independent exact documents. The graph's state, feedback order, stopping and
failure propagation still need independent review. Current catalog coverage
is `partial: 72/114`; a structured callable comparison with the 52-entry
historical ledger leaves 42 ledger assets without exact documents.

The direct moment tests passed 10/10. The 72 exact documents passed runtime
signature and executable-example validation. `pwsh ./scripts/check.ps1 -Mode
affected -BaseRef c79ce17` passed 78 tests in both the isolated worktree and
main checkout. The existing independent adaptive pitch-integral comparison
covers one selected two-barrier case at quadrature order 256 with `rtol=3e-8`
and `atol=1e-10`; it does not establish default-order convergence across
profiles, flux-convention compatibility, source-runtime identity, expert
approval or distribution licensing. No wheel or release was built.
