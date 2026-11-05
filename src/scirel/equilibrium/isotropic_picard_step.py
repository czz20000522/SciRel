"""One finite isotropic pressure-current/Green update."""

from __future__ import annotations

import numpy as np

from ._pressure_current import current_target, relaxed_green_update

__all__ = ["pressure_flux_picard_step"]


def pressure_flux_picard_step(
    r_grid, z_grid, psi_state, psi_vac, g_psi, pressure_derivative, psi_edge, currents_old, relax
):
    """Advance one current, Green-flux, and normalized residual step."""
    r_grid, z_grid, psi_state, psi_vac = [
        np.asarray(value, dtype=float) for value in (r_grid, z_grid, psi_state, psi_vac)
    ]
    if r_grid.ndim != 2 or any(
        value.shape != r_grid.shape for value in (z_grid, psi_state, psi_vac)
    ):
        raise ValueError("r_grid, z_grid, psi_state and psi_vac must be same-shape [Z,R] grids")
    if any(not np.all(np.isfinite(value)) for value in (r_grid, z_grid, psi_state, psi_vac)):
        raise ValueError("r_grid, z_grid, psi_state and psi_vac must be finite")

    r_axis, z_axis = r_grid[0], z_grid[:, 0]
    uniform_r = np.allclose(np.diff(r_axis), np.diff(r_axis)[0], rtol=1e-12, atol=1e-14)
    uniform_z = np.allclose(np.diff(z_axis), np.diff(z_axis)[0], rtol=1e-12, atol=1e-14)
    if (
        r_axis.size < 2
        or z_axis.size < 2
        or not np.allclose(r_grid, r_axis[None, :])
        or not np.allclose(z_grid, z_axis[:, None])
        or np.any(np.diff(r_axis) <= 0.0)
        or np.any(np.diff(z_axis) <= 0.0)
        or not uniform_r
        or not uniform_z
    ):
        raise ValueError("r_grid and z_grid must be uniformly spaced tensor-product grids")

    size = r_grid.size
    green = np.asarray(g_psi, dtype=float)
    if green.shape != (size, size) or not np.all(np.isfinite(green)):
        raise ValueError(f"g_psi must have shape ({size}, {size}) and finite values")
    derivative = np.asarray(pressure_derivative, dtype=float).reshape(-1)
    old = (
        np.zeros(size, dtype=float)
        if currents_old is None
        else np.asarray(currents_old, dtype=float).reshape(-1)
    )
    if derivative.shape != (size,) or old.shape != (size,):
        raise ValueError("pressure_derivative and currents_old must have one value per grid cell")
    if not np.all(np.isfinite(derivative)) or not np.all(np.isfinite(old)):
        raise ValueError("pressure_derivative and currents_old must be finite")
    relaxation = float(relax)
    if not np.isfinite(relaxation) or not 0.0 <= relaxation <= 1.0:
        raise ValueError("relax must be between 0 and 1")
    edge = float(psi_edge)
    if not np.isfinite(edge) or edge == 0.0:
        raise ValueError("psi_edge must be finite and non-zero")
    dr = abs(float(r_grid[0, 1] - r_grid[0, 0]))
    dz = abs(float(z_grid[1, 0] - z_grid[0, 0]))
    if not np.isfinite(dr) or not np.isfinite(dz) or dr == 0.0 or dz == 0.0:
        raise ValueError("r_grid and z_grid must have nonzero finite spacing")

    target = old if relaxation == 1.0 else current_target(r_grid.ravel(), derivative, dr, dz)
    currents, flux = relaxed_green_update(target, old, relaxation, green, psi_vac.ravel())
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        residual = float(np.linalg.norm(flux - psi_state.ravel()) / abs(edge))
    if not np.isfinite(residual):
        raise FloatingPointError("nonfinite normalized flux-update residual")
    return {
        "plasma_currents": currents,
        "psi_next": flux.reshape(r_grid.shape),
        "residual": residual,
    }
