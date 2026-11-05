"""One axisymmetric Picard flux update over a declared R--Z grid."""

from __future__ import annotations

import numpy as np

from ._anisotropic_numerics import cell_areas

__all__ = ["update_axisymmetric_picard_flux"]


def update_axisymmetric_picard_flux(
    r_grid,
    z_grid,
    j_phi,
    psi_state,
    psi_vac,
    g_psi,
    relax,
    previous_cell_currents=None,
    *,
    cell_edges=None,
):
    """Integrate current, apply the Green response, and report residuals."""
    arrays = [
        np.asarray(value, dtype=float) for value in (r_grid, z_grid, j_phi, psi_state, psi_vac)
    ]
    shape = arrays[0].shape
    if any(
        value.ndim != 2 or value.shape != shape or not np.all(np.isfinite(value))
        for value in arrays
    ):
        raise ValueError(
            "R, Z, j_phi, psi_state, and psi_vac must be finite same-shape [Z,R] arrays"
        )
    r_grid, z_grid, j_phi, psi_state, psi_vac = arrays
    r_axis, z_axis = r_grid[0], z_grid[:, 0]
    if (
        r_axis.size < 3
        or z_axis.size < 3
        or not np.allclose(r_grid, r_axis[None, :])
        or not np.allclose(z_grid, z_axis[:, None])
        or r_axis[0] < 0.0
        or np.any(np.diff(r_axis) <= 0.0)
        or np.any(np.diff(z_axis) <= 0.0)
    ):
        raise ValueError(
            "a finite nonnegative strictly increasing rectilinear R-Z grid with at least 3 points per axis is required"
        )
    green = np.asarray(g_psi, dtype=float)
    if green.shape != (r_grid.size, r_grid.size) or not np.all(np.isfinite(green)):
        raise ValueError(f"g_psi must have shape ({r_grid.size}, {r_grid.size}) and finite entries")
    relaxation = float(relax)
    if not np.isfinite(relaxation) or not 0.0 <= relaxation < 1.0:
        raise ValueError("relax must lie in [0, 1)")

    raw_currents = j_phi * cell_areas(r_grid, z_grid, cell_edges)
    old = (
        np.zeros_like(raw_currents)
        if previous_cell_currents is None
        else np.asarray(previous_cell_currents, dtype=float)
    )
    if old.shape != shape or not np.all(np.isfinite(old)):
        raise ValueError("previous_cell_currents must be finite with shape [N_Z,N_R]")

    candidate = psi_vac + (green @ raw_currents.ravel()).reshape(shape)
    psi_next = relaxation * psi_state + (1.0 - relaxation) * candidate
    tiny = np.finfo(float).tiny
    relative_psi_change = float(
        np.linalg.norm(psi_next - psi_state)
        / max(np.linalg.norm(psi_next), np.linalg.norm(psi_vac), tiny)
    )
    fixed_point_residual = float(
        np.linalg.norm(candidate - psi_state)
        / max(np.linalg.norm(candidate), np.linalg.norm(psi_vac), tiny)
    )
    relative_current_change = float(
        np.linalg.norm(raw_currents - old) / max(np.linalg.norm(raw_currents), 1.0)
    )
    return {
        "psi_next": psi_next,
        "plasma_cell_currents": raw_currents,
        "relative_psi_change": relative_psi_change,
        "relative_current_change": relative_current_change,
        "fixed_point_residual": fixed_point_residual,
    }
