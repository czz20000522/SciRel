"""Recover poloidal magnetic components from ``psi = R A_phi``."""

from __future__ import annotations

import numpy as np

from scirel._numerics import stable_gradient as _source_gradient
from scirel._result import Result


def _source_hypot(left, right):
    """Evaluate a finite-range-safe Euclidean norm elementwise."""
    left, right = np.broadcast_arrays(np.asarray(left, dtype=float), np.asarray(right, dtype=float))
    return np.hypot(left, right)


def poloidal_field_from_flux(r_grid, z_grid, psi):
    """Return axisymmetric poloidal field components as a named result.

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
        two-dimensional shape as the coordinate grids. Physical field recovery
        requires a consistent flux reference across Z; this is caller-owned
        and is not inferred from the array.

    Returns
    -------
    B_R : ndarray of float64, shape [N_Z,N_R]
        Field of the returned ``scirel._result.Result`` mapping containing
        ``-dpsi/dZ/R`` in [T]. Zero at an included cylindrical-axis column.
    B_Z : ndarray of float64, shape [N_Z,N_R]
        Field containing ``dpsi/dR/R`` in [T]. Uses the discrete axis rule if
        R=0 is included.
    B : ndarray of float64, shape [N_Z,N_R]
        Field containing the poloidal-field magnitude ``hypot(B_R,B_Z)`` in
        [T]. No fixed lower floor is applied.

    Raises
    ------
    ValueError
        ValueError is raised for complex/nonfinite/mismatched arrays,
        nonrectilinear grids, too few nodes, or invalid axes.
    FloatingPointError
        If an accepted finite input produces an unrepresentable field
        component or magnitude. No partial result is returned.

    See Also
    --------
    scirel.io.read_geqdsk : Reads psi(R, Z) per radian from a G-EQDSK file.
    scirel.field.solve_multi_coil_vacuum_field : Vacuum psi and field from coils.

    Notes
    -----
    The three arrays are returned together as one ``scirel._result.Result``
    mapping. Mapping access remains available and each field can also be read
    as an attribute. Away from the axis the components follow
    ``B_R=-dpsi/dZ/R`` and ``B_Z=dpsi/dR/R`` on the supplied rectilinear grid.

    Adding a constant reference leaves these derivatives unchanged. Subtracting
    a different reference function at each Z generally changes ``B_R``.
    In particular, ``integrate_filament_vacuum_field`` returns a radial
    relative integral starting at R0: unless its reference term is constant,
    restore ``psi_global(R0,Z)`` from the same source model before using it
    here, and account for its radial quadrature error. A regular included
    axis removes that reference term. This function does not perform a
    flux-reference or ``2*pi`` conversion.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel._result import Result
    >>> from scirel.field import poloidal_field_from_flux
    >>> r_grid, z_grid = np.meshgrid([0.0, 0.2, 0.4], [-0.5, 0.0, 0.5])
    >>> result = poloidal_field_from_flux(r_grid, z_grid, r_grid**2)
    >>> assert isinstance(result, Result)
    >>> assert result.B_R is result['B_R']
    >>> np.testing.assert_allclose(result['B_R'], 0.0)
    >>> np.testing.assert_allclose(result['B_Z'], 2.0)
    >>> np.testing.assert_allclose(result['B'], 2.0)
    """
    values = tuple(np.asarray(value) for value in (r_grid, z_grid, psi))
    if any(
        np.iscomplexobj(value)
        or (value.dtype.kind == "O" and any(np.iscomplexobj(item) for item in value.flat))
        for value in values
    ):
        raise ValueError("R, Z, and psi must be real-valued arrays")
    try:
        r_grid, z_grid, psi = (np.asarray(value, dtype=float) for value in values)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError("R, Z, and psi must be real-valued arrays") from error
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
    magnitude = _source_hypot(b_r, b_z)
    if not all(np.isfinite(value).all() for value in (b_r, b_z, magnitude)):
        raise FloatingPointError("poloidal field is not representable")
    return Result({"B_R": b_r, "B_Z": b_z, "B": magnitude})


__all__ = ["poloidal_field_from_flux"]
