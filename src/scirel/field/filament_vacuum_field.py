"""Corrected ideal-filament field with preserved radial flux quadrature."""
from __future__ import annotations
import numpy as np
from scirel.electromagnetism.greens import compute_greens

def integrate_filament_vacuum_field(r_grid, z_grid, filaments):
    """Evaluate ideal-filament B and the preserved radial-trapezoid psi.

    BR/BZ use the corrected actual-coordinate loop relation, including nonzero
    near-axis BR and no artificial elliptic cap or radius offset. Active exact
    filament coincidence raises. psi remains the source's uniform radial
    trapezoid integral of R*BZ, with zero reference at the first supplied R.
    This numerical producer differs from direct analytic R*A_phi and is not
    replaced by it. psi units are Wb/rad, magnetic fields T, currents A.
    保留径向离散磁通生产者及首半径零参考，只修磁场核的近轴/近丝错误。
    """
    if any(np.iscomplexobj(x) for x in (r_grid,z_grid,filaments)):
        raise ValueError('grid coordinates and filament currents must be real')
    r_grid = np.asarray(r_grid, dtype=float)
    z_grid = np.asarray(z_grid, dtype=float)
    filaments = np.asarray(filaments, dtype=float)
    if filaments.size == 0:
        filaments = np.empty((0, 3), dtype=float)
    if r_grid.ndim != 2 or z_grid.shape != r_grid.shape or min(r_grid.shape) < 2:
        raise ValueError('r_grid and z_grid must be equal-shape 2-D grids with at least two points per axis')
    if filaments.ndim != 2 or filaments.shape[1] != 3:
        raise ValueError('filaments must have shape (n_filaments, 3) = (R0_m, Z0_m, current_A)')
    if not np.all(np.isfinite(r_grid)) or not np.all(np.isfinite(z_grid)) or (not np.all(np.isfinite(filaments))):
        raise ValueError('grid and filament values must be finite')
    if np.any(filaments[:, 0] <= 0.0):
        raise ValueError('filament cylindrical radii must be strictly positive')
    radial_varies_axis_1 = np.any(r_grid != r_grid[:, :1])
    radial_varies_axis_0 = np.any(r_grid != r_grid[:1, :])
    if radial_varies_axis_1 == radial_varies_axis_0:
        raise ValueError('r_grid must be a rectilinear radial coordinate varying along exactly one axis')
    radial_axis = 1 if radial_varies_axis_1 else 0
    radial = r_grid[0, :] if radial_axis == 1 else r_grid[:, 0]
    expected_r = radial[np.newaxis, :] if radial_axis == 1 else radial[:, np.newaxis]
    if np.any(radial < 0.0) or np.any(np.diff(radial) <= 0.0) or (not np.array_equal(r_grid, np.broadcast_to(expected_r, r_grid.shape))):
        raise ValueError('r_grid must be a nonnegative, strictly increasing rectilinear radial coordinate')
    if radial_axis == 1:
        if not np.allclose(z_grid, z_grid[:, :1]):
            raise ValueError('z_grid must be rectilinear when R varies along axis 1')
    elif not np.allclose(z_grid, z_grid[:1, :]):
        raise ValueError('z_grid must be rectilinear when R varies along axis 0')
    spacing_values = np.diff(radial)
    if not np.allclose(spacing_values, spacing_values[0], rtol=1e-12, atol=1e-14):
        raise ValueError('radial flux quadrature requires a uniformly spaced radial axis')
    points = np.column_stack((r_grid.ravel(),z_grid.ravel()))
    _,br_flat,bz_flat = compute_greens(filaments,points)
    b_r,b_z = br_flat.reshape(r_grid.shape),bz_flat.reshape(r_grid.shape)
    psi = np.zeros_like(r_grid)
    spacing = float(radial[1] - radial[0])
    if radial_axis == 1:
        integrand = radial * b_z
        for index in range(1, r_grid.shape[1]):
            psi[:, index] = psi[:, index - 1] + 0.5 * (integrand[:, index - 1] + integrand[:, index]) * spacing
    else:
        integrand = radial[:, np.newaxis] * b_z
        for index in range(1, r_grid.shape[0]):
            psi[index, :] = psi[index - 1, :] + 0.5 * (integrand[index - 1, :] + integrand[index, :]) * spacing
    if not all((np.all(np.isfinite(value)) for value in (psi, b_r, b_z))):
        raise FloatingPointError('filament field evaluation produced a nonfinite result')
    return {'psi': psi, 'b_r': b_r, 'b_z': b_z}
__all__ = ['integrate_filament_vacuum_field']
