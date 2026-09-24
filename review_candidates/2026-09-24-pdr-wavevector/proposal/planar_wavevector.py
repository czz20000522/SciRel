"""Proposed SciRel callable; isolated from the maintained runtime package."""

from __future__ import annotations

import numpy as np


def project_planar_wavevector(
    *, k_grid=None, theta_rad=None, kx_grid=None, kz_grid=None
):
    """Project a real x-z wavevector in consistent inverse-length units."""

    if k_grid is not None:
        if kx_grid is not None or kz_grid is not None:
            raise ValueError("choose a magnitude sweep or paired components")
        k = np.asarray(k_grid, dtype=float)
        if k.ndim != 1 or k.size == 0 or not np.isfinite(k).all() or np.any(k < 0):
            raise ValueError("k_grid must be a nonempty finite nonnegative vector")
        theta = 0.0 if theta_rad is None else float(theta_rad)
        if not np.isfinite(theta):
            raise ValueError("theta_rad must be finite")
        return {
            "kx": k * np.sin(theta),
            "kz": k * np.cos(theta),
            "k": k.copy(),
            "theta_rad": theta,
            "projection_mode": "polar",
        }

    if kx_grid is None or kz_grid is None:
        raise ValueError("both component grids are required")
    kx = np.asarray(kx_grid, dtype=float)
    kz = np.asarray(kz_grid, dtype=float)
    if (
        kx.ndim != 1
        or kz.ndim != 1
        or kx.size == 0
        or kx.shape != kz.shape
        or not np.isfinite(kx).all()
        or not np.isfinite(kz).all()
    ):
        raise ValueError("component grids must be finite paired nonempty vectors")
    magnitude = np.hypot(kx, kz)
    if not np.isfinite(magnitude).all():
        raise ValueError("wavevector magnitude exceeds the finite numeric domain")
    return {
        "kx": kx.copy(),
        "kz": kz.copy(),
        "k": magnitude,
        "theta_rad": None,
        "projection_mode": "cartesian",
    }
