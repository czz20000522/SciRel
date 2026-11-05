"""Bilinear sampling of a scalar field on a rectilinear R-Z grid."""

from __future__ import annotations

import numpy as np

__all__ = ["sample_rectilinear_field"]


def _axes(r_grid, z_grid):
    """Validate the mesh and return its two one-dimensional axes."""
    r_grid = np.asarray(r_grid, dtype=float)
    z_grid = np.asarray(z_grid, dtype=float)
    if r_grid.ndim != 2 or z_grid.ndim != 2 or r_grid.shape != z_grid.shape:
        raise ValueError("R and Z must be same-shape 2-D arrays")
    if min(r_grid.shape) < 2:
        raise ValueError("R-Z grid must contain at least 2 rows and 2 columns")
    if not np.isfinite(r_grid).all() or not np.isfinite(z_grid).all():
        raise ValueError("R and Z must contain only finite values")
    if not np.allclose(r_grid, r_grid[0:1, :], rtol=1e-12, atol=1e-14):
        raise ValueError("R must be constant along each grid column")
    if not np.allclose(z_grid, z_grid[:, 0:1], rtol=1e-12, atol=1e-14):
        raise ValueError("Z must be constant along each grid row")
    r_axis = r_grid[0]
    z_axis = z_grid[:, 0]
    if np.any(np.diff(r_axis) <= 0.0) or np.any(np.diff(z_axis) <= 0.0):
        raise ValueError("R and Z axes must be strictly increasing")
    return r_grid, z_grid, r_axis, z_axis


def _cell_indices(axis, values):
    return np.clip(np.searchsorted(axis, values, side="right") - 1, 0, axis.size - 2)


def sample_rectilinear_field(r_grid, z_grid, quantity, points):
    """Rectilinear R-Z bilinear sampling

    Parameters
    ----------
    r_grid : real array-like, converted to float64
        Radius coordinate mesh with a common R axis along each row. [m] Shape:
        ``[N_Z,N_R]``. Finite, rectilinear, strictly increasing radial axis and N_R >= 2;
        same shape as z_grid and quantity.

    z_grid : real array-like, converted to float64
        Axial coordinate mesh with a common Z axis along each column. [m] Shape:
        ``[N_Z,N_R]``. Finite, rectilinear, strictly increasing axial axis and N_Z >= 2;
        same shape as r_grid and quantity.

    quantity : real array-like, converted to float64
        Real scalar field sampled at each grid node. [same as sampled field] Shape:
        ``[N_Z,N_R]``. Finite and exactly the same shape as the coordinate grids.

    points : real array-like, converted to float64
        Ordered query coordinates [R,Z]. [m,m] Shape: ``[N_point,2]``. Finite; each point
        must lie within the closed R-Z grid box. An empty [0,2] array is accepted.

    Returns
    -------
    samples : float64
        Bilinearly interpolated scalar values in query order. [same as quantity] Shape:
        ``[N_point]``. One-dimensional array; empty for zero query points.

    Raises
    ------
    ValueError
        Raises ValueError for invalid grid rank/shape, nonfinite inputs, insufficient or nonmonotonic axes, nonrectilinear coordinates, invalid point shape, or any point outside the grid.

    See Also
    --------
    map_axisymmetric_equilibrium_to_cartesian_grid : Axisymmetric equilibrium map to Cartesian solver grid.
    interpolate_complex_rectilinear_field : Complex rectilinear field interpolation.

    Notes
    -----
    Within each enclosing cell, blend its four [Z,R]-indexed corner values with the bilinear
    weights from the point's R and Z fractions. Return one value per point in input order.

    **Coordinates.** grid arrays indexed [Z,R]; each query point ordered [R,Z]

    **Boundary.** Points on the closed grid boundary are accepted; points outside are
    rejected rather than clamped or extrapolated.

    **Preconditions.**

    * The real field and query coordinates use the declared [Z,R] grid and [R,Z] point
      conventions.
    * The caller has already selected a meaningful quantity and consistent length units.

    **Limits.**

    * Extrapolation or out-of-domain clamping.
    * Complex or vector-valued interpolation.
    * Interpolation on curvilinear, unstructured, or three-dimensional grids.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.geometry import sample_rectilinear_field
    >>> r_grid, z_grid = np.meshgrid([1.0, 2.0, 4.0], [-1.0, 1.0])
    >>> quantity = 3.0*r_grid - 2.0*z_grid + 1.0
    >>> result = sample_rectilinear_field(r_grid, z_grid, quantity, [[1.5, 0.0], [4.0, 1.0]])
    >>> np.testing.assert_allclose(result['samples'], [5.5, 11.0])
    """
    _, _, r_axis, z_axis = _axes(r_grid, z_grid)
    quantity = np.asarray(quantity, dtype=float)
    points = np.asarray(points, dtype=float)
    if quantity.shape != np.asarray(r_grid).shape or not np.isfinite(quantity).all():
        raise ValueError("quantity must be finite and have the same shape as R and Z")
    if points.ndim != 2 or points.shape[1] != 2 or not np.isfinite(points).all():
        raise ValueError("points must be a finite array with shape (n_points, 2)")
    r_values, z_values = points.T
    inside = (
        (r_values >= r_axis[0])
        & (r_values <= r_axis[-1])
        & (z_values >= z_axis[0])
        & (z_values <= z_axis[-1])
    )
    if not np.all(inside):
        raise ValueError("diagnostic point lies outside the R-Z grid")

    ri = _cell_indices(r_axis, r_values)
    zi = _cell_indices(z_axis, z_values)
    rf = (r_values - r_axis[ri]) / (r_axis[ri + 1] - r_axis[ri])
    zf = (z_values - z_axis[zi]) / (z_axis[zi + 1] - z_axis[zi])
    q00 = quantity[zi, ri]
    q10 = quantity[zi, ri + 1]
    q01 = quantity[zi + 1, ri]
    q11 = quantity[zi + 1, ri + 1]
    samples = (
        (1.0 - rf) * (1.0 - zf) * q00
        + rf * (1.0 - zf) * q10
        + (1.0 - rf) * zf * q01
        + rf * zf * q11
    )
    return {"samples": samples}
