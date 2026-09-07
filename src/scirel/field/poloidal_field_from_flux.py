"""Recover axisymmetric poloidal magnetic field from psi = R A_phi."""
import math
import struct
import numpy as np

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
        c = (2.0 * dx2 + dx1) / (dx2 * (dx2 + dx1))
        result[:, -1] = a * values[:, -3] + b * values[:, -2] + c * values[:, -1]
    return result

def poloidal_field_from_flux(r_grid, z_grid, psi):
    """Return ``B_R=-dpsi/dZ/R`` and ``B_Z=dpsi/dR/R`` with the source axis rule."""
    r_grid, z_grid, psi = (np.asarray(r_grid, dtype=float), np.asarray(z_grid, dtype=float), np.asarray(psi, dtype=float))
    if r_grid.shape != z_grid.shape or psi.shape != r_grid.shape or r_grid.ndim != 2:
        raise ValueError('R, Z, and psi must be equal-shape 2-D arrays')
    if not np.all(np.isfinite(r_grid)) or not np.all(np.isfinite(z_grid)):
        raise ValueError('R and Z coordinates must be finite')
    r, z = (r_grid[0, :], z_grid[:, 0])
    if r.size < 3 or z.size < 3 or (not np.allclose(r_grid, r[np.newaxis, :])) or (not np.allclose(z_grid, z[:, np.newaxis])):
        raise ValueError('a rectilinear R-Z grid with at least 3 points per axis is required')
    if np.any(np.diff(r) <= 0.0) or np.any(np.diff(z) <= 0.0) or r[0] < 0.0 or (not np.all(np.isfinite(psi))):
        raise ValueError('grid axes and psi are invalid')
    dpsi_dz, dpsi_dr = (_source_gradient(psi, z, axis=0), _source_gradient(psi, r, axis=1))
    b_r, b_z = (np.zeros_like(psi), np.zeros_like(psi))
    off_axis = r_grid > 0.0
    b_r[off_axis], b_z[off_axis] = (-dpsi_dz[off_axis] / r_grid[off_axis], dpsi_dr[off_axis] / r_grid[off_axis])
    if r[0] == 0.0:
        b_r[:, 0] = 0.0
        b_z[:, 0] = 2.0 * (psi[:, 1] - psi[:, 0]) / r[1] ** 2
    return {'B_R': b_r, 'B_Z': b_z, 'B': _source_hypot(b_r, b_z)}
__all__ = ['poloidal_field_from_flux']
