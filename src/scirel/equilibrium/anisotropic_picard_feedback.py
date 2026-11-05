"""Single anisotropic Picard current relaxation and Green feedback step."""

from __future__ import annotations

import numpy as np

from ._anisotropic_numerics import cell_areas, flux_field_increment

__all__ = ["update_anisotropic_picard_flux"]


def _finite_field(name, value, shape):
    array = np.asarray(value, dtype=float)
    if array.shape != shape or not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must be a finite [Z,R] array with shape {shape}")
    return array


def _green_matrix(name, value, size, required):
    if value is None:
        if required:
            raise ValueError(f"{name} is required")
        return None
    matrix = np.asarray(value, dtype=float)
    if matrix.shape != (size, size) or not np.all(np.isfinite(matrix)):
        raise ValueError(f"{name} must have shape ({size}, {size}) and finite entries")
    return matrix


def update_anisotropic_picard_flux(
    j_phi,
    r_grid,
    z_grid,
    plasma_mask,
    currents_old,
    relax,
    g_psi,
    g_br,
    g_bz,
    psi_vac,
    br_vac,
    bz_vac,
    *,
    cell_edges=None,
):
    """Relax toroidal currents and map them to flux and poloidal fields.

    ``g_br`` and ``g_bz`` may be omitted together; in that case the field
    increment is differentiated from the same Green-produced flux increment.

    Notes
    -----
    ``plasma_mask`` is an explicit domain selector. For a supplied boolean
    ``[N_Z,N_R]`` mask, True cells preserve ``j_phi`` and False cells are
    replaced by zero before cell weighting and current relaxation. ``None``
    treats every cell as active. Invalid masks raise ``ValueError``; the zero
    values are a declared domain boundary, not a numerical-failure fallback.
    """
    r_grid = np.asarray(r_grid, dtype=float)
    if r_grid.ndim != 2:
        raise ValueError("r_grid must be a two-dimensional [Z,R] grid")
    shape = r_grid.shape
    r_grid = _finite_field("r_grid", r_grid, shape)
    z_grid = _finite_field("z_grid", z_grid, shape)
    j_phi = _finite_field("j_phi", j_phi, shape)
    psi_vac = _finite_field("psi_vac", psi_vac, shape)
    br_vac = _finite_field("br_vac", br_vac, shape)
    bz_vac = _finite_field("bz_vac", bz_vac, shape)
    if not np.allclose(r_grid, r_grid[0:1, :]) or not np.allclose(z_grid, z_grid[:, 0:1]):
        raise ValueError("r_grid and z_grid must be tensor-product [Z,R] grids")
    if shape[0] < 2 or shape[1] < 2:
        raise ValueError("r_grid and z_grid need at least two points per axis to define cell area")

    areas = cell_areas(r_grid, z_grid, cell_edges)
    size = r_grid.size
    old = (
        np.zeros(size, dtype=float)
        if currents_old is None
        else np.asarray(currents_old, dtype=float)
    )
    if old.shape != (size,) or not np.all(np.isfinite(old)):
        raise ValueError(f"currents_old must have finite shape ({size},)")
    relaxation = float(relax)
    if not np.isfinite(relaxation) or not 0.0 <= relaxation <= 1.0:
        raise ValueError("relax must be a finite scalar in [0,1]")
    if (g_br is None) != (g_bz is None):
        raise ValueError("g_br and g_bz must be provided together")
    green_psi = _green_matrix("g_psi", g_psi, size, True)
    green_br = _green_matrix("g_br", g_br, size, False)
    green_bz = _green_matrix("g_bz", g_bz, size, False)

    density = j_phi
    if plasma_mask is not None:
        mask = np.asarray(plasma_mask)
        if mask.dtype != np.dtype(bool) or mask.shape != shape:
            raise ValueError(f"plasma_mask must be boolean with shape {shape}")
        density = np.where(mask, j_phi, 0.0)
    raw_currents = density * areas
    currents = (1.0 - relaxation) * raw_currents.ravel() + relaxation * old
    psi = (psi_vac.ravel() + green_psi @ currents).reshape(shape)

    if green_br is None:
        reverse_z = z_grid[1, 0] < z_grid[0, 0]
        reverse_r = r_grid[0, 1] < r_grid[0, 0]
        order = (
            slice(None, None, -1) if reverse_z else slice(None),
            slice(None, None, -1) if reverse_r else slice(None),
        )
        increment = flux_field_increment(r_grid[order], z_grid[order], (psi - psi_vac)[order])
        br = br_vac + increment["B_R"][order]
        bz = bz_vac + increment["B_Z"][order]
    else:
        br = (br_vac.ravel() + green_br @ currents).reshape(shape)
        bz = (bz_vac.ravel() + green_bz @ currents).reshape(shape)
    return {
        "psi": psi,
        "BR": br,
        "BZ": bz,
        "j_phi": density,
        "initial_picard_current_state": np.zeros(size, dtype=float),
        "picard_current_state": currents,
        "plasma_currents": raw_currents,
    }
