# KN1DPy transport-step development integration

Status: development baseline candidate for expert review, not qualified
whole-source D1 intake, expert approval or public release. SciRel comparison
base: `1bf98aa`. Intake remains at `647d5db`, with `pending_unapproved`
documents; the qualified whole-source D1 delivery root is empty.

## Scientific boundary

Three distinct operators are added: forward/backward first-order upwind
coefficient assembly, bidirectional propagation of one first-flight or
scattered generation, and explicit Boltzmann RHS assembly. The propagation
callable accepts six coefficient arrays. It does not import or invoke the
coefficient assembler, so the exact documents declare no callable dependency;
the port composition is covered by the direct test and document example.
The RHS takes caller-supplied source and loss fields and does not solve or
iterate the transport equation. No TaskGraph, convergence loop or implicit
state is added.

The saved recurrence starts positive-vx first flight from `incoming_boundary`
and leaves the negative-vx right boundary at zero. Positive-vx first flight
uses `Fk`, scattered propagation uses `Bk`; the corresponding negative-vx
terms are `Gk` and `Dk`. The boundary may carry finite signed cells. SciRel
retains this arithmetic and the source's ordering on valid finite cases.

## Source comparison and limits

The archived files under `D1待重审历史产物/KN1DPy-631d0bf1/operators/`
matched the intake SHA-256 pins: upwind
`b7b2979415f82d64fb9f963d1c6e531a9ff6353b8d93e209d3370b34db721bf2`,
propagation
`9d24a06959b37deaa142857bf75bb545c1bedcdbd9ec54f721c62387698c1a13`,
and RHS
`fc47ee0a4c5ad0668844cc0ca30bf6ba4b3fc3530e8ca393e60642d8cf9e95fa`.
The archived direct tests passed 1, 2 and 2 cases respectively. Four
read-only intake replays against the isolated SciRel import passed; they
compare normal coefficient, both propagation-kind and RHS outputs bit for
bit and selected rejection behavior. This is bounded historical development
evidence, not a new D1 freeze or an external PDE/physics oracle.

SciRel rejects boolean, string and complex coercions. It also rejects
non-finite results reached from finite inputs; upwind additionally rejects
unrepresentable spatial steps. The intake already documented NaN axis
rejections and a named `ValueError` for zero spatial nodes in propagation.
These are explicit failure-domain tightenings, not claims of numerical
equivalence for invalid or overflowed inputs. The archived `operator.md`
pages include generic examples with incompatible shapes or branch choices,
so the pinned implementation and runnable direct tests bound the comparison.

## Verification

- The direct regression first failed at collection because the public
  callables were absent. After implementation, source-free tests cover the
  formulas, both branches, signed and right-boundary behavior, input types,
  overflow and invalid shapes (18 passed).
- `pwsh ./scripts/check.ps1 -Mode affected` selects the three direct assets,
  public surface, exact documentation, affected selection and release-count
  tests without full-suite fallback (99 passed).
- All 34 `scirel.asset-document.v1` records pass runtime and executable
  example validation. The catalog remains a partial `34/81` development
  pilot at `0.1.0.dev5`; no release was run.

KN1DPy's strict whole-source D1 qualification is withdrawn. Expert review,
version-level trust, external transport validation and distribution licensing
remain pending.
