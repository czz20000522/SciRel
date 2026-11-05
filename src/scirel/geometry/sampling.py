"""Grid sampling and line-integral utilities used by geometry diagnostics."""

from __future__ import annotations

import numpy as np

from .numerics import diff_12_central

__all__ = [
    "transform_to_rtheta",
    "transform_to_rhoz",
    "regular_grid",
    "poly_fit",
    "reflect_and_hstack",
    "locs_to_vals",
    "locs_to_vals_griddata",
    "locs_to_vals1D",
    "get_fieldlines",
    "parse_segment",
    "get_fieldline_distance",
    "interp",
    "flux_surface_avg",
    "diff_central",
]


def regular_grid(
    xx,
    yy,
    *fields,
    nx=200,
    ny=200,
    xi=None,
    yi=None,
    method="linear",
):
    """Scattered-to-regular grid sampling

    Parameters
    ----------
    xx : float64
        Sample x coordinates [length or coordinate units] Shape: ``matching array shape``.
        Finite

    yy : float64
        Sample y coordinates [length or coordinate units] Shape: ``same shape as xx``.
        Finite

    *fields : float64, optional
        Scalar fields sampled on ``xx`` and ``yy`` [field units]. Each field must
        broadcast to the sample shape; outputs preserve positional order. Zero
        fields return only the generated or supplied coordinate grids.

    nx : int, optional
        Number of generated x grid points [1] Shape: ``scalar``. Integer accepted by
        numpy.linspace; used when xi or yi is missing Optional; default ``200``.

    ny : int, optional
        Number of generated y grid points [1] Shape: ``scalar``. Integer accepted by
        numpy.linspace; used when xi or yi is missing Optional; default ``200``.

    xi : float64 array-like or None, optional
        Query x coordinates [length or coordinate units] Shape: ``array_like or None``. Used
        with yi only when both are supplied; if either is None, both axes are generated
        Optional; default ``None``.

    yi : float64 array-like or None, optional
        Query y coordinates [length or coordinate units] Shape: ``same shape as xi or
        None``. Used with xi only when both are supplied; if either is None, both axes are
        generated Optional; default ``None``.

    method : str, optional
        SciPy scattered-data interpolation method [1] Shape: ``string``. One of 'linear',
        'nearest', or 'cubic' Optional; default ``'linear'``.

    Returns
    -------
    grid_and_fields : float64
        Tuple xi,yi and interpolated scalar fields [coordinate and field units] Shape:
        ``tuple of (nx,ny) arrays or supplied grid shape``. Original field order preserved

    Raises
    ------
    ValueError
        raises ValueError when method is outside its documented set or the samples, fields, or query coordinates violate the SciPy interpolation contract;
    TypeError
        Raises TypeError when required arguments are missing, the removed values mapping keyword is used, or an unknown keyword is supplied;

    See Also
    --------
    poly_fit : Ascending-power SVD polynomial fit.
    interp : Rectangular spline field query.
    reflect_and_hstack : Scalar half-plane reflection.

    Notes
    -----
    Interpolate scalar fields onto supplied grids or generated ij-indexed grids.
    When both explicit axes are absent, ``nx, ny`` control the generated grid size.

    **Coordinates.** xx,yy generic planar coordinates; generated output axes use ij order

    **Boundary.** Explicit xi,yi are used together; if either is omitted, both supplied grid
    axes are replaced

    **Preconditions.**

    * Finite matched planar sample arrays and positional field arrays
    * Requested grid/query points lie inside convex/interpolation support
    * Fields are passed as separate positional arguments; no values mapping alias is
      accepted

    **Limits.**

    * No outside-hull value synthesis or nonlinear interpolation accuracy claim

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.geometry.sampling import regular_grid
    >>> x, y = np.meshgrid([0.0, 0.5, 1.0], [0.0, 0.5, 1.0])
    >>> result = regular_grid(x, y, x + y, nx=4, ny=5)
    >>> assert len(result) == 3
    >>> assert result[2].shape == (4, 5)
    """
    if method not in ("linear", "nearest", "cubic"):
        raise ValueError(f"Unknown interpolation method {method!r} for 2 dimensional data")
    if xi is None or yi is None:
        x = np.linspace(xx.min(), xx.max(), nx)
        y = np.linspace(yy.min(), yy.max(), ny)
        xi, yi = np.meshgrid(x, y, indexing="ij")
    if not fields:
        return xi, yi

    from scipy.interpolate import CloughTocher2DInterpolator, LinearNDInterpolator, griddata
    from scipy.spatial import Delaunay

    points = np.column_stack((np.asarray(xx).ravel(), np.asarray(yy).ravel()))
    flattened = [np.asarray(field).ravel() for field in fields]
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
    """Ascending-power SVD polynomial fit

    Parameters
    ----------
    x : float64
        Sample coordinates [coordinate units] Shape: ``(M,)``. Finite matched

    y : float64
        Sample values [value units] Shape: ``(M,)``. Finite matched

    order : int, optional
        Highest polynomial power [dimensionless] Shape: ``scalar``. Nonnegative integer
        Optional; default ``3``.

    Returns
    -------
    basis_fns : float64
        Ascending power evaluators [coordinate**power] Shape: ``list(order+1)``. Functions
        retain exponent
    coefficients : float64
        Minimum-norm coefficients [value/coordinate**power] Shape: ``(order+1,)``. Singular
        values below1e-10 discarded

    Raises
    ------
    ValueError
        Raises ValueError or the underlying NumPy/SciPy exception for nonfinite, mismatched, unsorted, out-of-domain, or malformed inputs;

    See Also
    --------
    regular_grid : Scattered-to-regular grid sampling.
    interp : Rectangular spline field query.
    diff_central : Nonuniform interior first derivative.

    Notes
    -----
    Compute minimum-norm ascending-power coefficients with absolute singular cutoff1e-10

    **Coordinates.** Generic x,y sample units; coefficients y/x**power

    **Boundary.** No boundary model; over/underdetermined systems use same cutoff

    **Preconditions.**

    * Finite one-dimensional matched x,y
    * Integer order>=0 for supported fit

    **Limits.**

    * Absolute source cutoff is not a scale-invariant statistical rank policy
    * No uncertainty/confidence or ill-conditioning guarantee

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.geometry.sampling import poly_fit
    >>> _, coefficients = poly_fit(np.array([-1.0, 0.0, 1.0]), np.array([2.0, 1.0, 0.0]), order=1)
    >>> np.testing.assert_allclose(coefficients, [1.0, -1.0])
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
    """Scalar half-plane reflection

    Parameters
    ----------
    Rho : float64
        Nonnegative radial grid [length units] Shape: ``(Nz,Nr)``. Radial first column zero;
        at least two radial columns

    Z : float64
        Axial grid [length units] Shape: ``same as Rho``. Matching finite two-dimensional
        shape

    *args : real array-like values, optional
        Values broadcast against the reflected ``(Rho, Z)`` support. Supplying
        ``quantities`` instead uses that explicit sequence.

    quantities : list or None, optional
        Named scalar/even fields; alternative to positional fields [field units] Shape:
        ``list of grids or None``. Finite and shape-matched when supplied; do not combine
        with positional fields Optional; default ``None``.

    Returns
    -------
    reflected : float64
        Tuple reflected Rho,Z and scalar fields [coordinate and field units] Shape:
        ``(Nz,2*Nr-1) each``. Zero column represented once

    Raises
    ------
    ValueError
        Raises ValueError or the underlying NumPy/SciPy exception for nonfinite, mismatched, unsorted, out-of-domain, or malformed inputs; a nonzero first radial column, fewer than two radial columns, mismatched shapes or nonfinite arrays are rejected with ValueError;

    See Also
    --------
    transform_to_rtheta : Meridional polar position and vector projection.
    regular_grid : Scattered-to-regular grid sampling.

    Notes
    -----
    Reflect R across zero and duplicate Z and even scalar quantities without duplicate zero
    column

    **Coordinates.** Rho,Z planar grids with radial column order

    **Boundary.** First radial column zero; remaining columns reflected in reverse order

    **Preconditions.**

    * Matching finite Rho,Z and scalar field shapes
    * First radial column is zero, at least two radial columns are present, and supplied
      fields are even under radial reflection

    **Limits.**

    * No vector-component parity or signed-radius physical field interpretation

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.geometry.sampling import reflect_and_hstack
    >>> rho, z = np.meshgrid([0.0, 0.5, 1.0], [-0.2, 0.2])
    >>> reflected = reflect_and_hstack(rho, z, quantities=[rho * rho])
    >>> assert reflected[0].shape == (2, 5)
    >>> assert reflected[1].shape == (2, 5)
    >>> assert reflected[2].shape == (2, 5)
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
    """Meridional polar position and vector projection

    Parameters
    ----------
    Rho : finite real
        Signed meridional radial coordinate [caller length] Shape: ``broadcastable``. Not
        simultaneously zero with Z

    Z : finite real
        Axial coordinate [caller length] Shape: ``broadcastable``. Not simultaneously zero
        with Rho

    rho_component : finite real
        Vector component along rho [caller vector] Shape: ``broadcastable``. Coherent with
        z_component

    z_component : finite real
        Vector component along Z [caller vector] Shape: ``broadcastable``. Coherent with
        rho_component

    Returns
    -------
    position_and_vector : float64 tuple
        Tuple r,theta,u_r,u_theta [caller length,radian,caller vector,caller vector] Shape:
        ``four broadcasted arrays``. Orthogonal vector projection

    Raises
    ------
    ValueError
        ValueError for nonfinite input or origin;

    See Also
    --------
    transform_to_rhoz : Inverse meridional polar projection.
    reflect_and_hstack : Scalar half-plane reflection.

    Notes
    -----
    theta is radians from +Z toward +rho. The source pi/2+atan2(Z,Rho) gives cos(theta)=-Z/r
    and conflicts with its inverse. The corrected angle and orthogonal vector basis preserve
    position, norm and inverse mapping.

    **Coordinates.** Caller coherent length/vector units; theta radians.

    **Boundary.** Origin has no polar vector basis and rejects; nonzero points on the axis
    are valid.

    **Preconditions.**

    * Finite broadcastable real arrays; away from coordinate origin

    **Limits.**

    * Polar basis at the origin
    * Magnetic-axis curvature or topology

    Examples
    --------
    >>> from scirel.geometry.sampling import transform_to_rtheta
    >>> r, theta, radial, angular = transform_to_rtheta(0.0, 2.0, 3.0, 4.0)
    >>> assert (r, theta, radial, angular) == (2.0, 0.0, 4.0, 3.0)
    """
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
    """Inverse meridional polar projection

    Parameters
    ----------
    R : finite real
        Distance from origin [caller length] Shape: ``broadcastable``. Strictly positive

    Theta : finite real
        Meridional angle from +Z toward +rho [rad] Shape: ``broadcastable``. Periodic
        sine/cosine convention

    r_component : finite real
        Radial vector component [caller vector] Shape: ``broadcastable``. Coherent vector
        units

    theta_component : finite real
        Angular vector component [caller vector] Shape: ``broadcastable``. Coherent vector
        units

    Returns
    -------
    position_and_vector : float64 tuple
        Tuple rho,z,u_rho,u_z [caller length,caller length,caller vector,caller vector]
        Shape: ``four broadcasted arrays``. Orthogonal vector projection

    Raises
    ------
    ValueError
        ValueError for nonfinite input or origin;

    See Also
    --------
    transform_to_rtheta : Meridional polar position and vector projection.
    reflect_and_hstack : Scalar half-plane reflection.

    Notes
    -----
    Inverse of the same orthogonal meridional basis; theta radians from +Z toward +rho. This
    explicit inverse fixes the forward convention and preserves vector norm.

    **Coordinates.** Caller coherent length/vector units; theta radians.

    **Boundary.** Origin has no polar vector basis and rejects; nonzero points on the axis
    are valid.

    **Preconditions.**

    * Finite broadcastable real arrays; away from coordinate origin

    **Limits.**

    * Polar basis at the origin
    * Magnetic-axis curvature or topology

    Examples
    --------
    >>> from scirel.geometry.sampling import transform_to_rhoz
    >>> rho, z, radial, axial = transform_to_rhoz(2.0, 0.0, 4.0, 3.0)
    >>> assert (rho, z, radial, axial) == (0.0, 2.0, 3.0, 4.0)
    """
    radius, theta, radial_component, angular_component = np.broadcast_arrays(
        *[np.asarray(value, dtype=float) for value in (R, Theta, r_component, theta_component)]
    )
    if not all(
        np.isfinite(value).all() for value in (radius, theta, radial_component, angular_component)
    ) or np.any(radius <= 0.0):
        raise ValueError("finite polar inputs and positive radius required; origin basis undefined")
    sin_theta, cos_theta = np.sin(theta), np.cos(theta)
    return (
        radius * sin_theta,
        radius * cos_theta,
        radial_component * sin_theta + angular_component * cos_theta,
        radial_component * cos_theta - angular_component * sin_theta,
    )


def locs_to_vals(X, Y, Q, coord_list):
    """Field query Separable xy grid axis nearest-neighbor sampling

    Parameters
    ----------
    X : float64
        Point x coordinates [coordinate units] Shape: ``matched grid/sample shape``. For
        rectangular nearest X[0,:] is x axis

    Y : float64
        Point y coordinates [coordinate units] Shape: ``same as X``. For rectangular nearest
        Y[:,0] is y axis

    Q : float64
        Sample field [field units] Shape: ``same as X``. Finite

    coord_list : float64
        Desired coordinate pairs [coordinate units] Shape: ``list of (x,y)``. Finite queries

    Returns
    -------
    values : float64
        Sampled values [field units] Shape: ``query-count list or array``. Source list/array
        return preserved

    Raises
    ------
    ValueError
        Raises ValueError or the underlying NumPy/SciPy exception for nonfinite, mismatched, unsorted, out-of-domain, or malformed inputs;

    See Also
    --------
    locs_to_vals_griddata : Field query SciPy griddata with linear default.
    locs_to_vals1D : Field query Geometric nearest sample on any matching planar arrays.
    interp : Rectangular spline field query.

    Notes
    -----
    Choose x-column and y-row independently nearest each query

    **Coordinates.** X column coordinate, Y row coordinate or matched scattered point arrays

    **Boundary.** No out-of-support interpolation synthesis

    **Preconditions.**

    * Finite matched planar sample arrays and fields
    * Requested grid/query points lie inside convex/interpolation support

    **Limits.**

    * Rectangular and geometric nearest schemes are not asserted equivalent on irregular
      input
    * Outside-support and nonfinite-field cases are unqualified

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.geometry.sampling import locs_to_vals
    >>> x, y = np.meshgrid([0.0, 0.5, 1.0], [0.0, 0.5, 1.0])
    >>> values = locs_to_vals(x, y, x + 2.0 * y, [(0.5, 0.5)])
    >>> np.testing.assert_allclose(values, [1.5])
    """
    values = []
    for x, y in coord_list:
        ix = np.argmin(np.abs(X[0, :] - x))
        iy = np.argmin(np.abs(Y[:, 0] - y))
        values.append(Q[iy, ix])
    return values


def locs_to_vals_griddata(X, Y, Q, coord_list):
    """Field query SciPy griddata with linear default

    Parameters
    ----------
    X : float64
        Point x coordinates [coordinate units] Shape: ``matched grid/sample shape``. For
        rectangular nearest X[0,:] is x axis

    Y : float64
        Point y coordinates [coordinate units] Shape: ``same as X``. For rectangular nearest
        Y[:,0] is y axis

    Q : float64
        Sample field [field units] Shape: ``same as X``. Finite

    coord_list : float64
        Desired coordinate pairs [coordinate units] Shape: ``list of (x,y)``. Finite queries

    Returns
    -------
    values : float64
        Sampled values [field units] Shape: ``query-count list or array``. Source list/array
        return preserved

    Raises
    ------
    ValueError
        Raises ValueError or the underlying NumPy/SciPy exception for nonfinite, mismatched, unsorted, out-of-domain, or malformed inputs;

    See Also
    --------
    locs_to_vals : Field query Separable xy grid axis nearest-neighbor sampling.
    locs_to_vals1D : Field query Geometric nearest sample on any matching planar arrays.
    interp : Rectangular spline field query.

    Notes
    -----
    Interpolate field at query coordinate pairs

    **Coordinates.** X column coordinate, Y row coordinate or matched scattered point arrays

    **Boundary.** No out-of-support interpolation synthesis

    **Preconditions.**

    * Finite matched planar sample arrays and fields
    * Requested grid/query points lie inside convex/interpolation support

    **Limits.**

    * Rectangular and geometric nearest schemes are not asserted equivalent on irregular
      input
    * Outside-support and nonfinite-field cases are unqualified

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.geometry.sampling import locs_to_vals_griddata
    >>> x, y = np.meshgrid([0.0, 0.5, 1.0], [0.0, 0.5, 1.0])
    >>> values = locs_to_vals_griddata(x, y, x + 2.0 * y, [(0.5, 0.5)])
    >>> np.testing.assert_allclose(values, [1.5])
    """
    from scipy.interpolate import griddata

    xi, yi = zip(*coord_list)
    return griddata((X.flatten(), Y.flatten()), Q.flatten(), (xi, yi))


def locs_to_vals1D(X, Y, Q, coord_list):
    """Field query Geometric nearest sample on any matching planar arrays

    Parameters
    ----------
    X : float64
        Point x coordinates [coordinate units] Shape: ``matched grid/sample shape``. For
        rectangular nearest X[0,:] is x axis

    Y : float64
        Point y coordinates [coordinate units] Shape: ``same as X``. For rectangular nearest
        Y[:,0] is y axis

    Q : float64
        Sample field [field units] Shape: ``same as X``. Finite

    coord_list : float64
        Desired coordinate pairs [coordinate units] Shape: ``list of (x,y)``. Finite queries

    Returns
    -------
    values : float64
        Sampled values [field units] Shape: ``query-count list or array``. Source list/array
        return preserved

    Raises
    ------
    ValueError
        Raises ValueError or the underlying NumPy/SciPy exception for nonfinite, mismatched, unsorted, out-of-domain, or malformed inputs;

    See Also
    --------
    locs_to_vals : Field query Separable xy grid axis nearest-neighbor sampling.
    locs_to_vals_griddata : Field query SciPy griddata with linear default.
    interp : Rectangular spline field query.

    Notes
    -----
    Choose flattened point of minimum squared coordinate distance

    **Coordinates.** X column coordinate, Y row coordinate or matched scattered point arrays

    **Boundary.** No out-of-support interpolation synthesis

    **Preconditions.**

    * Finite matched planar sample arrays and fields
    * Requested grid/query points lie inside convex/interpolation support

    **Limits.**

    * Rectangular and geometric nearest schemes are not asserted equivalent on irregular
      input
    * Outside-support and nonfinite-field cases are unqualified

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.geometry.sampling import locs_to_vals1D
    >>> x, y = np.meshgrid([0.0, 0.5, 1.0], [0.0, 0.5, 1.0])
    >>> values = locs_to_vals1D(x, y, x + 2.0 * y, [(0.5, 0.5)])
    >>> np.testing.assert_allclose(values, [1.5])
    """
    values = []
    flat_q = np.asarray(Q).ravel()
    for x, y in coord_list:
        index = ((X - x) ** 2 + (Y - y) ** 2).argmin()
        values.append(flat_q[index])
    return values


def get_fieldlines(
    contourset,
    level,
    start_coord=None,
    end_coord=None,
    clockwise=True,
):
    """Contour field-line selection

    Parameters
    ----------
    contourset : contour-like object
        Object exposing levels and allsegs [levels in caller flux-label units; vertices
        length] Shape: ``contour object``. Each allsegs entry contains finite planar
        segments

    level : float64
        Requested contour level [caller flux-label units] Shape: ``scalar``. Exact
        membership

    start_coord : float64, optional
        Nearest selected starting coordinate [length units] Shape: ``(2,) or None``. Exact
        nearest-vertex selection Optional; default ``None``.

    end_coord : float64, optional
        Nearest terminal coordinate included in output [length units] Shape: ``(2,) or
        None``. Terminal vertex retained; no interpolated crossing Optional; default
        ``None``.

    clockwise : bool, optional
        Desired signed polygon orientation [dimensionless] Shape: ``scalar``. Signed
        shoelace-like source test Optional; default ``True``.

    Returns
    -------
    segment : float64
        Selected parsed vertices [length units] Shape: ``(M,2)``. Largest segment selected
        by original point count

    Raises
    ------
    ValueError
        Raises ValueError or the underlying NumPy/SciPy exception for nonfinite, mismatched, unsorted, out-of-domain, or malformed inputs; Unknown contour levels raise ValueError;

    See Also
    --------
    parse_segment : Contour segment orientation, closure, and endpoints.
    contour_points : Contour field-line collection contour_points.
    get_fieldline_distance : Cumulative polyline distance.

    Notes
    -----
    Select largest vertex-count segment at exact contour level and parse its
    orientation/endpoints

    **Coordinates.** Planar segment vertices and exact level labels

    **Boundary.** Nearest endpoint convention from parse_segment

    **Preconditions.**

    * Requested level exactly appears in contourset.levels
    * At least one finite segment exists

    **Limits.**

    * Does not establish unique physical flux surface or connect separate segments

    Examples
    --------
    >>> import numpy as np
    >>> from types import SimpleNamespace
    >>> from scirel.geometry.sampling import get_fieldlines
    >>> segment = np.array([[0.0, 0.0], [0.0, 1.0], [1.0, 1.0], [1.0, 0.0]])
    >>> contours = SimpleNamespace(levels=[0.2], allsegs=[[segment]])
    >>> selected = get_fieldlines(contours, 0.2)
    >>> assert selected.shape == (4, 2)
    >>> np.testing.assert_array_equal(selected, segment)
    """
    if level not in list(contourset.levels):
        raise ValueError(f"level: {level} not found in contourset")
    index = list(contourset.levels).index(level)
    segments = contourset.allsegs[index]
    longest = max(segments, key=lambda segment: segment.shape[0])
    return parse_segment(longest, start_coord=start_coord, end_coord=end_coord, clockwise=clockwise)


def parse_segment(flpoints, start_coord=None, end_coord=None, clockwise=True):
    """Contour segment orientation, closure, and endpoints

    Parameters
    ----------
    flpoints : float64
        Ordered planar path vertices [length units] Shape: ``(N,2)``. Finite supplied
        ordering; exact first/last duplicate denotes closure

    start_coord : float64, optional
        Nearest selected starting coordinate [length units] Shape: ``(2,) or None``. Exact
        nearest-vertex selection Optional; default ``None``.

    end_coord : float64, optional
        Nearest terminal coordinate included in output [length units] Shape: ``(2,) or
        None``. Terminal vertex retained; no interpolated crossing; presence suppresses
        automatic re-closing Optional; default ``None``.

    clockwise : bool, optional
        Desired signed polygon orientation [dimensionless] Shape: ``scalar``. Signed
        shoelace-like source test Optional; default ``True``.

    Returns
    -------
    segment : float64
        Ordered selected vertices [length units] Shape: ``(M,2)``. No synthetic or omitted
        default endpoint; an exact input closure marker remains exactly once as the terminal
        vertex when end_coord is None

    Raises
    ------
    ValueError
        Raises ValueError or the underlying NumPy/SciPy exception for nonfinite, mismatched, unsorted, out-of-domain, or malformed inputs;

    See Also
    --------
    get_fieldlines : Contour field-line selection.
    get_fieldline_distance : Cumulative polyline distance.
    interp : Rectangular spline field query.

    Notes
    -----
    Roll to nearest start, orient by signed polygon test, normalize an exact closure marker,
    and retain selected terminal vertex

    **Coordinates.** Planar coordinates in length units

    **Boundary.** Default restores one exact closure edge; explicit nearest end is inclusive
    without automatic re-closing

    **Preconditions.**

    * Finite planar segment with meaningful polygon orientation
    * Any repeated closure endpoint matches the first vertex exactly

    **Limits.**

    * Non-exact repeated endpoints and general topology policies are not generalized

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.geometry.sampling import parse_segment
    >>> segment = np.array([[0.0, 0.0], [0.0, 1.0], [1.0, 1.0], [1.0, 0.0]])
    >>> np.testing.assert_array_equal(parse_segment(segment), segment)
    """
    points = np.asarray(flpoints)
    closed = points.ndim == 2 and points.shape[0] > 1 and np.array_equal(points[0], points[-1])
    if closed:
        points = points[:-1]
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
    segment = points[:end, :]
    if closed and end_coord is None:
        segment = np.vstack((segment, segment[:1]))
    return segment


def get_fieldline_distance(flpoints):
    """Cumulative polyline distance

    Parameters
    ----------
    flpoints : float64
        Ordered planar path vertices [length units] Shape: ``(N,2)``. Finite supplied
        ordering

    Returns
    -------
    distance : float64
        Cumulative path distance [length units] Shape: ``(N,)``. Nondecreasing; duplicate
        vertices give zero increments

    Raises
    ------
    ValueError
        Raises ValueError or the underlying NumPy/SciPy exception for nonfinite, mismatched, unsorted, out-of-domain, or malformed inputs;

    See Also
    --------
    interp : Rectangular spline field query.
    flux_surface_avg : B-weighted line reduction.
    parse_segment : Contour segment orientation, closure, and endpoints.

    Notes
    -----
    Accumulate Euclidean adjacent-vertex distances from zero

    **Coordinates.** Planar pairs in coherent length units

    **Boundary.** Starts at zero; no implicit closing segment

    **Preconditions.**

    * Finite ordered planar vertices

    **Limits.**

    * No true smooth-curve arclength or implicit closure

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.geometry.sampling import get_fieldline_distance
    >>> points = np.array([[0.0, 0.0], [3.0, 0.0], [3.0, 4.0]])
    >>> np.testing.assert_allclose(get_fieldline_distance(points), [0.0, 3.0, 7.0])
    """
    points = np.asarray(flpoints)
    distances = np.zeros(points.shape[0])
    distances[1:] = np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))
    return distances


def interp(Rho, Z, Q, flpoints):
    """Rectangular spline field query

    Parameters
    ----------
    Rho : float64
        Rectangular radial x grid [length units] Shape: ``(Nz,Nr)``. Rho[0,:] strictly
        increasing

    Z : float64
        Rectangular axial y grid [length units] Shape: ``same as Rho``. Z[:,0] strictly
        increasing

    Q : float64
        Rectangular field [field units] Shape: ``same as Rho``. Finite

    flpoints : float64
        Ordered planar path vertices [length units] Shape: ``(N,2)``. Finite supplied
        ordering; each query point must lie inside the closed grid support

    Returns
    -------
    values : float64
        Interpolated field along path [field units] Shape: ``(N,)``. Ordering follows
        flpoints

    Raises
    ------
    ValueError
        Raises ValueError or the underlying NumPy/SciPy exception for nonfinite, mismatched, unsorted, out-of-domain, or malformed inputs; out-of-grid or nonfinite query points are rejected with ValueError instead of being extrapolated;

    See Also
    --------
    regular_grid : Scattered-to-regular grid sampling.
    get_fieldlines : Contour field-line selection.
    flux_surface_avg : B-weighted line reduction.

    Notes
    -----
    Evaluate bicubic rectangular field interpolation at ordered path vertices

    **Coordinates.** xy row/column grid and planar flpoints

    **Boundary.** Queries must lie inside the closed grid support; out-of-grid or nonfinite
    query points are rejected rather than extrapolated.

    **Preconditions.**

    * Finite separable xy grid with at least four distinct points per axis
    * Finite Q and finite query coordinates inside the closed grid support

    **Limits.**

    * Out-of-grid spline extrapolation is not provided (outside queries are rejected);
      arbitrary nonlinear interpolation errors are unqualified

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.geometry.sampling import interp
    >>> rho, z = np.meshgrid(np.linspace(0.0, 1.0, 5), np.linspace(0.0, 1.0, 5))
    >>> points = np.array([[0.2, 0.3], [0.6, 0.7]])
    >>> np.testing.assert_allclose(interp(rho, z, rho + 2.0 * z, points), [0.8, 2.0])
    """
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
        (points[:, 0] >= r_axis[0])
        & (points[:, 0] <= r_axis[-1])
        & (points[:, 1] >= z_axis[0])
        & (points[:, 1] <= z_axis[-1])
    )
    if not np.all(inside):
        raise ValueError("query points must lie inside the closed grid support")
    spline = RectBivariateSpline(z_axis, r_axis, quantity)
    return np.asarray(spline(points[:, 1], points[:, 0], grid=False), dtype=float)


def flux_surface_avg(Rho, Z, B, flpoints, Q=None):
    """B-weighted line reduction

    Parameters
    ----------
    Rho : float64
        Rectangular radial x grid [length units] Shape: ``(Nz,Nr)``. Rho[0,:] strictly
        increasing

    Z : float64
        Rectangular axial y grid [length units] Shape: ``same as Rho``. Z[:,0] strictly
        increasing

    B : float64
        Positive weight field [field units] Shape: ``same as Rho``. Finite and strictly
        positive on the sampled path; nonpositive or nonfinite interpolated values are
        rejected before quadrature

    flpoints : float64
        Ordered planar path vertices [length units] Shape: ``(N,2)``. Finite supplied
        ordering

    Q : float64 array or None, optional
        Optional quantity to average [quantity units] Shape: ``grid-shaped or None``. Finite
        matched shape when supplied Optional; default ``None``.

    Returns
    -------
    reduction : float64
        Scalar weighted integral or average [length/field when Q absent; quantity units when
        present] Shape: ``scalar``. No volume-per-flux interpretation without external
        closure

    Raises
    ------
    ValueError
        Raises ValueError or the underlying NumPy/SciPy exception for nonfinite, mismatched, unsorted, out-of-domain, or malformed inputs;

    See Also
    --------
    interp : Rectangular spline field query.
    get_fieldline_distance : Cumulative polyline distance.
    compute_flux_surface_inverse_field_average : Polyline inverse-field measure and weighted mean.

    Notes
    -----
    Return integral(1/B ds) or integral(Q/B ds)/integral(1/B ds)

    **Coordinates.** xy rectangular grids and planar path with explicit chord arclength

    **Boundary.** No line closing or toroidal geometric factor

    **Preconditions.**

    * Finite positive B along finite interior path
    * Finite matching Q when supplied
    * Grid satisfies rectangular-spline and path-distance contracts

    **Limits.**

    * Physical flux-volume normalization/closed-surface interpretation remains unqualified
    * Zero/nonfinite B and outside-support queries are outside claim

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.geometry.sampling import flux_surface_avg
    >>> rho, z = np.meshgrid(np.linspace(0.0, 1.0, 5), np.linspace(-0.2, 0.2, 5))
    >>> path = np.column_stack([np.linspace(0.0, 1.0, 33), np.zeros(33)])
    >>> np.testing.assert_allclose(flux_surface_avg(rho, z, np.ones_like(rho), path), 1.0)
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
    """Nonuniform interior first derivative

    Parameters
    ----------
    x : float64
        Abscissae [coordinate units] Shape: ``(N,)``. Strictly increasing finite

    y : float64
        Samples [value units] Shape: ``(N,)``. Finite matched N

    Returns
    -------
    derivative : float64
        First interior derivative [value per coordinate] Shape: ``(N-2,)``. Quadratic
        exactness

    Raises
    ------
    ValueError
        Raises ValueError or the underlying NumPy/SciPy exception for nonfinite, mismatched, unsorted, out-of-domain, or malformed inputs;

    See Also
    --------
    diff_12_central : Nonuniform interior first and second derivatives.
    interp : Rectangular spline field query.

    Notes
    -----
    Return first interior derivative using the shared quadratic nonuniform operator

    **Coordinates.** Generic coherent coordinate/value units

    **Boundary.** No endpoint values

    **Preconditions.**

    * Finite matched one-dimensional x,y with N>=3
    * x strictly increasing

    **Limits.**

    * Periodic endpoints, noisy-data inference and conditioning extremes are unqualified

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.geometry.sampling import diff_central
    >>> x = np.array([0.0, 0.3, 1.0])
    >>> np.testing.assert_allclose(diff_central(x, x * x), [0.6])
    """
    return diff_12_central(x, y)[0]
