# Dense axisymmetric Green catalog closure

Status: development catalog documentation, not new scientific admission,
expert approval or public release. SciRel comparison base: `63bce29`.
The maintained implementation and direct tests were compared with the
frozen historical Pleiades mapping and pending intake candidate. SciRel
and intake implementation text matched. Intake r81-v1 remains
`pending_unapproved`; the qualified D1 delivery root was read-only checked
and contained zero entries. No qualified D1 input was consumed.

`dense_axisymmetric_green_response` now has a current-version
`scirel.asset-document.v1` record. It returns separate circular-filament
Green columns for flux and two poloidal-field components, with a
dimensionless source weight. It neither sums columns nor applies currents
or cell areas. The implemented near-axis source and nonfinite-kernel rules
return zero instead of a resolved singular self-field. No scientific source
or public API changed.

A new direct regression compares each weighted flux and field column with
the separately maintained circular-filament kernel at selected points.
Existing direct tests cover weight scaling, the analytic axial-field limit,
empty-source shape, axis-source zeros and invalid inputs. Catalog coverage
is `partial: 82/114`; structured callable comparison with the historical
52-entry ledger finds 20 matches and 32 assets without exact documents.
The isolated worktree and main checkout each passed 89 affected tests,
with the latter using `pwsh ./scripts/check.ps1 -Mode affected -BaseRef
63bce29`. Runtime signatures and examples executed for all 82 documents;
the deterministic catalog partition test passed.

Numerical agreement with the circular-filament kernel does not settle the
public flux-unit labels: that vacuum-field document says `Wb/A`, while this
record uses the implemented `psi=R A_phi` convention in `Wb/rad/A`.
Cross-asset public wiring remains for science-owner adjudication. These
tests do not establish resolved self-fields, arbitrary target accuracy,
expert recognition or distribution licensing. No wheel or release was
built.
