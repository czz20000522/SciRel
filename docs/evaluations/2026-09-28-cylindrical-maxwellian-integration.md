# KN1DPy velocity quadrature and Maxwellian rate development integration

Status: development baseline integration for expert review. This is not qualified
whole-source D1 intake, expert approval, or a public release. The base is
`6033dcdd6b1fb02be9cb4fdb71e60f4c748b7126`; the intake snapshot is
`647d5dbd36404bc5e76d934a875984787e789644` (`pending_unapproved`). The
qualified D1 delivery root was empty when checked for this batch.

## Scientific identity

- [Cylindrical velocity quadrature](../../catalog/examples/scirel.kinetic.cylindrical-velocity-quadrature.json) builds 18 fields from a strictly increasing normalized `(vr, vx)` mesh: ghost faces, annular volume measure, finite-volume coefficients and axial sign indices. The source's half-cell ghost convention is preserved. Its `volume` output can feed the second relation's `cylindrical_volume` port.
- [Maxwellian relative-speed rate average](../../catalog/examples/scirel.collisions.maxwellian-relative-speed-rate-average.json) averages a caller-supplied cross section over the supplied cylindrical mesh. Collision energy uses the particle mass, as in the saved source, rather than reduced mass. The historical `particle_mass_amu` and `target_mass_amu` names are retained, but their factors multiply the saved hydrogen mass `1.6726231e-27 kg`, not the standard atomic mass unit. No cross-section model or mesh convergence policy is supplied.

Neither relation had an equivalent public SciRel callable at the base. The
quadrature-to-rate port composition is directly tested. Both exact documents
list no callable dependency because the rate function accepts weights from any
caller that meets its contract; no TaskGraph was added.

## Source and contract differences

The read-only archive files in `D1待重审历史产物/KN1DPy-631d0bf1/operators/`
matched the intake SHA-256 locks: quadrature
`0a52064747e92b223bdc1c6f78ccdd8bc63a696edc64a7b9c903a6b0515fa0a6`,
rate average
`e006a4ddb49f00d732ba03816fec591bca41d518d6d8df71a2b4985edb1aecb6`.
The archived implementation is historical comparison material; its ledger
label is not present-day approval.

The accepted real-valued formulas, field names, shapes and saved constants are
preserved. SciRel rejects non-finite meshes, non-representable quadrature or
rate results, and non-representable collision energies before invoking the
cross-section callback. It also rejects boolean, numeric-string and complex
arrays as outside the declared real-numeric input contract. A numeric-string
scalar mass or temperature now raises a parameter-named `ValueError`; the
shared validator previously raised `TypeError`. These are documented failure
differences from the archive, not source-behavior claims.

## Verification boundary

- New type regressions failed against the copied intake modules before the fix (11 failures in the initial targeted run). Existing scientific assertions and tolerances were retained.
- Source-free direct relation and document tests: 95 passed. The project `pwsh ./scripts/check.ps1 -Mode affected` selected the two operators, public surface and documentation contracts: 107 passed, with no full-suite fallback.
- Separate read-only intake replay with `SCIREL_KN1DPY_REVIEW_ROOT` set to the archived bundle: 6 passed. It compares all 18 quadrature fields on two meshes at `rtol=1e-15`, constant- and linear-cross-section rates at `rtol=1e-14`, and the NaN repair witnesses. The replay is not part of the source-free maintained test suite.
- The exact document runtime and executable-example checks ran through `tests/test_asset_documentation.py`; catalog coverage is `partial: 26/73` at `0.1.0.dev5`.

These checks establish the discrete relations and bounded saved-point
agreement. They do not establish physical correctness of the particle-mass
collision-energy convention, any caller cross section or mesh, ghost-face
suitability for another scheme, or whole-source D1 qualification. Licensing,
expert review and release remain pending.
