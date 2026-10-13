"""Reflection-symmetric plasma-cell flux Green matrix from SciRel ``get_gpsi``."""
from __future__ import annotations
import numpy as np
from scirel.electromagnetism.greens import get_gpsi

def build_mirror_plasma_flux_green(r_grid, z_grid):
    """Build ``g_psi[target_cell,source_cell]`` from actual coordinates.

    Retains this asset's increasing rectilinear, symmetric uniform-Z domain.
    The corrected kernel evaluates each coordinate pair directly, not reflected
    blocks, and retains every positive loop radius. Diagonal and zero-radius
    source columns use the declared discrete zero convention. Other arithmetic
    failures raise. psi=R*A_phi units are Wb/rad per ampere; source currents and
    cell-area quadrature remain caller responsibilities.
    原反射索引与近轴剔除改为实际坐标核，不改变此镜像专用入口的几何域。
    """
    if np.iscomplexobj(r_grid) or np.iscomplexobj(z_grid):
        raise ValueError('grid coordinates must be real')
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
    g_psi = get_gpsi(r_grid,z_grid)
    return {'g_psi': g_psi}
__all__ = ['build_mirror_plasma_flux_green']
