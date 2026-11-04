# KN1DPy molecular-H2 charge-exchange rate development integration

Status: development candidate for expert review, not qualified whole-source
D1 intake, expert approval or public release. SciRel comparison base:
`71f6be6`; the clean intake snapshot `647d5db` is `pending_unapproved`.
Its r81-v1 frozen review records an empty qualified L1 delivery root. The
saved KN1DPy package supplies bounded historical comparison only.

## Relationship and disposition

The relation maps paired plasma temperature and impact energy in eV to the
H2 + H2+ charge-exchange Maxwellian rate coefficient. It evaluates the saved
9-by-9 bivariate logarithmic fit, clipping each input to `[0.1, 2.01e4]`
eV. The molecular coefficient table and energy-outer, temperature-inner
summation order are preserved. This is a separate leaf from the atomic-H rate
fit and from the molecular charge-exchange cross section. It does not call
`maxwellian-relative-speed-rate-average`; numerical or physical equivalence
to a velocity-mesh integral has not been established. No TaskGraph dependency
was added.

The saved `operator.md` describes broadcast-compatible input shapes, while
the callable requires exact shape equality. SciRel follows the callable.
The saved implementation also clips nonpositive temperature and negative
energy and accepts boolean and numeric-string coercion. SciRel rejects these
inputs, along with complex and non-finite values, as a documented maintained
contract repair. The saved implementation SHA-256 is
`8ca54201138f6d1d19803e2bfb042b80980b2a9367bad36d53eafccdfc6bfd22`.
The source and caller anchors in the exact document are saved-package claims,
not a new qualified-source freeze.

## Evidence and limits

Fourteen direct tests passed: fixed saved reference values and independent
`polyval2d` reevaluation check the fit on ordinary finite samples, while a
saved-order reference pins the double-upper-endpoint corner. Direct tests
also cover the atomic sibling distinction, endpoint clipping, scalar shape,
invalid domains and non-real input rejection. Five SHA-gated historical
replays passed, including exact one- and two-dimensional finite grids and
three saved-accepts/current-rejects witnesses. All 65 exact documents passed
runtime-signature and executable-example validation. The isolated worktree
and main checkout each ran `pwsh ./scripts/check.ps1 -Mode affected -BaseRef
71f6be6`: 130 passed, 5 optional saved-root replays skipped. Setting
`SCIREL_KN1DPY_REVIEW_ROOT` and running the main-checkout replay separately
yielded 5 passed. The catalog
target is `partial: 65/112`. Main commits `0a41745` and `a5659d5` carry the
asset and the three README count changes respectively; other owners' README
edits remain unstaged.

No external atomic-physics oracle validates the fitted rate or its claimed
physical accuracy; the saved package records `validation_oracle_gap`.
Endpoint clipping repeats rates outside the fit domain. These checks do not
establish whole-source D1 qualification, expert approval or public
distribution licensing. No wheel or release was built.
