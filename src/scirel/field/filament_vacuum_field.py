"""Ideal circular-filament vacuum-field integration on a regular grid."""

from __future__ import annotations

import numpy as np

from scirel.electromagnetism.greens import compute_greens


def integrate_filament_vacuum_field(r_grid, z_grid, filaments):
    """Evaluate ``b_r``, ``b_z`` and the declared radial flux quadrature.

    The magnetic components use the actual-coordinate Green kernel.  ``psi``
    is the caller-facing cumulative trapezoid of ``R*B_Z`` along the uniform
    radial axis, referenced to zero at its first radial node.
    """
    if any(np.iscomplexobj(value) for value in (r_grid, z_grid, filaments)):
        raise ValueError("grid coordinates and filament currents must be real")
    radius_grid, height_grid = np.asarray(r_grid, dtype=float), np.asarray(z_grid, dtype=float)
    sources = np.asarray(filaments, dtype=float)
    if sources.size == 0:
        sources = np.empty((0, 3), dtype=float)
    if (
        radius_grid.ndim != 2
        or height_grid.shape != radius_grid.shape
        or min(radius_grid.shape) < 2
    ):
        raise ValueError(
            "r_grid and z_grid must be equal-shape 2-D grids with at least two points per axis"
        )
    if sources.ndim != 2 or sources.shape[1] != 3:
        raise ValueError("filaments must have shape (n_filaments, 3) = (R0_m, Z0_m, current_A)")
    if (
        not np.all(np.isfinite(radius_grid))
        or not np.all(np.isfinite(height_grid))
        or not np.all(np.isfinite(sources))
    ):
        raise ValueError("grid and filament values must be finite")
    if np.any(sources[:, 0] <= 0.0):
        raise ValueError("filament cylindrical radii must be strictly positive")

    varies_by_column = np.any(radius_grid != radius_grid[:, :1])
    varies_by_row = np.any(radius_grid != radius_grid[:1, :])
    if varies_by_column == varies_by_row:
        raise ValueError(
            "r_grid must be a rectilinear radial coordinate varying along exactly one axis"
        )
    radial_axis = 1 if varies_by_column else 0
    radial = radius_grid[0, :] if radial_axis == 1 else radius_grid[:, 0]
    expected = radial[None, :] if radial_axis == 1 else radial[:, None]
    if (
        np.any(radial < 0.0)
        or np.any(np.diff(radial) <= 0.0)
        or not np.array_equal(radius_grid, np.broadcast_to(expected, radius_grid.shape))
    ):
        raise ValueError(
            "r_grid must be a nonnegative, strictly increasing rectilinear radial coordinate"
        )
    if radial_axis == 1:
        if not np.allclose(height_grid, height_grid[:, :1]):
            raise ValueError("z_grid must be rectilinear when R varies along axis 1")
    elif not np.allclose(height_grid, height_grid[:1, :]):
        raise ValueError("z_grid must be rectilinear when R varies along axis 0")
    spacing = np.diff(radial)
    if not np.allclose(spacing, spacing[0], rtol=1.0e-12, atol=1.0e-14):
        raise ValueError("radial flux quadrature requires a uniformly spaced radial axis")

    points = np.column_stack((radius_grid.ravel(), height_grid.ravel()))
    _, radial_field, axial_field = compute_greens(sources, points)
    b_r = radial_field.reshape(radius_grid.shape)
    b_z = axial_field.reshape(radius_grid.shape)
    psi = np.zeros_like(radius_grid)
    step = float(spacing[0])
    integrand = (radial[:, None] if radial_axis == 0 else radial[None, :]) * b_z
    increments = (
        0.5
        * (
            np.take(integrand, indices=range(integrand.shape[radial_axis] - 1), axis=radial_axis)
            + np.take(integrand, indices=range(1, integrand.shape[radial_axis]), axis=radial_axis)
        )
        * step
    )
    if radial_axis == 1:
        psi[:, 1:] = np.cumsum(increments, axis=1)
    else:
        psi[1:, :] = np.cumsum(increments, axis=0)
    if not all(np.all(np.isfinite(value)) for value in (psi, b_r, b_z)):
        raise FloatingPointError("filament field evaluation produced a nonfinite result")
    return {"psi": psi, "b_r": b_r, "b_z": b_z}


__all__ = ["integrate_filament_vacuum_field"]
