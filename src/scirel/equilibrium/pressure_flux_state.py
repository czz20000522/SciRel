"""Historical exact-midplane pressure spline and derivative state."""
import numpy as np
from scipy.interpolate import InterpolatedUnivariateSpline

def _finite_grid(name, value, shape=None):
    array = np.asarray(value, dtype=float)
    if array.ndim != 2:
        raise ValueError(f'{name} must be a two-dimensional [Z,R] array')
    if shape is not None and array.shape != shape:
        raise ValueError(f'{name} must have shape {shape}')
    if not np.all(np.isfinite(array)):
        raise ValueError(f'{name} must contain only finite values')
    return array

def _representation(spline, psi_samples, pressure_samples):
    knots, coefficients, degree = spline._eval_args
    return {'psi_samples': np.asarray(psi_samples, dtype=float), 'pressure_samples': np.asarray(pressure_samples, dtype=float), 'knots': np.asarray(knots, dtype=float), 'coefficients': np.asarray(coefficients, dtype=float), 'degree': int(degree), 'extrapolation': 'zeros', 'evaluation': "InterpolatedUnivariateSpline(psi_samples, pressure_samples, ext='zeros')"}

def build_pressure_flux_state(r_grid, z_grid, psi, pressure_of_radius, plasma_mask=None):
    """Build one source-order P(psi) state and its clipped current derivative."""
    r_grid = _finite_grid('r_grid', r_grid)
    z_grid = _finite_grid('z_grid', z_grid, shape=r_grid.shape)
    psi = _finite_grid('psi', psi, shape=r_grid.shape)
    if not callable(pressure_of_radius):
        raise ValueError('pressure_of_radius must be callable as pressure_of_radius(R)')
    r_flat, z_flat, psi_flat = (r_grid.ravel(), z_grid.ravel(), psi.ravel())
    z0_indices = np.where(z_flat == 0.0)[0]
    zero_rows = np.where(np.all(z_grid == 0.0, axis=1))[0]
    if zero_rows.size != 1 or z0_indices.size != r_grid.shape[1]:
        raise ValueError('z_grid must contain exactly one complete zero midplane row')
    r_z0 = r_flat[z0_indices]
    pressure_z0 = np.asarray([pressure_of_radius(radius) for radius in r_z0], dtype=float)
    if pressure_z0.ndim != 1 or not np.all(np.isfinite(pressure_z0)) or np.any(pressure_z0 < 0.0):
        raise ValueError('pressure_of_radius must return finite nonnegative scalar values')
    try:
        limiter_index = next((index for index, pressure in enumerate(pressure_z0) if pressure == 0.0))
    except StopIteration as exc:
        raise ValueError('pressure_of_radius must define an exact zero-pressure boundary') from exc
    psi_prefix = psi_flat[z0_indices][:limiter_index + 1]
    if psi_prefix.size < 4 or not np.all(np.diff(psi_prefix) > 0.0):
        raise ValueError('midplane psi samples must be strictly increasing with at least four points')
    spline = InterpolatedUnivariateSpline(psi_prefix, pressure_z0[:limiter_index + 1], ext='zeros')
    pressure_derivative = spline.derivative()(psi_flat)
    pressure_derivative[~np.isfinite(pressure_derivative)] = 0.0
    psi_edge = float(psi_flat[z0_indices][limiter_index])
    pressure_derivative[psi_flat > psi_edge] = 0.0
    if plasma_mask is not None:
        plasma_mask = np.asarray(plasma_mask, dtype=bool)
        if plasma_mask.shape != r_grid.shape:
            raise ValueError('plasma_mask must have the same shape as r_grid')
        pressure_derivative[plasma_mask.ravel()] = 0.0
    return {'pressure_derivative': pressure_derivative, 'zero_currents': np.zeros_like(pressure_derivative), 'psi_edge': psi_edge, 'pressure_of_psi': _representation(spline, psi_flat[z0_indices], pressure_z0), 'limiter_index': limiter_index}
__all__ = ['build_pressure_flux_state']
