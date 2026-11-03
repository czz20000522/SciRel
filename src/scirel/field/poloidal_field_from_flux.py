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

    Parameters
    ----------
    r_grid : real array-like, converted to float64, shape [N_Z,N_R]
        Cylindrical radius at each grid point [m]. Finite rectilinear grid with
        nonnegative, strictly increasing R axis and N_R >= 3; same shape as
        z_grid and psi.
    z_grid : real array-like, converted to float64, shape [N_Z,N_R]
        Axial coordinate at each grid point [m]. Finite rectilinear grid with
        strictly increasing Z axis and N_Z >= 3; same shape as r_grid and psi.
    psi : real array-like, converted to float64, shape [N_Z,N_R]
        Axisymmetric poloidal flux function R A_phi sampled on the R-Z grid, not
        full linked flux [Wb/rad]. Finite values and exactly the same
        two-dimensional shape as the coordinate grids.

    Returns
    -------
    B_R : float64, shape [N_Z,N_R]
        Radial poloidal magnetic-field component [T]. Zero at an included
        cylindrical-axis column.
    B_Z : float64, shape [N_Z,N_R]
        Axial poloidal magnetic-field component [T]. Uses the discrete axis rule
        if R=0 is included.
    B : float64, shape [N_Z,N_R]
        Poloidal-field magnitude hypot(B_R,B_Z) [T]. No fixed lower floor is
        applied.

    Raises
    ------
    ValueError
        ValueError is raised for complex/nonfinite/mismatched arrays,
        nonrectilinear grids, too few nodes, or invalid axes.

    See Also
    --------
    scirel.io.read_geqdsk : Reads psi(R, Z) per radian from a G-EQDSK file.
    scirel.field.solve_multi_coil_vacuum_field : Vacuum psi and field from coils.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.field import poloidal_field_from_flux
    >>> r_grid, z_grid = np.meshgrid([0.0, 0.2, 0.4], [-0.5, 0.0, 0.5])
    >>> result = poloidal_field_from_flux(r_grid, z_grid, r_grid**2)
    >>> np.testing.assert_allclose(result['B_R'], 0.0)
    >>> np.testing.assert_allclose(result['B_Z'], 2.0)
    >>> np.testing.assert_allclose(result['B'], 2.0)
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
