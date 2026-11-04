# KN1DPy atomic-H charge-exchange rate development integration

Status: development candidate for expert review, not a qualified whole-source
D1 intake, expert approval or public release. SciRel comparison base:
`ca9cb3e`; clean intake snapshot `647d5db` is `pending_unapproved`.
Its latest r81-v1 frozen review records an empty qualified L1 delivery root.
The saved KN1DPy package supports bounded historical comparison only.

## Relationship and disposition

The relation maps paired plasma temperature and impact energy in eV to the
H + H+ charge-exchange Maxwellian rate coefficient. It evaluates a saved
9-by-9 bivariate logarithmic fit with temperature and energy clipped to
`[0.1, 2.01e4]` eV. The coefficient table and energy-outer,
temperature-inner summation order are preserved. This is a new independent
leaf relation, not an invocation of the existing atomic-H charge-exchange
cross-section callable and not a velocity-mesh calculation by
`maxwellian-relative-speed-rate-average`. Their physical or numerical
equivalence has not been established. The public callable follows the current
collisions-domain export pattern; no TaskGraph dependency is added.

The saved `operator.md` declares positive temperature and nonnegative energy,
but its implementation clips nonpositive temperatures and negative energies
into the fit. SciRel rejects both. Independent review also found that the
intake successor still accepts boolean and numeric-string coercion through
`np.asarray(..., dtype=float)`, inconsistent with the maintained collision
energy input contract; SciRel rejects boolean, complex and numeric-string
inputs. The saved implementation also accepts those coercions. This is a
documented additional development repair, not historical parity. The saved
implementation SHA-256 is
`9a0037c238cc9fc99eabfa17984368d954c56ef9aa651e47967b5b1c273a1bfa`.
The source anchors are the saved package's claims, not a new qualified-source
freeze.

## Evidence and limits

Fourteen direct tests passed: fixed saved reference values and an independent
`polyval2d` reevaluation check the fit on ordinary finite points; clipping,
scalar shape, invalid domains and non-real rejection have direct assertions.
The double-upper-endpoint corner retains a source-order reference assertion:
`polyval2d` differs there by about `2.1e-12` relative due to addition order,
so its ordinary-point oracle tolerance was not expanded to hide that effect.
Five SHA-gated historical replays passed, including exact one- and
two-dimensional finite grids and three saved-accepts/current-rejects
witnesses. All 64 exact documents passed runtime-signature and executable-
example validation. The isolated worktree and main checkout each ran
`pwsh ./scripts/check.ps1 -Mode affected -BaseRef ca9cb3e`: 129 passed,
5 optional saved-root replays skipped. Setting `SCIREL_KN1DPY_REVIEW_ROOT`
and running main-checkout replay separately yielded 5 passed. The catalog
target is `partial: 64/111`. Main commits `62d7aac` and `8fd69f2` carry the
asset and the three README count changes respectively; other owners' README
edits remain unstaged.

No external atomic-physics oracle validates the fitted rate or its claimed
physical accuracy; the saved package records `validation_oracle_gap`.
Endpoint clipping can repeat a value outside the fit domain. These checks do
not establish whole-source D1 qualification, expert approval or public
distribution licensing. No wheel or release was built.
