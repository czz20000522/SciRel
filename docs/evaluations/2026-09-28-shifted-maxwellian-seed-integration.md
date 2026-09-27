# KN1DPy shifted-Maxwellian seed development integration

Status: development baseline integration for expert review, not qualified
whole-source D1 intake, expert approval or public release. The comparison base
is SciRel `ea3e641471c439f1abc894a0999f160aa39adfb4`; the intake snapshot
is `647d5dbd36404bc5e76d934a875984787e789644` (`pending_unapproved`).
The qualified D1 delivery root was empty at the start of this batch.

## Scientific identity

The [exact document](../../catalog/examples/scirel.kinetic.shifted-maxwellian-seed.json)
defines one new leaf: the volume-normalized shifted-Maxwellian exponential
seed on an explicit `(vr, vx)` mesh, before the saved source's discrete moment
compensation. It retains the source's strict `-80 < argument < 0` clamp: a node
at the shifted peak (`argument == 0`) receives the floor while the `exponent`
output retains zero. The seed consumes caller-supplied cell volumes; a direct
test connects the existing cylindrical quadrature's `volume` output to this
normalization and the same mesh to the Maxwellian rate average. The rate
average does not consume the seed distribution, so no TaskGraph or callable
dependency was invented. No existing main callable implements this seed.

`mass_amu` is a historical parameter name. Its factor multiplies the saved
hydrogen mass `1.6726231e-27 kg`, not the standard atomic mass unit. A direct
cross-asset assertion checks the returned thermal speed against SciRel's
existing thermal-speed relation at the same normalization temperature and
mass factor.

## Source and failure differences

The read-only archive implementation at
`D1待重审历史产物/KN1DPy-631d0bf1/operators/平移Maxwellian离散初值/scientific_operator.py`
matched the intake SHA-256 pin
`c495a86822c02dbb4bd84fe11f5cffb6093a85906be3dae66773d2e334641051`.
The accepted real-valued formula, operation order, constants, clamp and output
fields are unchanged. The saved implementation checked array finiteness but
coerced boolean and numeric-string arrays, accepted `molecule_count=True` or
`1.0`, and returned zero layers for empty shifts. SciRel rejects these against
the declared real-array, integer-scalar and nonempty-shift contracts. Numeric
string scalar masses or normalization temperatures now raise a parameter-named
`ValueError` instead of an unrelated `TypeError`.

## Verification boundary

- New input regressions failed first against the copied intake module: 12 failed and one valid NumPy-integer case passed. The old numerical assertions and tolerances were retained.
- Source-free direct tests passed 48 cases. The project `pwsh ./scripts/check.ps1 -Mode affected` selected the leaf, public surface and documentation gates: 74 passed with no full-suite fallback.
- Separately executed, SHA-256-pinned intake replay against the archive passed 3 cases. It compares distribution, exponent and thermal speed on single- and double-molecule holdouts at `rtol=1e-15`; it is outside the maintained source-free suite.
- All 27 exact documents passed source-runtime and executable-example validation. The catalog remains a partial `27/74` development pilot at `0.1.0.dev5`.

These observations establish the discrete seed relation and bounded saved-point
agreement. They do not establish that the uncompensated seed is physically
adequate for any downstream transport calculation, that a caller's mesh is
valid for its model, or that the source project has regained strict D1 status.
Licensing, expert review and release remain pending.
