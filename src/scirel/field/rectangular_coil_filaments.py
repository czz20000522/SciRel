"""Rectangular coil to axisymmetric filament locations from SciRel."""
from __future__ import annotations
import math
import numpy as np

def _positive_integer(name, value):
    if isinstance(value, bool) or int(value) != value or int(value) <= 0:
        raise ValueError(f'{name} must be a positive integer')
    return int(value)

def _positive_scalar(name, value):
    value = float(value)
    if not np.isfinite(value) or value <= 0.0:
        raise ValueError(f'{name} must be a positive finite scalar')
    return value

def discretize_rectangular_coil(r0, z0, nr, nz, dr, dz, angle_deg=0.0):
    """Return SciRel' ordered rectangular-coil filament locations [R,Z]."""
    r0, z0 = (float(r0), float(z0))
    if not np.isfinite(r0) or not np.isfinite(z0):
        raise ValueError('r0 and z0 must be finite')
    if r0 < 0.0:
        raise ValueError('r0 must be a nonnegative cylindrical radius')
    nr, nz = (_positive_integer('nr', nr), _positive_integer('nz', nz))
    dr, dz = (_positive_scalar('dr', dr), _positive_scalar('dz', dz))
    angle_deg = float(angle_deg)
    if not np.isfinite(angle_deg):
        raise ValueError('angle_deg must be finite')
    r_lower, r_upper = (r0 - dr * (nr - 1) / 2.0, r0 + dr * (nr - 1) / 2.0)
    z_lower, z_upper = (z0 - dz * (nz - 1) / 2.0, z0 + dz * (nz - 1) / 2.0)
    r_values = np.linspace(r_lower, r_upper, nr)
    z_values = np.linspace(z_lower, z_upper, nz)
    rz_pts = np.array([(r_value, z_value) for r_value in r_values for z_value in z_values])
    if np.isclose(angle_deg, 0.0):
        if np.any(rz_pts[:, 0] < 0.0):
            raise ValueError('coil geometry crosses the cylindrical axis')
        return rz_pts
    angle = math.pi * angle_deg / 180.0
    c, s = (np.cos(angle), np.sin(angle))
    rotation = np.array([[c, -s], [s, c]])
    rotated = (rz_pts - np.array([r0, z0])) @ rotation + np.array([r0, z0])
    if np.any(rotated[:, 0] < 0.0):
        raise ValueError('rotated coil geometry crosses the cylindrical axis')
    return rotated
__all__ = ['discretize_rectangular_coil']
