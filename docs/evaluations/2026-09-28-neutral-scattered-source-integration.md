# KN1DPy scattered-source development integration

Status: development baseline candidate for expert review. SciRel base:
`1c2dd56`. Intake remains clean at `647d5db` with `pending_unapproved`
documents. The designated qualified whole-source D1 delivery root was empty
on recheck. This is not expert approval or a public release.

## Scientific boundary

Four distinct leaves are added, all with explicit caller ports and no direct
callable dependencies:

- Atomic source reduction sums `Beta_CX + OmegaM`; molecular reduction sums
  `Swall + Beta_CX + OmegaM`. Both keep finite signed cells and the source
  addition order.
- Elastic regeneration aggregation sums each named `Omega_q[x] * M_q` term
  in mapping iteration order. Frequencies and regenerated distributions are
  nonnegative; all channel distributions must share one `(nvr,nvx,nx)` mesh.
- Simple CX source contracts the previous-generation distribution against
  the caller's CX frequency, cylindrical weight and `dvx`, then scales the
  caller's target distribution per spatial cell. Target and previous cells
  may be signed.

No feedback loop, collision matrix construction or transport solver is
hidden in these leaves. Their ports may be composed with existing frequency,
RHS and propagation relations only under a separately reviewed graph.

## Saved comparison

The four archived `KN1DPy-631d0bf1` implementation SHA-256 values matched
their intake pins:

- Atomic two-channel reduction:
  `6fe5d850c7aef5c07f8c5996dc65948a6ba35f1ea10e120dcb6fd28ed61ff159`.
- Molecular three-channel reduction:
  `4b17a8e6a15d2c7ebf4e0fdc58db7e7b81af8c0139687182dbe8c5a9e6542898`.
- Elastic regeneration aggregation:
  `8957adc7a5f0cd11cbdc6b3c6738057adbab660285c38fb2da490db09f7919c0`.
- Simple CX source:
  `b4962366c43c308aa0ca8e047d00fb34ce2756f1db025e14a77339b1de50770f`.

Eight read-only finite-input comparisons asserted the isolated SciRel `src/`
import and matched saved arrays exactly: two mesh sizes for each source sum,
two mapping orders for elastic regeneration and two signed Simple_CX cases.
The four archived package tests each passed one case when run from their own
saved directories with bytecode and pytest cache writes disabled. Their
fixed numerical assertions are retained in the source-free direct test.
Three saved-arm witnesses confirmed that the archive returns an overflowing
atomic sum, broadcasts unequal but compatible elastic velocity meshes, and
accepts numeric-string `dvx`. SciRel rejects those cases under its finite
real and shared-mesh contracts. The saved source is historical development
evidence, not a renewed strict D1 freeze or independent physics oracle.

## Verification

- The new direct test failed at import before implementation, then passed
  17 tests covering the saved finite samples, signed cells, channel order, input
  types, alignment, common mesh and derived overflow.
- `pwsh ./scripts/check.ps1 -Mode affected` selected six test files and
  passed **98 tests** without full-suite fallback.
- All 44 exact documents passed source-runtime and executable-example
  validation. The catalog remains `partial: 44/91` at `0.1.0.dev5`; no
  release gate or wheel build was run.

Expert recognition, version-level trust, distribution licensing and full
neutral transport composition remain open.
