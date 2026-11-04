# KN1DPy adaptive neutral velocity mesh development integration

Status: development baseline candidate for expert review, not qualified
whole-source D1 intake, expert approval or public release. The comparison
base is SciRel `b13836c`; the clean intake snapshot is `647d5db`
(`pending_unapproved`). The qualified D1 delivery root was empty at the
start of this batch.

## Scientific boundary

The [exact document](../../catalog/examples/scirel.kinetic.adaptive-neutral-velocity-mesh.json)
defines one source-specific mesh relation: ion temperatures and requested
energies determine the saved `3.5` base mesh, optional quadratic stretching,
normalization temperature, inserted energy nodes and their final indices.
The cap filters only the population used to choose `Tnorm` and stretching;
the saved loop still inserts every positive requested energy, including one
above the cap. An inserted node can extend the final mesh beyond `3.5`.

The output is a mesh, not a transport solver. A direct test connects its
`vr`/`vx` axes to the existing cylindrical quadrature, then feeds the
quadrature's cell volumes to the shifted-Maxwellian seed and neutral moment
reduction. This observed port composition does not create a TaskGraph or
callable dependency.

## Source and failure differences

The read-only archive implementation at
`D1待重审历史产物/KN1DPy-631d0bf1/operators/自适应中性粒子速度网格/scientific_operator.py`
matched the intake SHA-256 pin
`38fcde8ba437ce5ee72f6465968ea3fd8ade9a4ff24b5a6692823a20207f2842`.
With the isolated SciRel `src/` path asserted, six valid uniform, stretched,
inserted-energy, capped and multi-temperature cases matched all five saved
return fields with `assert_array_equal`.

The saved implementation casts boolean/numeric-string inputs, discards a
complex temperature's imaginary part, accepts non-finite requested energy or
cap, and can return duplicate axis nodes. Two concrete witnesses are a
repeated `(9.0, 9.0)` energy request and a capped `3.0625 eV` request that
lands on an existing `1.75` node. The existing cylindrical quadrature
rejects both returned meshes because `vr` is not strictly increasing.
SciRel rejects those inputs or final axes with `ValueError`; it retains the
saved finite real-valued formula and index lifecycle on the accepted domain.
The initial regression run had 20 failures and 17 passes; one failure was a
test assertion treating the symmetric axial index array as a scalar, and
was corrected without changing its numerical expectation. The other
failures demonstrated the declared input and duplicate-axis divergences.

## Verification boundary

- Source-free direct contract tests: 37 passed, including the quadrature,
  seed and moment composition.
- `pwsh ./scripts/check.ps1 -Mode affected` selected six test files and
  passed 117 tests without full-suite fallback.
- All 29 exact documents passed source-runtime and executable-example
  validation. The catalog is a partial `29/76` development pilot at
  `0.1.0.dev5`.
- The release gate's static counts were updated from `28/75` to `29/76` and
  its maintained test passed. No release was executed or certified.

The saved bundle's strict D1 qualification remains withdrawn, so replay is
bounded historical development evidence. Whether a future mesh contract
should deduplicate requested energies rather than reject them requires
expert decision. Licensing, expert recognition and release remain pending.
