# KN1DPy collision-matrix development integration

Status: development baseline candidate for expert review. SciRel base:
`8272105`; saved KN1DPy bundle remains a pending, unapproved source. The
atomic and molecular matrix operators depend on the seven cross-section leaves
integrated at `dd8bab4`; their four dependencies per matrix are declared in
the exact documents.

## Scientific boundary

- Both operators retain five theta nodes, the source's double-velocity
  predecessor geometry, source-side weights and Fortran-order flattening.
  Four `(nvr*nvx, nvr*nvx)` matrices and the six predecessor/normalization
  fields are returned. Signed elastic cells are not clamped.
- The atomic matrices bind the H/H+ CX, H-H viscosity, H-H2 and H+-H public
  cross-section leaves. The molecular matrices bind H2/H2+ CX, H-H2, H2-H+
  and H2-H2 viscosity leaves. The two leaves that return a leading singleton
  axis have that axis removed explicitly at the matrix call site.
- Molecular SIG_CX retains `H_MASS*Vth2/Q`, with no `0.5` or `mu`; the atomic
  CX factor is `0.5*H_MASS*Vth2/Q`. The other molecular factors and `/8`
  viscosity path retain their saved values. The difference is an expert
  question, not an inferred physical correction.
- The saved formal implementations accepted a reversed positive `vr` despite
  declaring it strictly increasing, coerced boolean/string carrier cells,
  and relied on NumPy conversion for size-one `Tnorm`/`mu` arrays. Each
  integrated operator rejects those inputs with ValueError. The normalized
  velocity axes and weights require real numeric dtypes; `Tnorm` and `mu`
  require finite positive real scalars.
- A finite positive `Tnorm` can underflow the saved thermal-speed calculation
  to zero. Both maintained operators reject that nonrepresentable result
  before assembling matrices; the saved arm returned a zero `Vth2`. A finite
  positive `mu` can also underflow the saved mass denominator to zero; the
  maintained operators report ValueError instead of leaking ZeroDivisionError.
- The saved operator documents contain a generic example that treats the
  returned mapping as a numeric array and provides mismatched carrier lengths.
  The exact documents instead describe the actual keyed result and run
  executable examples against the maintained API.

## Comparison and verification

The saved implementation files are pinned by SHA-256:

- atomic `80fcd63681d255fbe6a2a0fc2e400d63143c9809099d1181bb30ef3266a956fe`;
- molecular `34358f11e3ee91fa6768c8cf89d22eb1a2edbe2707f9e58d0b91472bf1b50d06`.

The copied independent broadcast-geometry tests retain their `rtol=1e-12`,
`atol=0` matrix assertions and pass after binding the maintained cross-section
leaves. Six new scalar/ordering regressions failed before repair; four array
  dtype regressions, two mixed-list boolean regressions and two thermal
  underflow regressions also failed before their respective repairs. The
  direct matrix tests now pass 31 cases. The SHA-gated historical replay passes
8 cases, comparing both matrices on two grids (including `mu=2`) and
witnessing the reversed-radial-axis and thermal-underflow repairs.

The isolated `affected` run selected both matrix assets and their direct and
historical tests without full-suite fallback: 153 passed, 8 optional replay
tests skipped with no saved root set. All 55 exact documents passed schema,
source-runtime and executable-example validation. The development catalog is
`partial: 55/102` at `0.1.0.dev5`; no release or wheel was built.

These checks establish bounded agreement with the saved formulas and the
stated input/shape contracts. They do not establish collision-operator moment
conservation, positivity, external cross-section validity, source-wide strict
D1 qualification, expert approval or public distribution licensing. Atomic
and molecular Omega aggregation remain separate pending relations.
