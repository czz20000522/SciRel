"""Flux-surface 1/B measure and weighted average."""
from __future__ import annotations
import numpy as np
from scipy.integrate import trapezoid
from scipy.interpolate import RectBivariateSpline

def compute_flux_surface_inverse_field_average(r_grid, z_grid, magnetic_field, field_line_points, quantity=None):
    """Compute ``dl_B = integral(dl/B)`` and optionally ``<quantity>_B``."""
    r_grid = np.asarray(r_grid, dtype=float)
    z_grid = np.asarray(z_grid, dtype=float)
    magnetic_field = np.asarray(magnetic_field, dtype=float)
    field_line_points = np.asarray(field_line_points, dtype=float)
    if r_grid.ndim != 2 or z_grid.shape != r_grid.shape:
        raise ValueError('r_grid and z_grid must be equal-shape 2-D grids')
    if magnetic_field.shape != r_grid.shape:
        raise ValueError('magnetic_field must match the R-Z grid')
    if field_line_points.ndim != 2 or field_line_points.shape[1] != 2:
        raise ValueError('field_line_points must have shape (n_points, 2)')
    if field_line_points.shape[0] < 2:
        raise ValueError('field_line_points needs at least two points')
    if quantity is not None:
        quantity = np.asarray(quantity, dtype=float)
        if quantity.shape != r_grid.shape:
            raise ValueError('quantity must match the R-Z grid')
    for name, values in (('r_grid', r_grid), ('z_grid', z_grid), ('magnetic_field', magnetic_field), ('field_line_points', field_line_points)):
        if not np.all(np.isfinite(values)):
            raise ValueError(f'{name} must contain only finite values')
    if quantity is not None and (not np.all(np.isfinite(quantity))):
        raise ValueError('quantity must contain only finite values')
    r_axis = r_grid[0, :]
    z_axis = z_grid[:, 0]
    if np.any(np.diff(r_axis) <= 0.0) or np.any(np.diff(z_axis) <= 0.0) or (not np.allclose(r_grid, r_axis[np.newaxis, :])) or (not np.allclose(z_grid, z_axis[:, np.newaxis])):
        raise ValueError('r_grid and z_grid must be strictly increasing rectilinear grids')
    if r_axis.size < 4 or z_axis.size < 4:
        raise ValueError('r_grid and z_grid need at least four points per axis for cubic interpolation')
    if np.any(magnetic_field <= 0.0):
        raise ValueError('magnetic_field must be strictly positive')
    points_r = field_line_points[:, 0]
    points_z = field_line_points[:, 1]
    if np.any(points_r < r_axis[0]) or np.any(points_r > r_axis[-1]) or np.any(points_z < z_axis[0]) or np.any(points_z > z_axis[-1]):
        raise ValueError('field_line_points must lie inside the R-Z grid')
    segment = np.diff(field_line_points, axis=0)
    segment_lengths = np.linalg.norm(segment, axis=1)
    if np.any(segment_lengths <= 0.0):
        raise ValueError('field_line_points must define a nondegenerate polyline without repeated consecutive points')
    interpolator = RectBivariateSpline(z_axis, r_axis, magnetic_field)
    magnetic_values = np.asarray(interpolator(points_z, points_r, grid=False), dtype=float)
    if not np.all(np.isfinite(magnetic_values)) or np.any(magnetic_values <= 0.0):
        raise ValueError('interpolated magnetic field must be finite and strictly positive')
    s = np.concatenate(([0.0], np.cumsum(segment_lengths)))
    dl_B = float(trapezoid(1.0 / magnetic_values, x=s))
    if not np.isfinite(dl_B) or dl_B <= 0.0:
        raise ValueError('dl_B must be finite and strictly positive')
    result = {'dl_B': dl_B}
    if quantity is not None:
        quantity_values = np.asarray(RectBivariateSpline(z_axis, r_axis, quantity)(points_z, points_r, grid=False), dtype=float)
        if not np.all(np.isfinite(quantity_values)):
            raise ValueError('interpolated quantity must be finite')
        flux_surface_average = float(trapezoid(quantity_values / magnetic_values, x=s) / dl_B)
        if not np.isfinite(flux_surface_average):
            raise ValueError('flux_surface_average must be finite')
        result['flux_surface_average'] = flux_surface_average
    return result
__all__ = ['compute_flux_surface_inverse_field_average']
