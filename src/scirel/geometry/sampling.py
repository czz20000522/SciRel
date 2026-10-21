"""Grid sampling and line-integral utilities used by geometry diagnostics."""
from __future__ import annotations

import numpy as np

from .numerics import diff_12_central

__all__ = [
    "transform_to_rtheta", "transform_to_rhoz", "regular_grid", "poly_fit",
    "reflect_and_hstack", "locs_to_vals", "locs_to_vals_griddata", "locs_to_vals1D",
    "get_fieldlines", "parse_segment", "get_fieldline_distance", "interp",
    "flux_surface_avg", "diff_central",
]


def regular_grid(xx, yy, *args, **kwargs):
    """Interpolate scattered fields onto a supplied or generated ``ij`` grid.

    Parameters
    ----------
    xx, yy : array_like
        Matched sample coordinates.
    *args : array_like
        Fields sampled at those coordinates.
    values, nx, ny, xi, yi, method : optional
        Keyword forms for fields, generated dimensions, query grids, and the
        SciPy interpolation method.

    Returns
    -------
    tuple
        ``(xi, yi)`` followed by one result per input field.

    Raises
    ------
    TypeError, ValueError
        Unknown keywords or conflicting positional and named fields.
    """
    values = kwargs.pop("values", None)
    if values is not None:
        if args:
            raise ValueError("supply fields either positionally or through values")
        args = tuple(values)
    nx = kwargs.pop("nx", 200)
    ny = kwargs.pop("ny", 200)
    xi = kwargs.pop("xi", None)
    yi = kwargs.pop("yi", None)
    method = kwargs.pop("method", "linear")
    if kwargs:
        unknown = ", ".join(sorted(kwargs))
        raise TypeError(f"regular_grid() got unexpected keyword argument(s): {unknown}")
    if xi is None or yi is None:
        x = np.linspace(xx.min(), xx.max(), nx)
        y = np.linspace(yy.min(), yy.max(), ny)
        xi, yi = np.meshgrid(x, y, indexing="ij")
    if not args:
        return xi, yi

    from scipy.interpolate import CloughTocher2DInterpolator, LinearNDInterpolator, griddata
    from scipy.spatial import Delaunay

    points = np.column_stack((np.asarray(xx).ravel(), np.asarray(yy).ravel()))
    flattened = [np.asarray(field).ravel() for field in args]
    if method == "linear":
        triangulation = Delaunay(points)
        outputs = [
            LinearNDInterpolator(triangulation, field, fill_value=np.nan)(
                xi, yi, simplex_tolerance=1.0
            )
            for field in flattened
        ]
    elif method == "cubic":
        triangulation = Delaunay(points)
        outputs = [
            CloughTocher2DInterpolator(triangulation, field, fill_value=np.nan)(
                xi, yi, simplex_tolerance=1.0
            )
            for field in flattened
        ]
    else:
        outputs = [griddata(points, field, (xi, yi), method=method) for field in flattened]
    return (xi, yi, *outputs)


def poly_fit(x, y, order=3):
    """Return ascending-power basis callables and a truncated-SVD fit.

    Singular values below the absolute cutoff ``1e-10`` are discarded.

    Parameters
    ----------
    x, y : array_like
        Coordinates and values used to build the design matrix.
    order : int, default=3
        Highest power in the ascending polynomial basis.

    Returns
    -------
    tuple
        Basis callables and minimum-norm coefficient array.

    Raises
    ------
    TypeError, ValueError, numpy.linalg.LinAlgError
        Errors from array construction or the singular-value decomposition.
    """
    count = order + 1
    basis = [(lambda value, power=power: value**power) for power in range(count)]
    x_values = np.ma.asarray(x, dtype=float).filled(np.nan)
    design = np.power(x_values[:, None], np.arange(count)[None, :])
    left, singular, right = np.linalg.svd(design)
    inverse = np.zeros((count, len(y)))
    keep = singular >= 1.0e-10
    diagonal = np.diag_indices(len(singular))
    inverse[diagonal[0][keep], diagonal[1][keep]] = 1.0 / singular[keep]
    coefficients = right.T @ inverse @ left.T @ y
    return basis, coefficients


def reflect_and_hstack(Rho, Z, *args, quantities=None):
    """Reflect R-Z arrays through the first column and concatenate them.

    The first radial column is the symmetry plane and must be exactly zero;
    the remaining columns are reflected in reverse order.  Invalid shapes,
    nonfinite values and a nonzero symmetry column are rejected.
    """
    if quantities is not None:
        if args:
            raise ValueError("supply fields either positionally or through quantities")
        args = tuple(quantities)
    rho = np.asarray(Rho, dtype=float)
    z = np.asarray(Z, dtype=float)
    if rho.ndim != 2 or z.shape != rho.shape:
        raise ValueError("Rho and Z must be matching two-dimensional arrays")
    if rho.shape[1] < 2:
        raise ValueError("Rho must contain at least two radial columns to reflect")
    if not np.all(np.isfinite(rho)) or not np.all(np.isfinite(z)):
        raise ValueError("Rho and Z must contain only finite values")
    if not np.all(rho[:, 0] == 0.0):
        raise ValueError("the first radial column must be zero (symmetry plane)")
    fields = []
    for field in args:
        values = np.asarray(field, dtype=float)
        if values.shape != rho.shape:
            raise ValueError("supplied fields must match the Rho/Z shape")
        if not np.all(np.isfinite(values)):
            raise ValueError("supplied fields must contain only finite values")
        fields.append(np.hstack((values[:, -1:0:-1], values)))
    reflected_rho = np.hstack((-rho[:, -1:0:-1], rho))
    reflected_z = np.hstack((z[:, -1:0:-1], z))
    return (reflected_rho, reflected_z, *fields)


def transform_to_rtheta(Rho, Z, rho_component, z_component):
    """Convert meridional Cartesian components to polar components."""
    rho, z, radial_component, axial_component = np.broadcast_arrays(
        *[np.asarray(value, dtype=float) for value in (Rho, Z, rho_component, z_component)]
    )
    if not all(np.isfinite(value).all() for value in (rho, z, radial_component, axial_component)):
        raise ValueError("polar mapping inputs must be finite")
    radius = np.hypot(rho, z)
    if np.any(radius == 0.0):
        raise ValueError("polar basis is undefined at the origin")
    sin_theta, cos_theta = rho / radius, z / radius
    return (
        radius,
        np.arctan2(rho, z),
        radial_component * sin_theta + axial_component * cos_theta,
        radial_component * cos_theta - axial_component * sin_theta,
    )


def transform_to_rhoz(R, Theta, r_component, theta_component):
    """Convert polar position and vector components back to meridional form."""
    radius, theta, radial_component, angular_component = np.broadcast_arrays(
        *[np.asarray(value, dtype=float) for value in (R, Theta, r_component, theta_component)]
    )
    if not all(np.isfinite(value).all() for value in (radius, theta, radial_component, angular_component)) or np.any(radius <= 0.0):
        raise ValueError("finite polar inputs and positive radius required; origin basis undefined")
    sin_theta, cos_theta = np.sin(theta), np.cos(theta)
    return (
        radius * sin_theta,
        radius * cos_theta,
        radial_component * sin_theta + angular_component * cos_theta,
        radial_component * cos_theta - angular_component * sin_theta,
    )


def locs_to_vals(X, Y, Q, coord_list):
    """Select the nearest separable-grid value for each coordinate pair."""
    values = []
    for x, y in coord_list:
        ix = np.argmin(np.abs(X[0, :] - x))
        iy = np.argmin(np.abs(Y[:, 0] - y))
        values.append(Q[iy, ix])
    return values


def locs_to_vals_griddata(X, Y, Q, coord_list):
    """Interpolate a field at coordinate pairs with SciPy ``griddata``."""
    from scipy.interpolate import griddata
    xi, yi = zip(*coord_list)
    return griddata((X.flatten(), Y.flatten()), Q.flatten(), (xi, yi))


def locs_to_vals1D(X, Y, Q, coord_list):
    """Select the nearest point in a general flattened two-dimensional grid."""
    values = []
    flat_q = np.asarray(Q).ravel()
    for x, y in coord_list:
        index = ((X - x) ** 2 + (Y - y) ** 2).argmin()
        values.append(flat_q[index])
    return values


def get_fieldlines(contourset, level, start_coord=None, end_coord=None, clockwise=True, idx_check=[]):
    """Return the longest contour segment at ``level`` in requested order."""
    assert level in list(contourset.levels), f"level: {level} not found in contourset"
    index = list(contourset.levels).index(level)
    segments = contourset.allsegs[index]
    longest = max(segments, key=lambda segment: segment.shape[0])
    return parse_segment(longest, start_coord=start_coord, end_coord=end_coord, clockwise=clockwise)


def parse_segment(flpoints, start_coord=None, end_coord=None, clockwise=True):
    """Orient and optionally trim an ordered planar contour segment.

    Parameters
    ----------
    flpoints : array_like, shape (N, 2)
        Ordered contour vertices.
    start_coord, end_coord : array_like, optional
        Nearest vertices used as the start and inclusive terminal vertex.
    clockwise : bool, default=True
        Requested signed traversal direction.

    Returns
    -------
    ndarray
        The oriented and optionally trimmed segment.

    Raises
    ------
    TypeError, ValueError, IndexError
        Errors raised by NumPy for unsupported shapes or values.
    """
    points = np.asarray(flpoints)
    if start_coord is not None:
        start = np.asarray(start_coord)
        index = np.argmin(np.sum((points - start) ** 2, axis=1))
        points = np.roll(points, -index, axis=0)
    x, y = points[:, 0], points[:, 1]
    is_clockwise = np.sum((x[1:] - x[:-1]) * (y[1:] + y[:-1])) + (x[0] - x[-1]) * (y[0] + y[-1]) > 0
    if clockwise != is_clockwise:
        points = np.roll(points[::-1, :], 1, axis=0)
    end = len(points)
    if end_coord is not None:
        target = np.asarray(end_coord)
        end = np.argmin(np.sum((points - target) ** 2, axis=1)) + 1
    return points[:end, :]


def get_fieldline_distance(flpoints):
    """Return cumulative Euclidean distance along a polyline."""
    points = np.asarray(flpoints)
    distances = np.zeros(points.shape[0])
    distances[1:] = np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))
    return distances


def interp(Rho, Z, Q, flpoints):
    """Evaluate a separable rectangular field at paired line points inside the grid."""
    from scipy.interpolate import RectBivariateSpline
    rho = np.asarray(Rho, dtype=float)
    z = np.asarray(Z, dtype=float)
    quantity = np.asarray(Q, dtype=float)
    points = np.asarray(flpoints, dtype=float)
    if rho.ndim != 2 or z.shape != rho.shape or quantity.shape != rho.shape:
        raise ValueError("Rho, Z and Q must be equal-shape two-dimensional arrays")
    if points.ndim != 2 or points.shape[1] != 2:
        raise ValueError("flpoints must have shape (n_points, 2)")
    if not np.all(np.isfinite(points)):
        raise ValueError("query points must be finite and lie inside the closed grid support")
    r_axis = rho[0, :]
    z_axis = z[:, 0]
    inside = (
        (points[:, 0] >= r_axis[0]) & (points[:, 0] <= r_axis[-1])
        & (points[:, 1] >= z_axis[0]) & (points[:, 1] <= z_axis[-1])
    )
    if not np.all(inside):
        raise ValueError("query points must lie inside the closed grid support")
    spline = RectBivariateSpline(z_axis, r_axis, quantity)
    return np.asarray(spline(points[:, 1], points[:, 0], grid=False), dtype=float)


def flux_surface_avg(Rho, Z, B, flpoints, Q=None):
    """Compute ``integral(ds/B)`` or its Q-weighted average.

    The interpolated field must stay finite and strictly positive along the
    sampled path; nonpositive or nonfinite B is rejected before quadrature.
    """
    import scipy.integrate
    field = interp(Rho, Z, B, flpoints)
    if not np.all(np.isfinite(field)) or np.any(field <= 0.0):
        raise ValueError("interpolated B must be finite and positive along the sampled path")
    distance = get_fieldline_distance(flpoints)
    denominator = scipy.integrate.trapezoid(y=1.0 / field, x=distance)
    if Q is None:
        return denominator
    quantity = interp(Rho, Z, Q, flpoints)
    if not np.all(np.isfinite(quantity)):
        raise ValueError("interpolated Q must be finite along the sampled path")
    return scipy.integrate.trapezoid(y=quantity / field, x=distance) / denominator


def diff_central(x, y):
    """Return the first derivative from the shared nonuniform stencil."""
    return diff_12_central(x, y)[0]
