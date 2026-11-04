# KN1DPy cross-mesh distribution development integration

Status: development baseline candidate for expert review, not qualified
whole-source D1 intake, expert approval or public release. SciRel comparison
base: `64aa495`. Intake remains clean at `647d5db` with `pending_unapproved`
documents; the qualified whole-source D1 delivery root is empty.

## Scientific boundary

The [exact document](../../catalog/examples/scirel.kinetic.cross-mesh-distribution-interpolation.json)
defines the source-specific H/H2 phase-space handoff: cylindrical velocity-cell
overlap weights, spatial linear interpolation, optional AN/BN moment correction
and density rescale. SciRel reuses its existing cylindrical quadrature asset
for the source's `make_dvr_dvx` relation. The dependency is explicit in the
exact document and affected-test reverse closure. No transport solver or
TaskGraph is added.

The saved correction's update state is the current distribution slice and
AN/BN perturbation at each target spatial node. It computes moments, chooses
the signed perturbation and step `s`, updates the slice, and stops when
`s >= 1`. The saved loop has no finite iteration guarantee. SciRel limits it
to `max_correction_iterations` updates per node (default 1000); exhaustion
raises `ValueError` without returning a partial distribution.

## Source comparison and limits

The archived implementation at
`D1待重审历史产物/KN1DPy-631d0bf1/operators/跨网格分布插值/scientific_operator.py`
matched SHA-256
`c93f491369b36e237c35c10528a82af9f33de2db730f9a3a8054dace6dca5a43`.
An isolated `src/` import matched the saved arrays exactly for two phase-space
mesh cases with each `correct` branch, plus repeated-call and basic rejection
replays. Reusing quadrature did not alter these valid-domain arrays.

A deterministic positive input built with NumPy seed 0 needs more than one
correction update: a limit of 1 raises at target x index 0. With the default
limit it finishes, but both saved and SciRel implementations return 37 negative
cells among 140, minimum about `-740.8`. This is the saved algorithm's
behavior, not a quadrature-reuse difference. The output is an algebraic
transfer with no nonnegativity guarantee; consumers requiring a physical
nonnegative distribution must check it or use another validated transfer.
No external atomic-physics reference or general interpolation-error bound is
claimed.

SciRel also fails closed on boolean/string/complex coercions, nonnegative
radial and two-sided axial mesh requirements, selector types, unrepresentable
temperature scaling, and non-finite intermediate or final results. The source
does not enforce these contracts uniformly. The saved formal operator has no
cache branch; the original runtime's cache lifecycle is outside this replay.

## Verification boundary

- Failed-first focused run stopped at the missing public import. Source-free
  direct regressions (32 passed) cover independent analytic cylindrical moments, branch
  selection, determinism, input contracts, bounded exhaustion and the
  negative-output witness.
- `pwsh ./scripts/check.ps1 -Mode affected` selected the direct contract,
  catalog, public surface, selector and release-environment tests without
  full-suite fallback: 113 passed.
- All 31 exact documents passed source-runtime and executable-example
  validation. The catalog is a partial `31/78` development pilot at
  `0.1.0.dev5`; the release gate's static counts were updated. No release was
  executed.

Archived replay is bounded historical development evidence because KN1DPy's
strict D1 qualification remains withdrawn. Expert recognition, the physical
use of signed outputs, licensing and public release remain pending.
