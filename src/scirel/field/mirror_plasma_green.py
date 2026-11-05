"""Flux Green matrix for a symmetric rectilinear plasma grid."""

from __future__ import annotations

import numpy as np

from scirel.electromagnetism.greens import get_gpsi


def build_mirror_plasma_flux_green(r_grid, z_grid):
    """Build ``g_psi[target, source]`` after validating mirror-grid geometry."""
    if np.iscomplexobj(r_grid) or np.iscomplexobj(z_grid):
        raise ValueError("grid coordinates must be real")
    radius, height = np.asarray(r_grid, dtype=float), np.asarray(z_grid, dtype=float)
    if radius.ndim != 2 or height.shape != radius.shape or min(radius.shape) < 2:
        raise ValueError(
            "r_grid and z_grid must be equal-shape 2-D grids with at least two points per axis"
        )
    if not np.all(np.isfinite(radius)) or not np.all(np.isfinite(height)):
        raise ValueError("r_grid and z_grid must be finite")
    radial, axial = radius[0], height[:, 0]
    if (
        not np.allclose(radius, radial[None, :])
        or not np.allclose(height, axial[:, None])
        or np.any(radial < 0.0)
        or np.any(np.diff(radial) <= 0.0)
        or np.any(np.diff(axial) <= 0.0)
    ):
        raise ValueError(
            "the source-compatible matrix requires a strictly increasing rectilinear R-Z grid"
        )
    if not np.allclose(axial, -axial[::-1], rtol=0.0, atol=1.0e-12):
        raise ValueError("the reflection construction requires an axis-reflection-symmetric Z grid")
    if not np.allclose(np.diff(axial), np.diff(axial)[0], rtol=1.0e-12, atol=1.0e-14):
        raise ValueError("the reflection construction requires a uniformly spaced Z grid")
    return {"g_psi": get_gpsi(radius, height)}


__all__ = ["build_mirror_plasma_flux_green"]
