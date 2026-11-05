"""Observation geometry for the scalar axisymmetric filament Green form."""

from __future__ import annotations

import numpy as np

SOURCE_AXIS_OFFSET_M = 1.0e-8


def compute_axisymmetric_coil_modulus(
    observation_radius_m, observation_z_m, coil_radius_m, coil_z_m
):
    """Return the offset observation radius, ``m`` and the Green distance."""
    raw_radius = float(observation_radius_m)
    radius = raw_radius + SOURCE_AXIS_OFFSET_M
    coil_radius = np.asarray(coil_radius_m, dtype=float)
    coil_z = np.asarray(coil_z_m, dtype=float)
    if radius <= 0.0 or not np.isfinite(radius) or not np.isfinite(observation_z_m):
        raise ValueError("observation coordinates must be finite after source axis offset")
    if raw_radius < 0.0:
        raise ValueError("observation_radius_m must be nonnegative")
    if (
        coil_radius.ndim != 1
        or coil_z.shape != coil_radius.shape
        or np.any(coil_radius <= 0.0)
        or not np.all(np.isfinite(coil_radius))
        or not np.all(np.isfinite(coil_z))
    ):
        raise ValueError(
            "coil radii/z coordinates must be finite same-shape vectors with positive radii"
        )
    with np.errstate(over="ignore", invalid="ignore"):
        denominator = (radius + coil_radius) ** 2 + (observation_z_m - coil_z) ** 2
        modulus_squared = 4.0 * radius * coil_radius / denominator
        distance = np.sqrt(denominator)
    if not np.all(np.isfinite(modulus_squared)) or not np.all(np.isfinite(distance)):
        raise ValueError("coil geometry overflowed to non-finite modulus/distance")
    if np.any(modulus_squared <= 0.0):
        raise ValueError("coil modulus underflowed to zero")
    return radius, modulus_squared, distance


__all__ = ["compute_axisymmetric_coil_modulus"]
