"""Reflection-symmetric plasma-cell flux Green matrix from SciRel ``get_gpsi``."""
from __future__ import annotations
import numpy as np
from scipy.special import ellipe, ellipk

def build_mirror_plasma_flux_green(r_grid, z_grid):
    """Build the source-compatible dense ``g_psi[target_cell, source_cell]`` matrix."""
    r_grid = np.asarray(r_grid, dtype=float)
    z_grid = np.asarray(z_grid, dtype=float)
    if r_grid.ndim != 2 or z_grid.shape != r_grid.shape or min(r_grid.shape) < 2:
        raise ValueError('r_grid and z_grid must be equal-shape 2-D grids with at least two points per axis')
    if not np.all(np.isfinite(r_grid)) or not np.all(np.isfinite(z_grid)):
        raise ValueError('r_grid and z_grid must be finite')
    radial, axial = (r_grid[0], z_grid[:, 0])
    if not np.allclose(r_grid, radial[np.newaxis, :]) or not np.allclose(z_grid, axial[:, np.newaxis]) or np.any(radial < 0.0) or np.any(np.diff(radial) <= 0.0) or np.any(np.diff(axial) <= 0.0):
        raise ValueError('the source-compatible matrix requires a strictly increasing rectilinear R-Z grid')
    if not np.allclose(axial, -axial[::-1], rtol=0.0, atol=1e-12):
        raise ValueError('the reflection construction requires an axis-reflection-symmetric Z grid')
    if not np.allclose(np.diff(axial), np.diff(axial)[0], rtol=1e-12, atol=1e-14):
        raise ValueError('the reflection construction requires a uniformly spaced Z grid')
    n_z, n_r = r_grid.shape
    targets_r, targets_z = (r_grid.ravel(), z_grid.ravel())
    base = np.zeros((targets_r.size, n_r), dtype=float)
    prefactor = 1e-07
    source_z = axial[0]
    with np.errstate(divide='ignore', invalid='ignore'):
        for source_index, source_r in enumerate(radial):
            if np.isclose(source_r, 0.0, rtol=0.0, atol=1e-12):
                continue
            z_delta_squared = (targets_z - source_z) ** 2
            d_plus = np.sqrt(z_delta_squared + (targets_r + source_r) ** 2)
            k_squared = 4.0 * targets_r * source_r / d_plus ** 2
            flux = prefactor * targets_r * source_r / d_plus * 4.0 / k_squared * ((2.0 - k_squared) * ellipk(k_squared) - 2.0 * ellipe(k_squared))
            flux[~np.isfinite(flux)] = 0.0
            base[:, source_index] = flux
    reflected = np.zeros((n_r * (2 * n_z - 1), n_r), dtype=float)
    reflected[(n_z - 1) * n_r:, :] = base
    for reflection_index in range(n_z - 1):
        if reflection_index == 0:
            reflected[:n_r, :] = base[-n_r:, :]
        else:
            reflected[reflection_index * n_r:(reflection_index + 1) * n_r, :] = base[-(reflection_index + 1) * n_r:-reflection_index * n_r, :]
    g_psi = np.zeros((targets_r.size, targets_r.size), dtype=float)
    for source_plane in range(n_z):
        g_psi[:, source_plane * n_r:(source_plane + 1) * n_r] = reflected[(n_z - (source_plane + 1)) * n_r:(2 * n_z - (source_plane + 1)) * n_r, :]
    return {'g_psi': g_psi}
__all__ = ['build_mirror_plasma_flux_green']
