"""Bilinear sampling of a scalar field on a rectilinear R-Z grid."""

from __future__ import annotations

from fractions import Fraction

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
    if np.any(r_axis[1:] <= r_axis[:-1]) or np.any(z_axis[1:] <= z_axis[:-1]):
        raise ValueError("R and Z axes must be strictly increasing")
    return r_grid, z_grid, r_axis, z_axis


def _cell_indices(axis, values):
    """Return the lower cell index per value, clamped onto the closed axis box.

    ``searchsorted(..., side="right") - 1`` selects the interval containing each
    value; values at or beyond the last node would report the last index, so the
    result is clamped to ``axis.size - 2`` and ``index + 1`` stays inside the axis.
    The clamp chooses a stencil, not a value.
    """
    return np.clip(np.searchsorted(axis, values, side="right") - 1, 0, axis.size - 2)


def _exact_sample(r0, r1, z0, z1, r, z, corners):
    """Round the original finite-input bilinear polynomial only at its result."""
    r0, r1, z0, z1, r, z = (Fraction.from_float(float(value)) for value in (r0, r1, z0, z1, r, z))
    q00, q10, q01, q11 = (Fraction.from_float(float(value)) for value in corners)
    lower = ((r1 - r) * q00 + (r - r0) * q10) / (r1 - r0)
    upper = ((r1 - r) * q01 + (r - r0) * q11) / (r1 - r0)
    return float(((z1 - z) * lower + (z - z0) * upper) / (z1 - z0))


def _samples(r0, r1, z0, z1, r, z, corners):
    """Use vector weights normally and exact input ratios at arithmetic hazards."""
    # Each complementary weight is formed from its own endpoint difference.
    # Computing it as 1-t would lose a small, representable near-node contribution.
    # Finite-input hazards are reevaluated below, not accepted as inf/NaN/zero.
    with np.errstate(over="ignore", invalid="ignore", under="ignore", divide="ignore"):
        dr, dz = r1 - r0, z1 - z0
        fractions = np.asarray([(r1 - r) / dr, (r - r0) / dr, (z1 - z) / dz, (z - z0) / dz])
        left, right, lower, upper = fractions
        weights = np.asarray([left * lower, right * lower, left * upper, right * upper])
        terms = weights * corners
        samples = np.sum(terms, axis=0)
        magnitude = np.sum(np.abs(terms), axis=0)
        small = np.finfo(float).tiny
        # A nonzero exact weight can underflow before a large corner value rescues
        # it. Include zero and subnormal intermediate fractions/products.
        nonzero_fractions = np.asarray([r1 != r, r != r0, z1 != z, z != z0])
        nonzero_weights = np.asarray(
            [
                (r1 != r) & (z1 != z),
                (r != r0) & (z1 != z),
                (r1 != r) & (z != z0),
                (r != r0) & (z != z0),
            ]
        )
        hazard = (
            ~np.isfinite(dr)
            | ~np.isfinite(dz)
            | ~np.isfinite(samples)
            | ~np.isfinite(magnitude)
            | np.any(nonzero_fractions & (np.abs(fractions) < small), axis=0)
            | np.any(nonzero_weights & (np.abs(weights) < small), axis=0)
            | np.any(nonzero_weights & (corners != 0.0) & (np.abs(terms) < small), axis=0)
            | (np.abs(samples) < magnitude / 8.0)
        )
    for index in np.flatnonzero(hazard):
        samples[index] = _exact_sample(
            r0[index],
            r1[index],
            z0[index],
            z1[index],
            r[index],
            z[index],
            corners[:, index],
        )
    return samples


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
    scirel.geometry.map_axisymmetric_equilibrium_to_cartesian_grid : Axisymmetric equilibrium map to Cartesian solver grid.
    scirel.numerics.interpolate.interpolate_complex_rectilinear_field : Complex rectilinear field interpolation.

    Notes
    -----
    Within each enclosing cell, blend its four [Z,R]-indexed corner values with the bilinear
    weights from the point's R and Z fractions. Return one value per point in input order.
    Complementary weights use independent endpoint differences. Overflowing spans,
    vanishing intermediate contributions and strong cancellation are reevaluated
    from exact ratios of the original float64 inputs before final rounding.

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
    >>> from scirel.numerics.interpolate import sample_rectilinear_field
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
    samples = _samples(
        r_axis[ri],
        r_axis[ri + 1],
        z_axis[zi],
        z_axis[zi + 1],
        r_values,
        z_values,
        np.asarray(
            [
                quantity[zi, ri],
                quantity[zi, ri + 1],
                quantity[zi + 1, ri],
                quantity[zi + 1, ri + 1],
            ]
        ),
    )
    return {"samples": samples}
