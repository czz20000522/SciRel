"""Recover poloidal magnetic components from ``psi = R A_phi``."""

from __future__ import annotations

import numpy as np

from scirel._numerics import stable_gradient as _source_gradient


def _source_hypot(left, right):
    """Evaluate a finite-range-safe Euclidean norm elementwise."""
    left, right = np.broadcast_arrays(np.asarray(left, dtype=float), np.asarray(right, dtype=float))
    return np.hypot(left, right)


def poloidal_field_from_flux(r_grid, z_grid, psi):
    """Return ``B_R=-dpsi/dZ/R``, ``B_Z=dpsi/dR/R`` and ``B``.

    A rectilinear grid is differentiated with the package's stable local
    stencil.  At the cylindrical axis the even-flux limit is used for
    ``B_Z`` and ``B_R`` is set to zero.
    """
    r_grid, z_grid, psi = (
        np.asarray(r_grid, dtype=float),
        np.asarray(z_grid, dtype=float),
        np.asarray(psi, dtype=float),
    )
    if r_grid.ndim != 2 or r_grid.shape != z_grid.shape or psi.shape != r_grid.shape:
        raise ValueError("R, Z, and psi must be equal-shape 2-D arrays")
    if not np.all(np.isfinite(r_grid)) or not np.all(np.isfinite(z_grid)):
        raise ValueError("R and Z coordinates must be finite")
    radial, axial = r_grid[0, :], z_grid[:, 0]
    if (
        radial.size < 3
        or axial.size < 3
        or not np.allclose(r_grid, radial[None, :])
        or not np.allclose(z_grid, axial[:, None])
    ):
        raise ValueError("a rectilinear R-Z grid with at least 3 points per axis is required")
    if (
        np.any(np.diff(radial) <= 0.0)
        or np.any(np.diff(axial) <= 0.0)
        or radial[0] < 0.0
        or not np.all(np.isfinite(psi))
    ):
        raise ValueError("grid axes and psi are invalid")

    dpsi_dz = _source_gradient(psi, axial, axis=0)
    dpsi_dr = _source_gradient(psi, radial, axis=1)
    b_r = np.zeros_like(psi)
    b_z = np.zeros_like(psi)
    off_axis = r_grid > 0.0
    b_r[off_axis] = -dpsi_dz[off_axis] / r_grid[off_axis]
    b_z[off_axis] = dpsi_dr[off_axis] / r_grid[off_axis]
    if radial[0] == 0.0:
        b_r[:, 0] = 0.0
        b_z[:, 0] = 2.0 * (psi[:, 1] - psi[:, 0]) / radial[1] ** 2
    return {"B_R": b_r, "B_Z": b_z, "B": _source_hypot(b_r, b_z)}


__all__ = ["poloidal_field_from_flux"]
