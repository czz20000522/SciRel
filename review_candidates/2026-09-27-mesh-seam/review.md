# Candidate: KN1DPy adaptive velocity mesh + cross-mesh scalar seam (two operators)

Status: development candidate prepared for expert review, to be frozen as the
pending_unapproved r61 successor of r60c. Nothing here is expert approval, a
trusted version, or a public release.

## Base and comparison scope

- SciRel base: `913accd` (r60c, KN1DPy neutral-moment diagnostics family,
  110 assets dev32, `pending_unapproved`).
- Unpublished candidate pool: re-checked by relation for velocity-mesh
  constructors and cross-mesh interpolation seams — none exists. The
  baseline has the cylindrical quadrature (a quadrature over an existing
  mesh) but no mesh constructor and no mesh-to-mesh seam; both incoming
  leaves are **new capabilities**.
- Incoming source (read only): the saved KN1DPy bundle
  `D1待重审历史产物/KN1DPy-631d0bf1` (provisional; strict D1 withdrawn),
  implementations pinned by SHA-256 (`38fcde8b…` mesh, `01a014fe…` seam).
  Saved-tree imports read-only; zero writes.
- Qualified L1 consumption: none (delivery root re-checked empty; strict D1
  withdrawn). Bounded historical development evidence only.

## Inventory

| Saved callable | Disposition | Proposed SciRel identity | Material differences | Evidence |
| --- | --- | --- | --- | --- |
| `create_vr_vx_mesh` (`create_vr_vx_mesh.py:16-56`) | add new capability | scirel.kinetic.adaptive-neutral-velocity-mesh | **no repair**; one declared JSON adaptation: `requested_energy_ev` defaults to `None` (JSON-serializable) instead of the empty tuple, treated identically — recorded in the document | direct 7 + replay 3 |
| `interp_scalar_across_mesh` (`interp_scalarx.py`, consumed at `kn1d.py:485-486, 521`) | add new capability | scirel.kinetic.cross-mesh-scalar-interpolation | **no repair** — linear interpolation, out-of-range zero fill (the saved phase-space contract), and the do_warn boundary warnings reproduced | direct 7 + replay 3 |

Why these two and why only these two: they form the minimal closure for the
next deferred layer (mesh construction feeds every transport leaf already
integrated; the seam is the prerequisite for the H<->H2 cross-grid handoff
deferred from earlier batches). The larger cross-grid distribution
interpolation (411 lines) and the per-species source-production assemblies
remain deferred until their upstream chains close.

## Declared adaptations and open questions

- `requested_energy_ev=None` default replaces the saved `()` so the default
  is JSON-serializable in the exact document; behavior is identical for
  both defaults. Recorded as an assumption, flagged for expert review.
- The saved `vmax = 3.5`, the `0.1*Tmax` uniformity threshold, the out-of-
  range zero fill and the cap semantics are preserved verbatim.

## Files

- `proposal/adaptive_neutral_velocity_mesh.py`,
  `proposal/cross_mesh_scalar_interpolation.py`
- `proposal/test_mesh_and_seam.py`, `proposal/test_mesh_and_seam_l1.py`
- `proposal/scirel.kinetic.adaptive-neutral-velocity-mesh.json`,
  `proposal/scirel.kinetic.cross-mesh-scalar-interpolation.json`

## Public API and dependency impact

Two new public callables in `scirel.kinetic` and the root namespace; two new
exact documents; version `0.1.0.dev32` -> `0.1.0.dev33`; catalog 110 -> 112.
The other 110 exact documents change only in the mechanical
`implementation_version` bump. No existing assertion weakened.
