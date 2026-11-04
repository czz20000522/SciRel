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

def _source_gradient(values, coordinates, axis):
    """Preserve the source ``np.gradient(..., coordinates, edge_order=2)`` stencil."""
    distances = np.diff(coordinates)
    result = np.empty_like(values)
    uniform = (distances == distances[0]).all()
    if axis == 0:
        if uniform:
            spacing = distances[0]
            result[1:-1, :] = (values[2:, :] - values[:-2, :]) / (2.0 * spacing)
            result[0, :] = -1.5 / spacing * values[0, :] + 2.0 / spacing * values[1, :] - 0.5 / spacing * values[2, :]
            result[-1, :] = 0.5 / spacing * values[-3, :] - 2.0 / spacing * values[-2, :] + 1.5 / spacing * values[-1, :]
        else:
            dx1, dx2 = (distances[:-1], distances[1:])
            a = -dx2 / (dx1 * (dx1 + dx2))
            b = (dx2 - dx1) / (dx1 * dx2)
            c = dx1 / (dx2 * (dx1 + dx2))
            result[1:-1, :] = a[:, None] * values[:-2, :] + b[:, None] * values[1:-1, :] + c[:, None] * values[2:, :]
            dx1, dx2 = (distances[0], distances[1])
            a = -(2.0 * dx1 + dx2) / (dx1 * (dx1 + dx2))
            b = (dx1 + dx2) / (dx1 * dx2)
            c = -dx1 / (dx2 * (dx1 + dx2))
            result[0, :] = a * values[0, :] + b * values[1, :] + c * values[2, :]
            dx1, dx2 = (distances[-2], distances[-1])
            a = dx2 / (dx1 * (dx1 + dx2))
            b = -(dx2 + dx1) / (dx1 * dx2)
            c = (2.0 * dx2 + dx1) / (dx2 * (dx1 + dx2))
            result[-1, :] = a * values[-3, :] + b * values[-2, :] + c * values[-1, :]
    elif uniform:
        spacing = distances[0]
        result[:, 1:-1] = (values[:, 2:] - values[:, :-2]) / (2.0 * spacing)
        result[:, 0] = -1.5 / spacing * values[:, 0] + 2.0 / spacing * values[:, 1] - 0.5 / spacing * values[:, 2]
        result[:, -1] = 0.5 / spacing * values[:, -3] - 2.0 / spacing * values[:, -2] + 1.5 / spacing * values[:, -1]
    else:
        dx1, dx2 = (distances[:-1], distances[1:])
        a = -dx2 / (dx1 * (dx1 + dx2))
        b = (dx2 - dx1) / (dx1 * dx2)
        c = dx1 / (dx2 * (dx1 + dx2))
        result[:, 1:-1] = a * values[:, :-2] + b * values[:, 1:-1] + c * values[:, 2:]
        dx1, dx2 = (distances[0], distances[1])
        a = -(2.0 * dx1 + dx2) / (dx1 * (dx1 + dx2))
        b = (dx1 + dx2) / (dx1 * dx2)
        c = -dx1 / (dx2 * (dx1 + dx2))
        result[:, 0] = a * values[:, 0] + b * values[:, 1] + c * values[:, 2]
        dx1, dx2 = (distances[-2], distances[-1])
        a = dx2 / (dx1 * (dx1 + dx2))
        b = -(dx2 + dx1) / (dx1 * dx2)
        c = (2.0 * dx2 + dx1) / (dx2 * (dx1 + dx2))
        result[:, -1] = a * values[:, -3] + b * values[:, -2] + c * values[:, -1]
    return result

def compute_anisotropic_force_balance(r_grid, z_grid, b_r, b_z, p_parallel, p_perpendicular, active_mask=None):
    """Return the source-defined ``div(P)`` force, toroidal current, and diagnostics."""
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
    magnitude = _source_hypot(b_r, b_z)
    inverse_b = np.divide(1.0, magnitude, out=np.zeros_like(magnitude), where=magnitude > np.finfo(float).tiny)
    unit_r, unit_z = (b_r * inverse_b, b_z * inverse_b)
    delta = p_parallel - p_perpendicular
    p_rr = p_perpendicular + delta * unit_r ** 2
    p_zz = p_perpendicular + delta * unit_z ** 2
    p_rz = delta * unit_r * unit_z
    force_r = _source_gradient(p_rr, r, axis=1) + _source_gradient(p_rz, z, axis=0)
    force_z = _source_gradient(p_rz, r, axis=1) + _source_gradient(p_zz, z, axis=0)
    off_axis = r_grid > 0.0
    force_r[off_axis] += (p_rr[off_axis] - p_perpendicular[off_axis]) / r_grid[off_axis]
    force_z[off_axis] += p_rz[off_axis] / r_grid[off_axis]
    if r[0] == 0.0:
        force_r[:, 0] = 0.0
    b_squared = magnitude ** 2
    j_phi = np.divide(b_z * force_r - b_r * force_z, b_squared, out=np.zeros_like(magnitude), where=b_squared > np.finfo(float).tiny)
    parallel_force = (b_r * force_r + b_z * force_z) * inverse_b
    if r[0] == 0.0:
        j_phi[:, 0] = 0.0
    force_norm = _source_hypot(force_r, force_z)
    if np.any(mask):
        parallel_force_error = float(np.sqrt(np.mean(parallel_force[mask] ** 2)) / max(float(np.sqrt(np.mean(force_norm[mask] ** 2))), np.finfo(float).tiny))
    else:
        parallel_force_error = 0.0
    firehose_margin = 1.0 - MU0 * (p_parallel - p_perpendicular) / np.maximum(b_squared, np.finfo(float).tiny)
    return {'force_R': force_r, 'force_Z': force_z, 'parallel_force': parallel_force, 'J_phi': j_phi, 'B': magnitude, 'parallel_force_error': parallel_force_error, 'firehose_margin': firehose_margin}
__all__ = ['compute_anisotropic_force_balance']
