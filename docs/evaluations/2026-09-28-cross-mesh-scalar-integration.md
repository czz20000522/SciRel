# KN1DPy cross-mesh scalar interpolation development integration

Status: development baseline candidate for expert review, not qualified
whole-source D1 intake, expert approval or public release. The SciRel comparison
base is `20f973d`; intake is the clean `647d5db` snapshot with
`pending_unapproved` documents. The qualified D1 delivery root was empty.

## Scientific boundary

The [exact document](../../catalog/examples/scirel.kinetic.cross-mesh-scalar-interpolation.json)
defines the one-dimensional H/H2 spatial scalar handoff. Target nodes inside
the source mesh receive SciPy linear interpolation; nodes outside it remain
exactly zero. This is not conservative remapping or the separate phase-space
distribution transfer. The selected in-range target indices must be contiguous,
but their coordinates may be unsorted. The warning selector retains the saved
`do_warn * max(abs(fb))` threshold and never changes the interpolated values.
The operator has no callable asset dependency or TaskGraph binding.

## Source and failure differences

The archived KN1DPy implementation at
`D1待重审历史产物/KN1DPy-631d0bf1/operators/跨网格标量插值/scientific_operator.py`
matched the intake SHA-256 pin
`01a014fe9b733d6afc6b9ce1216baed292a8cc9f79c0a45d6b89d5f9236bffa7`.
With the isolated SciRel `src/` path asserted, six random finite meshes and
one unsorted-but-contiguous in-range case matched the saved return arrays
exactly.

The saved arm accepts boolean and numeric-string coercions, discards the
imaginary part of a complex NumPy array with a warning (while a complex list
raises `TypeError`), and raises a raw broadcast `ValueError` when in-range
target indices have holes. SciRel rejects these inputs with named `ValueError`s
under its real-input and contiguous-selection contract. It also rejects
one-node source meshes and non-integer warning selectors before the saved
arm's later or implicit behavior. The first focused regression failed
at the missing public import; after implementation, a test mistakenly used
`do_warn=1` as a forced-warning switch. It was corrected to `-1` to exercise
the actual saved threshold without changing the interpolation arithmetic.

## Verification boundary

- Direct source-free contract tests: 21 passed, covering the closed-form
  linear profile, zero fill, affine invariance, unsorted contiguous nodes,
  warning behavior and declared rejections.
- `pwsh ./scripts/check.ps1 -Mode affected` selected six test files and passed
  101 tests without full-suite fallback.
- All 30 exact documents passed source-runtime and executable-example
  validation. The catalog remains a partial `30/77` development pilot at
  `0.1.0.dev5`.
- The release gate's static counts were updated to `30/77`; no release was
  executed. `git diff --check` passed in the isolated worktree.

The saved bundle's strict D1 qualification remains withdrawn. The exact
comparison is bounded historical development evidence. Scientific review,
licensing and public release remain pending.
