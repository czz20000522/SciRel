"""Discretization of a signed permanent-ring approximation."""

import numpy as np


def discretize_permanent_ring(r0, z0, width, height, mu_hat_deg=0.0):
    """Return two eight-point radial faces and their default signed weights."""
    center = np.asarray((r0, z0), dtype=float)
    dimensions = np.asarray((width, height, mu_hat_deg), dtype=float)
    if not np.all(np.isfinite(center)) or not np.all(np.isfinite(dimensions)):
        raise ValueError("ring geometry must be finite")
    if center[0] < 0.0 or dimensions[0] <= 0.0 or dimensions[1] <= 0.0:
        raise ValueError("ring geometry must have nonnegative radius and positive dimensions")
    with np.errstate(over="ignore", invalid="ignore"):
        radial = center[0] + np.array([-0.5, 0.5]) * dimensions[0]
        axial = np.linspace(center[1] - 0.5 * dimensions[1], center[1] + 0.5 * dimensions[1], 8)
        points = np.vstack(
            (
                np.column_stack((np.full(8, radial[0]), axial)),
                np.column_stack((np.full(8, radial[1]), axial)),
            )
        )
        if dimensions[2] != 0.0:
            theta = np.deg2rad(dimensions[2])
            rotation = np.array([[np.cos(theta), -np.sin(theta)], [np.sin(theta), np.cos(theta)]])
            points = (points - center) @ rotation + center
    if not np.all(np.isfinite(points)) or np.any(points[:, 0] < 0.0):
        raise ValueError("ring geometry crosses the cylindrical axis or contains nonfinite points")
    return {"rz_pts": points, "default_weights": np.r_[-np.ones(8), np.ones(8)]}


__all__ = ["discretize_permanent_ring"]
