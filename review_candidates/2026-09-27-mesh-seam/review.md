# Candidate: KN1DPy cross-mesh distribution interpolation (one operator)

Status: development candidate prepared for expert review, to be frozen as the
pending_unapproved r62 successor of r61. Nothing here is expert approval, a
trusted version, or a public release.

## Base and comparison scope

- SciRel base: `d01820e` (r61b, mesh/seam family + boundary fix, 112 assets
  dev33, `pending_unapproved`).
- Unpublished candidate pool: re-checked by relation for cross-grid
  distribution interpolation — none exists. The baseline has the cross-mesh
  scalar seam (r61) but no distribution-level transfer; the incoming leaf
  is a **new capability**.
- Incoming source (read only): the saved KN1DPy bundle
  `D1待重审历史产物/KN1DPy-631d0bf1` (provisional; strict D1 withdrawn),
  implementation pinned by SHA-256 `c93f491369b36e237c35c10528a82af9f33de2db730f9a3a8054dace6dca5a43`.
- Qualified L1 consumption: none (delivery root re-checked empty; strict D1
  withdrawn). Bounded historical development evidence only.

## Proposed identity

- `scirel.kinetic.cross-mesh-distribution-interpolation`, callable
  `interp_distribution_across_mesh(fa, vr_a, vx_a, x_a, Tnorm_a, vr_b, vx_b,
  x_b, Tnorm_b, correct=1, do_warn=None)`

## Material scientific differences and declared divergences

1. **No cache/w_new in the saved formal operator.** The original source
   runtime has a weight cache lifecycle (w_new=1 build / w_new=0 reuse),
   but the saved formal operator does not carry it — it recomputes the
   weight matrix every call, exactly like the stateless SciRel port.
   Cache-state parity is therefore out of scope for this replay.
2. **Axis validation (declared narrowing).** The saved arm only validates
   vr_a/vr_b monotonicity; x_a/x_b/vx_a/vx_b monotonicity and minimum node
   counts are unvalidated (a single-node vx_a raises a raw IndexError in
   the correction branch). This integration enforces strict monotonicity
   and >= 2 nodes on all six axes, with named ValueError messages.
3. **Tnorm finiteness (declared narrowing).** The saved arm checks
   Tnorm <= 0, so NaN/inf pass silently; this asset requires finite and
   positive Tnorm.
4. **No repair on the declared legal domain.** On inputs satisfying the
   declared contracts, the port reproduces the saved formal operator
   bit for bit (verified by the environment-gated replay across both
   correct branches and repeated calls).

## Evidence

- Independent analytic quadrature in the test oracle: ring areas
  pi*(edges[1:]^2 - edges[:-1]^2) computed from first principles (not from
  the implementation's _make_dvr_dvx), so an error in either would surface
  as a mismatch.
- Moment-target assertions (independent analytic quadrature, not from the implementation): density on mesh_b matches mesh_a density interpolated onto mesh_b x nodes to 1e-9 rtol; axial flow stays zero for vx-symmetric input (atol 1e-12). Energy-moment reproduction is handled by the saved correction loop but is not independently asserted; no external atomic-physics validation is claimed.
- 10 tests total (7 direct + 3 replay); `pytest --collect-only` verified.

## Files

- `proposal/cross_mesh_distribution_interpolation.py`
- `proposal/test_cross_mesh_distribution.py`, `test_cross_mesh_distribution_l1.py`
- `proposal/scirel.kinetic.cross-mesh-distribution-interpolation.json`

## Version and impact

Version `0.1.0.dev34` -> `0.1.0.dev35`; catalog 112 -> 113 exact documents.
The other 112 documents change only in the mechanical `implementation_version`
bump.

## Snapshot-path disclosure (r62 freeze history)

The r62 batch was frozen twice at the same output path
`build/verification/review-2026-09-27-r62-dist-interp-v2/` (the second
freeze overwrote the first in place, violating the fresh-path convention).
Both r62-v2 snapshots are superseded by this r62-v3 successor at a fresh
path. The original manifest bytes of the overwritten attempt cannot be
re-verified.
