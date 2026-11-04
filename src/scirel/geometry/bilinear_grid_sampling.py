"""Source-faithful bilinear R-Z sampling used by SciRel diagnostics."""
import numpy as np

def _axes(r_grid, z_grid):
    r_grid = np.asarray(r_grid, dtype=float)
    z_grid = np.asarray(z_grid, dtype=float)
    if r_grid.ndim != 2 or z_grid.ndim != 2 or r_grid.shape != z_grid.shape:
        raise ValueError('R and Z must be same-shape 2-D arrays')
    if r_grid.shape[0] < 2 or r_grid.shape[1] < 2:
        raise ValueError('R-Z grid must contain at least 2 rows and 2 columns')
    if not np.all(np.isfinite(r_grid)) or not np.all(np.isfinite(z_grid)):
        raise ValueError('R and Z must contain only finite values')
    if not np.allclose(r_grid, r_grid[0:1, :], rtol=1e-12, atol=1e-14):
        raise ValueError('R must be constant along each grid column')
    if not np.allclose(z_grid, z_grid[:, 0:1], rtol=1e-12, atol=1e-14):
        raise ValueError('Z must be constant along each grid row')
    r_axis, z_axis = (r_grid[0], z_grid[:, 0])
    if np.any(np.diff(r_axis) <= 0.0) or np.any(np.diff(z_axis) <= 0.0):
        raise ValueError('R and Z axes must be strictly increasing')
    return (r_grid, z_grid, r_axis, z_axis)

def sample_rectilinear_field(r_grid, z_grid, quantity, points):
    """Bilinearly sample a scalar R-Z field at caller-owned diagnostic points."""
    r_grid, z_grid, r_axis, z_axis = _axes(r_grid, z_grid)
    quantity = np.asarray(quantity, dtype=float)
    points = np.asarray(points, dtype=float)
    if quantity.shape != r_grid.shape or not np.all(np.isfinite(quantity)):
        raise ValueError('quantity must be finite and have the same shape as R and Z')
    if points.ndim != 2 or points.shape[1] != 2 or (not np.all(np.isfinite(points))):
        raise ValueError('points must be a finite array with shape (n_points, 2)')
    output = np.empty(points.shape[0], dtype=float)
    for index, (r_value, z_value) in enumerate(points):
        if r_value < r_axis[0] or r_value > r_axis[-1] or z_value < z_axis[0] or (z_value > z_axis[-1]):
            raise ValueError('diagnostic point lies outside the R-Z grid')
        r_index = int(np.clip(np.searchsorted(r_axis, r_value) - 1, 0, r_axis.size - 2))
        z_index = int(np.clip(np.searchsorted(z_axis, z_value) - 1, 0, z_axis.size - 2))
        r0, r1 = (r_axis[r_index], r_axis[r_index + 1])
        z0, z1 = (z_axis[z_index], z_axis[z_index + 1])
        r_fraction = 0.0 if r1 == r0 else (r_value - r0) / (r1 - r0)
        z_fraction = 0.0 if z1 == z0 else (z_value - z0) / (z1 - z0)
        q00 = quantity[z_index, r_index]
        q10 = quantity[z_index, r_index + 1]
        q01 = quantity[z_index + 1, r_index]
        q11 = quantity[z_index + 1, r_index + 1]
        output[index] = (1.0 - r_fraction) * (1.0 - z_fraction) * q00 + r_fraction * (1.0 - z_fraction) * q10 + (1.0 - r_fraction) * z_fraction * q01 + r_fraction * z_fraction * q11
    return {'samples': output}
__all__ = ['sample_rectilinear_field']
