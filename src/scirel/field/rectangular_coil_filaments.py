"""Vectorized rectangular coil filament geometry."""

from __future__ import annotations

import numpy as np


def _positive_integer(name, value):
    if isinstance(value, (bool, np.bool_)) or int(value) != value or int(value) <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return int(value)


def _positive_scalar(name, value):
    value = float(value)
    if not np.isfinite(value) or value <= 0.0:
        raise ValueError(f"{name} must be a positive finite scalar")
    return value


def discretize_rectangular_coil(r0, z0, nr, nz, dr, dz, angle_deg=0.0):
    """Return ordered ``(R, Z)`` centers for a rectangular filament array.

    The radial index is outermost and the axial index is innermost.  Rotation
    is applied to row vectors around the declared centroid, so a positive
    angle follows the package's cylindrical drawing convention.
    """
    r0, z0 = float(r0), float(z0)
    if not np.isfinite(r0) or not np.isfinite(z0):
        raise ValueError("r0 and z0 must be finite")
    if r0 < 0.0:
        raise ValueError("r0 must be a nonnegative cylindrical radius")
    nr, nz = _positive_integer("nr", nr), _positive_integer("nz", nz)
    dr, dz = _positive_scalar("dr", dr), _positive_scalar("dz", dz)
    angle_deg = float(angle_deg)
    if not np.isfinite(angle_deg):
        raise ValueError("angle_deg must be finite")

    radial = np.linspace(r0 - 0.5 * dr * (nr - 1), r0 + 0.5 * dr * (nr - 1), nr)
    axial = np.linspace(z0 - 0.5 * dz * (nz - 1), z0 + 0.5 * dz * (nz - 1), nz)
    points = np.column_stack((np.repeat(radial, nz), np.tile(axial, nr)))
    if angle_deg != 0.0:
        theta = np.deg2rad(angle_deg)
        cosine, sine = np.cos(theta), np.sin(theta)
        rotation = np.array([[cosine, -sine], [sine, cosine]])
        points = (points - np.array([r0, z0])) @ rotation + np.array([r0, z0])
    if np.any(points[:, 0] < 0.0):
        raise ValueError("coil geometry crosses the cylindrical axis")
    return points


__all__ = ["discretize_rectangular_coil"]
