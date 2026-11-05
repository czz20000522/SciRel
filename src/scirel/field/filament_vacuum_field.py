"""Ideal circular-filament vacuum-field integration on a regular grid."""

from __future__ import annotations

import numpy as np

from scirel._result import Result
from scirel.electromagnetism.greens import compute_greens


def integrate_filament_vacuum_field(r_grid, z_grid, filaments):
    """Evaluate filament vacuum fields and radial flux as a named result.

    The magnetic components use the actual-coordinate Green kernel.  ``psi``
    is the caller-facing cumulative trapezoid of ``R*B_Z`` along the uniform
    radial axis, referenced to zero at its first radial node.

    Parameters
    ----------
    r_grid : real array-like, shape 2-D, at least two points per axis
        Target cylindrical-radius grid [m]. Finite, nonnegative, rectilinear,
        uniformly spaced and strictly increasing along exactly one array axis.
    z_grid : real array-like, shape same as r_grid
        Target axial-coordinate grid [m]. Finite and rectilinear along the
        other axis; axial order is not constrained.
    filaments : real array-like, shape [N_filament,3]
        Ideal circular-source rows ``[R0_m, Z0_m, current_A]`` in [m,m,A].
        Finite with strictly positive source radius; an empty source set is
        allowed.

    Returns
    -------
    psi : ndarray of float64, shape same as r_grid
        Field ``psi`` of the returned ``scirel._result.Result`` mapping:
        ``R A_phi`` from radial trapezoidal integration [Wb/rad], referenced
        to zero at the first radial grid point.
    b_r : ndarray of float64, shape same as r_grid
        Field ``b_r`` of the returned result mapping: superposed radial
        magnetic field [T].
    b_z : ndarray of float64, shape same as r_grid
        Field ``b_z`` of the returned result mapping: superposed axial magnetic
        field [T].

    Raises
    ------
    ValueError
        If grids or filaments are malformed, nonfinite, or have invalid axes
        or source/target singularities.
    FloatingPointError
        If Green evaluation or the radial integration produces a nonfinite
        result.

    See Also
    --------
    scirel.electromagnetism.compute_greens : Circular-filament Green kernel.
    scirel.field.circular_filament_green_response : Weighted Green response.

    Notes
    -----
    The three arrays are stored directly in one ``scirel._result.Result``
    mapping. No nested mapping is returned, and mapping access remains
    available alongside attribute access.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel._result import Result
    >>> from scirel.field import integrate_filament_vacuum_field
    >>> r_grid, z_grid = np.meshgrid(
    ...     np.linspace(0.0, 0.3, 5), np.linspace(-0.2, 0.2, 4)
    ... )
    >>> result = integrate_filament_vacuum_field(
    ...     r_grid, z_grid, [[0.45, -0.1, 1500.0]]
    ... )
    >>> assert isinstance(result, Result)
    >>> assert list(result) == ['psi', 'b_r', 'b_z']
    >>> assert result.psi is result['psi']
    >>> assert all(value.shape == r_grid.shape for value in result.values())
    >>> assert np.isfinite(result['b_z']).all()
    >>> np.testing.assert_array_equal(result['psi'][:, 0], 0.0)
    >>> np.testing.assert_array_equal(result['b_r'][:, 0], 0.0)
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
    return Result({"psi": psi, "b_r": b_r, "b_z": b_z})


__all__ = ["integrate_filament_vacuum_field"]
