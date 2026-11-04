"""SciRel value-space parallel-pressure equilibrium diagnostic."""
import numpy as np

def _derivative_with_respect_to_field(quantity, field, floor):
    flattened_quantity = np.asarray(quantity, dtype=float).ravel()
    flattened_field = np.asarray(field, dtype=float).ravel()
    order = np.argsort(flattened_field)
    sorted_field = flattened_field[order]
    sorted_quantity = flattened_quantity[order]
    derivative_sorted = np.zeros_like(sorted_quantity)
    if sorted_field.size > 1 and np.ptp(sorted_field) > floor:
        if np.any(np.diff(sorted_field) <= floor):
            raise ValueError('magnetic_field samples must be unique unless all values are equal')
        derivative_sorted = np.gradient(sorted_quantity, sorted_field, edge_order=1)
    derivative = np.empty_like(derivative_sorted)
    derivative[order] = derivative_sorted
    return derivative.reshape(np.shape(field))

def compute_parallel_pressure_residual(p_parallel, p_perp, magnetic_field, rtol=0.01, atol=1e-06, strict=False):
    """Check the pressure relation; reject undefined derivatives and nonfinite results."""
    p_parallel = np.asarray(p_parallel, dtype=float)
    p_perp = np.asarray(p_perp, dtype=float)
    magnetic_field = np.asarray(magnetic_field, dtype=float)
    if p_parallel.shape != p_perp.shape or p_parallel.shape != magnetic_field.shape:
        raise ValueError('p_parallel, p_perp, and magnetic_field must have the same shape')
    if p_parallel.size == 0:
        raise ValueError('parallel-pressure equilibrium requires at least one sample')
    if not all((np.all(np.isfinite(value)) for value in (p_parallel, p_perp, magnetic_field))):
        raise ValueError('p_parallel, p_perp, and magnetic_field must contain only finite values')
    if not np.isfinite(rtol) or not np.isfinite(atol) or rtol < 0.0 or (atol <= 0.0):
        raise ValueError('rtol must be non-negative and atol must be positive finite values')
    rhs = -magnetic_field * magnetic_field * _derivative_with_respect_to_field(p_parallel / np.maximum(magnetic_field, 1e-30), magnetic_field, 1e-30)
    error = p_perp - rhs
    relative_error = np.abs(error) / np.maximum(np.maximum(np.abs(p_perp), np.abs(rhs)), atol)
    if not all(np.all(np.isfinite(value)) for value in (rhs, error, relative_error)):
        raise ValueError('parallel-pressure derivative and residuals must be finite')
    maximum = float(np.max(relative_error))
    mean = float(np.mean(relative_error))
    passed = bool(maximum <= rtol)
    if strict and (not passed):
        raise ValueError('parallel equilibrium check failed')
    return {'rhs': rhs, 'error': error, 'relative_error': relative_error, 'max_relative_error': maximum, 'mean_relative_error': mean, 'passed': passed}
__all__ = ['compute_parallel_pressure_residual']
