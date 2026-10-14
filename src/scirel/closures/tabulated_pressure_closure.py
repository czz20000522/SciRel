"""Tabulated anisotropic or isotropic pressure closure on ``(B, psi)``."""
import numpy as np
from scipy.interpolate import RegularGridInterpolator, interp1d

def evaluate_tabulated_pressure(magnetic_field, psi, psi_grid, p_parallel_table, p_perpendicular_table=None, b_grid=None, bounds_error=True, fill_value=None):
    """Linearly interpolate supplied nonnegative pressure tables.

    ``is_isotropic`` denotes exact equality of the two component tables,
    independent of table dimension. A one-dimensional law requires exact
    equality if both tables are supplied; no anisotropy is silently discarded.
    ``table_dimension`` records whether psi alone or (B, psi) is tabulated.
    Table equality does not certify thermodynamic closure or force balance.
    """
    psi_grid = np.asarray(psi_grid, dtype=float)
    parallel_table = np.asarray(p_parallel_table, dtype=float)
    if psi_grid.ndim != 1 or psi_grid.size < 2 or (not np.all(np.isfinite(psi_grid))) or np.any(np.diff(psi_grid) <= 0.0):
        raise ValueError('psi_grid must be one-dimensional, finite, and strictly increasing')
    if not np.all(np.isfinite(parallel_table)) or np.any(parallel_table < 0.0):
        raise ValueError('pressure tables must be finite and nonnegative')
    if not isinstance(bounds_error, (bool, np.bool_)):
        raise ValueError('bounds_error must be boolean')
    if fill_value is not None:
        fill_array = np.asarray(fill_value, dtype=float)
        if fill_array.ndim != 0 or not np.isfinite(fill_array) or float(fill_array) < 0.0:
            raise ValueError('fill_value must be a finite nonnegative scalar or None')
        fill_value = float(fill_array)
    field, flux = np.broadcast_arrays(np.asarray(magnetic_field, dtype=float), np.asarray(psi, dtype=float))
    if not np.all(np.isfinite(field)) or not np.all(np.isfinite(flux)):
        raise ValueError('magnetic_field and psi must be finite')
    if b_grid is None:
        if parallel_table.shape != psi_grid.shape:
            raise ValueError('an isotropic pressure table must match psi_grid')
        if p_perpendicular_table is not None:
            perpendicular_table = np.asarray(p_perpendicular_table, dtype=float)
            if perpendicular_table.shape != psi_grid.shape or not np.all(np.isfinite(perpendicular_table)) or np.any(perpendicular_table < 0.0):
                raise ValueError('an isotropic perpendicular pressure table must match psi_grid and be finite and nonnegative')
            if not np.array_equal(parallel_table, perpendicular_table):
                raise ValueError('b_grid=None requires equal parallel and perpendicular pressure tables')
        extrapolation = 'extrapolate' if not bounds_error and fill_value is None else fill_value
        interpolator = interp1d(psi_grid, parallel_table, kind='linear', bounds_error=bool(bounds_error), fill_value=np.nan if bounds_error else extrapolation, assume_sorted=True)
        pressure = np.asarray(interpolator(flux), dtype=float)
        if not np.all(np.isfinite(pressure)) or np.any(pressure < 0.0):
            raise ValueError('interpolated pressure must be finite and nonnegative')
        return {'p_parallel': pressure, 'p_perpendicular': pressure.copy(), 'is_isotropic': True, 'table_dimension': 1}
    b_grid = np.asarray(b_grid, dtype=float)
    perpendicular_table = parallel_table if p_perpendicular_table is None else np.asarray(p_perpendicular_table, dtype=float)
    expected_shape = (b_grid.size, psi_grid.size)
    if b_grid.ndim != 1 or b_grid.size < 2 or (not np.all(np.isfinite(b_grid))) or np.any(np.diff(b_grid) <= 0.0):
        raise ValueError('b_grid must be one-dimensional, finite, and strictly increasing')
    if parallel_table.shape != expected_shape or perpendicular_table.shape != expected_shape or (not np.all(np.isfinite(perpendicular_table))) or np.any(perpendicular_table < 0.0):
        raise ValueError('anisotropic pressure tables must be finite nonnegative arrays with shape (len(b_grid), len(psi_grid))')
    options = {'bounds_error': bool(bounds_error), 'fill_value': fill_value}
    points = np.column_stack((field.ravel(), flux.ravel()))
    parallel = RegularGridInterpolator((b_grid, psi_grid), parallel_table, **options)(points).reshape(field.shape)
    perpendicular = RegularGridInterpolator((b_grid, psi_grid), perpendicular_table, **options)(points).reshape(field.shape)
    if not np.all(np.isfinite(parallel)) or not np.all(np.isfinite(perpendicular)) or np.any(parallel < 0.0) or np.any(perpendicular < 0.0):
        raise ValueError('interpolated pressures must be finite and nonnegative')
    return {'p_parallel': parallel, 'p_perpendicular': perpendicular, 'is_isotropic': bool(np.array_equal(parallel_table, perpendicular_table)), 'table_dimension': 2}
__all__ = ['evaluate_tabulated_pressure']
