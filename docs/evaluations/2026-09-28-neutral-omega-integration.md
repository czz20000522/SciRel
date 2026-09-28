# KN1DPy atomic and molecular Omega development integration

Status: development baseline candidate for expert review. SciRel base:
`3874127`. The saved KN1DPy bundle is pending re-review and is not approved
or a qualified whole-source D1. The two Omega operators remain distinct
scientific identities and depend respectively on the atomic/molecular Alpha
contraction and collision-matrix exact documents.

## Scientific boundary

- Each operator returns six `(nx,)` profiles: bulk flow, three nonnegative
  elastic Omega channels, their exact sum and the selected perpendicular
  moment. The caller supplies all branch-time fields and quadrature carriers;
  neither function reads a source checkout, cache, network or database.
- The atomic direct-moment branch uses `sum(MH_H_sum) <= 0`; molecular uses
  `sum(MH2_H2_sum) < 0`. Equality therefore takes different branches.
  Molecular H2-H divides inside `np.sum`, while H2-P divides outside. Both
  operators preserve the source's Fortran-order SIG carrier and its symbolic
  sign followed by a magnitude floor.
- A signed denominator remains zero when its unfloored value is exactly zero.
  The saved operators then return a non-finite Omega. The maintained operators
  raise `ValueError` for an enabled channel at that point. Enabled channels
  also reject nonpositive density; with all channels off, finite zero density
  and six zero profiles remain admissible. Nonempty 3-D distributions, 1-D
  aligned velocity axes and finite positive scalar thermal speed and floors
  are checked explicitly.

## Verification and limits

The saved implementation SHA-256 values are atomic
`5b80ea51cf51490208c5e39d71ca5a56c9a4610943a703e066cbbfa4ea6d9038`
and molecular
`13b001078958fa6fd8a819e65340a3a4e22fbfb6a3dbb58e4451db92e81f78d9`.
The SHA-gated replay passed eight cases: three moment scales for each operator
with exact array equality, plus one singular-boundary witness per operator
showing both zero-DeltaVx and zero-Wpp repairs. The two direct test files passed
38 cases, including failures demonstrated before the explicit shape repairs.
All 57 exact documents passed source-runtime and executable-example checks;
the development catalog target is `partial: 57/104`. The worktree `affected`
run selected the two Omega assets and their direct and historical tests,
plus the public export, asset-document and check-script contract tests:
161 passed, 8 optional saved-root replays skipped. No release or wheel was built.

These checks establish bounded source-formula agreement and the stated
failure contract on manufactured carriers. They do not establish external
collision-frequency validity, matrix conservation, complete kinetic-model
composition, qualified D1 provenance, public licensing or expert approval.
