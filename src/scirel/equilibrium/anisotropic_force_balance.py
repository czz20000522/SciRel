"""Axisymmetric gyrotropic pressure-tensor force and current closure."""
import math
import struct
import numpy as np
MU0 = 4e-07 * np.pi

def _source_hypot(left, right):
    """Reproduce source ``np.hypot`` without finite-range under/overflow."""
    left, right = np.broadcast_arrays(np.asarray(left, dtype=float), np.asarray(right, dtype=float))
    values = []
    for x, y in zip(left.flat, right.flat):
        x, y = (abs(float(x)), abs(float(y)))
        if math.isinf(x) or math.isinf(y):
            values.append(math.inf)
            continue
        if math.isnan(x) or math.isnan(y):
            values.append(math.nan)
            continue
        if x < y:
            x, y = (y, x)
        if x == 0.0:
            values.append(0.0)
            continue
        _, exponent = math.frexp(x)
        x = math.ldexp(x, -exponent)
        y = math.ldexp(y, -exponent)
        bits = struct.unpack('>Q', struct.pack('>d', x))[0] & 18446744073575333888
        high = struct.unpack('>d', struct.pack('>Q', bits))[0]
        low = x - high
        scaled = math.sqrt(high * high - (y * -y - low * (x + high)))
        try:
            values.append(math.ldexp(scaled, exponent))
        except OverflowError:
            values.append(math.inf)
    return np.asarray(values, dtype=float).reshape(left.shape)

from ._anisotropic_numerics import stable_gradient as _source_gradient, pressure_divergence, residual_metrics

def compute_anisotropic_force_balance(r_grid, z_grid, b_r, b_z, p_parallel, p_perpendicular, active_mask=None):
    """Return SI div(P) and current for a smooth, axisymmetric poloidal field.

    The regular-axis tensor limit is included. Compatibility error resolves
    only force above the reported floating-point stencil uncertainty; raw
    absolute and relative residuals are returned without alteration."""
    values = [np.asarray(value, dtype=float) for value in (r_grid, z_grid, b_r, b_z, p_parallel, p_perpendicular)]
    shape = values[0].shape
    if any((value.ndim != 2 or value.shape != shape or (not np.all(np.isfinite(value))) for value in values)):
        raise ValueError('R, Z, field, and pressure inputs must be finite same-shape [Z,R] arrays')
    r_grid, z_grid, b_r, b_z, p_parallel, p_perpendicular = values
    r, z = (r_grid[0, :], z_grid[:, 0])
    if r.size < 3 or z.size < 3 or (not np.allclose(r_grid, r[np.newaxis, :])) or (not np.allclose(z_grid, z[:, np.newaxis])):
        raise ValueError('a rectilinear R-Z grid with at least 3 points per axis is required')
    if r[0] < 0.0 or np.any(np.diff(r) <= 0.0) or np.any(np.diff(z) <= 0.0) or np.any(p_parallel < 0.0) or np.any(p_perpendicular < 0.0):
        raise ValueError('grid axes and pressures are invalid')
    mask = np.ones(shape, dtype=bool) if active_mask is None else np.asarray(active_mask, dtype=bool)
    if mask.shape != shape:
        raise ValueError('active_mask must match the R-Z grid')
    result = pressure_divergence(r_grid, z_grid, b_r, b_z, p_parallel, p_perpendicular)
    force_norm = np.hypot(result['force_R'], result['force_Z'])
    diagnostics = residual_metrics(result['parallel_force'], force_norm, result['parallel_force_roundoff'], mask)
    result.update({'parallel_force_error':diagnostics['error'],
                   'parallel_force_absolute':diagnostics['absolute'],
                   'parallel_force_error_raw':diagnostics['raw_relative'],
                   'parallel_force_roundoff_rms':diagnostics['roundoff'],
                   'parallel_force_roundoff_consistent':diagnostics['roundoff_consistent'],
                   'firehose_margin':1.0-MU0*(p_parallel-p_perpendicular)/np.maximum(result['B']**2,np.finfo(float).tiny)})
    return result
__all__ = ['compute_anisotropic_force_balance']
