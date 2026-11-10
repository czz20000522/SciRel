"""Parametric field-line geometry and bounded diagnostic operations."""

from __future__ import annotations

import numpy as np

__all__ = [
    "d_ds_arclength",
    "FieldLineSet",
    "FieldLine",
    "HelperFieldLine",
    "Boundary",
    "contour_points",
    "helper_contour_points",
]


def d_ds_arclength(vertices, values):
    """Actual-arclength first derivative

    Parameters
    ----------
    vertices : float64
        Ordered planar vertices [length units] Shape: ``(N,2)``. Finite and adjacent
        distinct

    values : float64
        Sampled scalar values [value units] Shape: ``(N,)``. Finite matched N

    Returns
    -------
    derivative : float64
        First derivative including endpoints [value per length] Shape: ``(N,)``. Derivative
        along declared ordering

    Raises
    ------
    ValueError
        ValueError is raised for wrong shapes, too few samples, nonfinite values, or duplicate adjacent vertices.

    See Also
    --------
    FieldLine : FieldLine geometry and diagnostics.
    HelperFieldLine : HelperFieldLine geometry and diagnostics.
    get_fieldline_distance : Cumulative polyline distance.

    Notes
    -----
    Use a three-point unequal-spacing stencil at interior and one-sided quadratic stencils
    at both endpoints.

    **Coordinates.** Vertices in length units; values in caller units.

    **Boundary.** No periodic closure is inferred; endpoints use one-sided stencils.

    **Preconditions.**

    * Vertices and values are finite, matched, and have N>=3.
    * Adjacent vertices are distinct.

    **Limits.**

    * Smooth-curve arclength reconstruction, periodic endpoint stencils, and noise
      statistics.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.geometry.fieldline import d_ds_arclength
    >>> p=np.array([[0.,0.],[.3,0.],[1.,0.]])
    >>> assert np.allclose(d_ds_arclength(p,p[:,0]**2),2*p[:,0])
    """
    points = np.asarray(vertices, dtype=float)
    values = np.asarray(values, dtype=float)
    if points.ndim != 2 or points.shape[1] != 2 or values.ndim != 1:
        raise ValueError("vertices must be (N,2), values must be (N,), N >= 3")
    if points.shape[0] != values.size or values.size < 3:
        raise ValueError("vertices must be (N,2), values must be (N,), N >= 3")
    if not np.isfinite(points).all() or not np.isfinite(values).all():
        raise ValueError("vertices and values must be finite")
    step = np.linalg.norm(np.diff(points, axis=0), axis=1)
    if np.any(step <= 0.0):
        raise ValueError("adjacent vertices must be distinct")
    coordinate = np.r_[0.0, np.cumsum(step)]
    left = coordinate[1:-1] - coordinate[:-2]
    right = coordinate[2:] - coordinate[1:-1]
    derivative = np.empty_like(values)
    derivative[1:-1] = (
        left * (values[2:] - values[1:-1]) / right + right * (values[1:-1] - values[:-2]) / left
    ) / (left + right)
    h0, h1 = coordinate[1] - coordinate[0], coordinate[2] - coordinate[1]
    derivative[0] = (
        -(2.0 * h0 + h1) / (h0 * (h0 + h1)) * values[0]
        + (h0 + h1) / (h0 * h1) * values[1]
        - h0 / (h1 * (h0 + h1)) * values[2]
    )
    h0, h1 = coordinate[-1] - coordinate[-2], coordinate[-2] - coordinate[-3]
    derivative[-1] = (
        (2.0 * h0 + h1) / (h0 * (h0 + h1)) * values[-1]
        - (h0 + h1) / (h0 * h1) * values[-2]
        + h0 / (h1 * (h0 + h1)) * values[-3]
    )
    return derivative


def _sample_fieldline(vertices, R, Z, Q, method, filter_nonfinite):
    """Evaluate a field on line vertices using the requested SciPy method."""
    from scipy.interpolate import CloughTocher2DInterpolator, RectBivariateSpline, griddata

    points = np.asarray(vertices, dtype=float)
    r_grid, z_grid, quantity = (np.asarray(value) for value in (R, Z, Q))
    rectangular = (
        method == "cubic"
        and not np.iscomplexobj(quantity)
        and r_grid.ndim == 2
        and min(r_grid.shape) >= 4
        and r_grid.shape == z_grid.shape == quantity.shape
        and all(np.isfinite(value).all() for value in (r_grid, z_grid, quantity))
        and np.array_equal(r_grid, np.broadcast_to(r_grid[0], r_grid.shape))
        and np.array_equal(z_grid, np.broadcast_to(z_grid[:, 0, None], z_grid.shape))
    )
    if rectangular:
        r_axis, z_axis, values = r_grid[0].copy(), z_grid[:, 0].copy(), quantity.copy()
        if np.all(np.diff(r_axis) < 0.0):
            r_axis, values = r_axis[::-1], values[:, ::-1]
        if np.all(np.diff(z_axis) < 0.0):
            z_axis, values = z_axis[::-1], values[::-1, :]
        if np.all(np.diff(r_axis) > 0.0) and np.all(np.diff(z_axis) > 0.0):
            query_r, query_z = points[:, 0], points[:, 1]
            inside = (
                np.isfinite(query_r)
                & np.isfinite(query_z)
                & (query_r >= r_axis[0])
                & (query_r <= r_axis[-1])
                & (query_z >= z_axis[0])
                & (query_z <= z_axis[-1])
            )
            result = np.full(points.shape[0], np.nan)
            spline = RectBivariateSpline(z_axis, r_axis, values, kx=3, ky=3, s=0)
            result[inside] = spline.ev(query_z[inside], query_r[inside])
            # FITPACK interpolation should reproduce supplied nodes exactly,
            # including a zero value at a node. The index clamp only locates the nearest
            # node of an inside query; it is not a value clamp.
            r_index = np.clip(np.searchsorted(r_axis, query_r), 0, r_axis.size - 1)
            z_index = np.clip(np.searchsorted(z_axis, query_z), 0, z_axis.size - 1)
            at_node = inside & (query_r == r_axis[r_index]) & (query_z == z_axis[z_index])
            result[at_node] = values[z_index[at_node], r_index[at_node]]
            return result

    mask = np.isfinite(quantity.ravel()) if filter_nonfinite else np.ones(quantity.size, dtype=bool)
    source_points = np.column_stack((r_grid.ravel()[mask], z_grid.ravel()[mask]))
    source_values = quantity.ravel()[mask]
    query = (points[:, 0], points[:, 1])
    if method == "cubic":
        return CloughTocher2DInterpolator(source_points, source_values, tol=1e-12)(*query)
    return griddata(source_points, source_values, xi=query, method=method)


def _curve_curvature(vertices, br, bz):
    """Differentiate normalized field direction along a local curve parameter."""
    points = np.asarray(vertices, dtype=float)
    field = np.column_stack((br, bz))
    if (
        points.ndim != 2
        or points.shape[1] != 2
        or points.shape[0] < 3
        or field.shape != points.shape
    ):
        raise ValueError("curvature requires finite vertices (N,2), N >= 3")
    if not np.isfinite(points).all():
        raise ValueError("curvature requires finite vertices (N,2), N >= 3")
    magnitude = np.hypot(field[:, 0], field[:, 1])
    if not np.isfinite(magnitude).all() or np.any(magnitude <= 0.0):
        raise ValueError("curvature requires finite nonzero field inside interpolation support")
    segment = np.linalg.norm(np.diff(points, axis=0), axis=1)
    if np.any(segment <= 0.0):
        raise ValueError("adjacent vertices must be distinct")
    coordinate = np.r_[0.0, np.cumsum(segment)]
    direction = field / magnitude[:, None]
    samples = np.column_stack((points, direction))
    width = min(5, points.shape[0])
    offsets = np.arange(width)
    target_moment = np.zeros(width)
    target_moment[1] = 1.0
    # The moving window needs ``width`` rows, so its start is clamped onto the closed
    # range of valid starts. The clamp chooses which samples are fitted, not a value.
    starts = np.minimum(
        np.maximum(np.arange(points.shape[0]) - width // 2, 0), points.shape[0] - width
    )
    derivative = np.empty_like(samples)
    for begin in range(0, points.shape[0], 4096):
        end = min(begin + 4096, points.shape[0])
        rows = np.arange(begin, end)
        indices = starts[rows, None] + offsets
        local = coordinate[indices] - coordinate[rows, None]
        scale = np.max(np.abs(local), axis=1)
        normalized = local / scale[:, None]
        vandermonde = normalized[:, :, None] ** offsets[None, None, :]
        rhs = np.broadcast_to(target_moment, (rows.size, width))[..., None]
        weights = np.linalg.solve(vandermonde.transpose(0, 2, 1), rhs)[..., 0] / scale[:, None]
        derivative[rows] = np.einsum("ij,ijk->ik", weights, samples[indices] - samples[rows, None])
    tangent, direction_derivative = derivative[:, :2], derivative[:, 2:]
    speed = np.linalg.norm(tangent, axis=1)
    sign = np.sign(np.sum(tangent * direction, axis=1))
    if (
        not np.isfinite(speed).all()
        or np.any(speed <= 0.0)
        or not np.isfinite(sign).all()
        or np.any(sign == 0.0)
    ):
        raise ValueError("curvature requires finite nonzero tangent-aligned field")
    return sign[:, None] * direction_derivative / speed[:, None]


def _bounded_intersection(line, boundary):
    from scipy.optimize import least_squares

    lower = np.array([float(line.u.min()), float(boundary.u.min())])
    upper = np.array([float(line.u.max()), float(boundary.u.max())])
    geometry = np.vstack((line.verts, boundary.verts))
    tolerance = 1e-9 * max(1.0, float(np.max(np.ptp(geometry, axis=0))))

    def separation(parameter):
        return np.asarray(line.interpolate(parameter[0])) - np.asarray(
            boundary.interpolate(parameter[1])
        )

    roots = []
    for start_line in np.linspace(lower[0], upper[0], 7):
        for start_boundary in np.linspace(lower[1], upper[1], 7):
            result = least_squares(
                separation,
                [start_line, start_boundary],
                bounds=(lower, upper),
                xtol=1e-13,
                ftol=1e-13,
                gtol=1e-13,
            )
            if result.success and np.linalg.norm(separation(result.x)) <= tolerance:
                if not any(np.linalg.norm(result.x - root) < 1e-6 for root in roots):
                    roots.append(result.x)
    if not roots:
        raise ValueError("no intersection found within fitted parameter intervals")
    if len(roots) > 1:
        raise ValueError("multiple intersections found; crossing selection is undefined")
    return float(roots[0][0])


def _fit_parametric_curve(vertices, u=None, s=0.0, k=2, npts=1000, periodic=False):
    from scipy.interpolate import splev, splprep

    tck, fitted_u = splprep(np.asarray(vertices).T, u=u, k=k, s=s, per=int(periodic))
    sample_u = np.linspace(fitted_u.min(), fitted_u.max(), npts)
    fitted = np.column_stack(splev(sample_u, tck, der=0))
    return tck, sample_u, fitted


class FieldLineSet:
    """Contour field-line collection FieldLineSet

    Parameters
    ----------
    contourset : contour-like object
        Object exposing levels and allsegs [levels in caller flux-label units; vertices
        length] Shape: ``contour object``. Each allsegs entry contains finite planar
        segments

    **kwargs : keyword arguments, optional
        Forwarded unchanged to every :class:`FieldLine` constructor.

    Returns
    -------
    collection : Python object
        Per-level lists of target line objects [same as target line] Shape: ``FieldLineSet
        object``. The flset mapping is keyed by contour level and preserves segment order.

    Attributes
    ----------
    flset : dict
        Mapping from each contour level [caller flux-label units] to the list
        of constructed FieldLine objects [one line object per segment].

    Raises
    ------
    ValueError
        Underlying array, spline, or interpolation validation errors propagate;
        the callable adds no input repair or fallback.

    See Also
    --------
    FieldLine : FieldLine geometry and diagnostics.
    HelperFieldLine : HelperFieldLine geometry and diagnostics.
    contour_points : Contour field-line collection contour_points.

    Notes
    -----
    Construct FieldLine instances for every segment and store them in the flset mapping.

    **Coordinates.** Segment vertices in caller length units; levels in caller flux-label
    units.

    **Boundary.** Every segment must be accepted by the FieldLine constructor.

    **Preconditions.**

    * The contour object exposes matching levels and allsegs.
    * Optional kwargs are forwarded to each FieldLine.

    **Limits.**

    * Contour topology repair, field reconstruction, and physical flux-surface
      qualification.

    Examples
    --------
    >>> import numpy as np
    >>> from types import SimpleNamespace
    >>> from scirel.geometry.fieldline import FieldLineSet
    >>> c=SimpleNamespace(levels=[.2],allsegs=[[np.array([[.2,0.],[.6,0.],[1.,0.]])]])
    >>> r=FieldLineSet(c)
    >>> assert len(r.flset[.2])==1
    """

    def __init__(self, contourset, **kwargs):
        self.flset = {
            level: [FieldLine(level, segment, **kwargs) for segment in contourset.allsegs[index]]
            for index, level in enumerate(contourset.levels)
        }


class FieldLine:
    """FieldLine geometry and diagnostics

    Parameters
    ----------
    psi : float64
        Contour level label [caller flux-label units] Shape: ``scalar``. Not a reconstructed
        flux field

    verts : float64
        Contour vertices [length units] Shape: ``(M,2)``. Finite ordered points sufficient
        for the default quadratic splprep fit; adjacent fitted samples must remain distinct.

    **kwargs : keyword arguments, optional
        Controls passed to the internal parametric spline fit, including ``u``, ``s``,
        ``k``, and ``npts``.

    Returns
    -------
    line : Python object
        Object exposing verts,tck,u and arclength/field diagnostics [length; gradient caller
        flux per length; curvature inverse length] Shape: ``line object``. get_ds returns
        first segment length, not a uniform-step guarantee

    Attributes
    ----------
    psi : scalar
        Caller-supplied contour label [caller flux-label units].
    verts : ndarray
        Fitted planar vertices [m], shape ``(npts, 2)`` in fitted-parameter
        order.
    u : ndarray
        Sampling parameters of the fitted spline [dimensionless].
    tck : tuple
        SciPy spline representation [mixed caller units]. Treat it as an opaque
        implementation detail.
    ubound0, ubound1 : float, optional
        Intersection parameters created by ``apply_boundary`` [dimensionless].

    Raises
    ------
    ValueError
        ValueError is raised for undefined curvature support, duplicate vertices, invalid flux grids, or nonfinite interpolation results; Intersection raises ValueError when no unique fitted-interval crossing is found;

    See Also
    --------
    HelperFieldLine : HelperFieldLine geometry and diagnostics.
    Boundary : Parametric boundary interpolation.
    contour_points : Contour field-line collection contour_points.

    Notes
    -----
    Fit an ordered parametric line; field curvature differentiates normalized interpolated
    BR,BZ along the fitted geometry.

    **Coordinates.** Planar R,Z in caller length units; psi is a contour label.

    **Boundary.** Intersections search only the fitted parameter intervals and reject zero
    or multiple crossings.

    **Preconditions.**

    * Finite vertices are sufficient for splprep and adjacent fitted samples remain
      distinct.
    * Field curvature needs finite nonzero B and nonzero tangent projection.

    **Limits.**

    * Arbitrary contour topology, magnetic-axis limits, field-line certification, and
      universal error bounds.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.geometry.fieldline import FieldLine
    >>> line=FieldLine(.2,np.array([[.2,0.],[.6,0.],[1.,0.]]))
    >>> assert line.verts.shape==(1000,2)
    """

    def __init__(self, psi, verts, **kwargs):
        self.psi = psi
        self._verts = verts
        self._interpolate_verts(**kwargs)

    def is_closed(self):
        """Return whether the original contour closes exactly.

        Returns
        -------
        is_closed : bool
            ``True`` when the first and last input vertices are exactly equal
            [dimensionless]. The fit does not make a closed contour from an
            approximately closed one.

        Raises
        ------
        No exception is raised for a successfully constructed line.

        See Also
        --------
        get_bounded_fl : Sample a line between two boundary intersections.

        Notes
        -----
        The check is on the original vertices, not on the fitted samples. It is
        an exact equality test and therefore does not infer closure from a
        distance tolerance.

        Examples
        --------
        >>> import numpy as np
        >>> from scirel.geometry import FieldLine
        >>> bool(FieldLine(0.2, np.array([[0., 0.], [.5, 0.], [1., 0.]])).is_closed())
        False
        """
        return np.all(self._verts[0, :] == self._verts[-1, :])

    def _interpolate_verts(self, u=None, s=0.0, k=2, npts=1000):
        self.tck, self.u, self.verts = _fit_parametric_curve(
            self._verts, u=u, s=s, k=k, npts=npts, periodic=self.is_closed()
        )

    def interpolate(self, u):
        """Evaluate the fitted line at spline parameters ``u``.

        Parameters
        ----------
        u : real array-like
            Spline parameters in the fitted interval [dimensionless]. Scalars
            and arrays are accepted; values outside the interval are passed to
            SciPy without an additional domain check.

        Returns
        -------
        points : sequence of ndarray
            ``[R, Z]`` coordinate arrays [m], one array per planar axis. A
            scalar parameter gives two scalars; an array of shape ``S`` gives
            two arrays of shape ``S``.

        Raises
        ------
        ValueError
            If SciPy rejects the parameter array or the stored spline
            representation is invalid.

        See Also
        --------
        get_svec : Cumulative fitted polyline distance.
        get_bounded_fl : Sample between two boundary intersections.

        Notes
        -----
        ``u`` is the spline parameter, not arclength. No physical distance
        conversion or endpoint clamping is applied by this method.

        Examples
        --------
        >>> import numpy as np
        >>> from scirel.geometry import FieldLine
        >>> line = FieldLine(0.2, np.array([[0., 0.], [.5, 0.], [1., 0.]]))
        >>> np.testing.assert_allclose(line.interpolate([0., 1.]), [[0., 1.], [0., 0.]], atol=1e-8)
        """
        from scipy.interpolate import splev

        return splev(u, self.tck, der=0)

    def get_svec(self):
        """Return cumulative fitted-polyline distance along the line.

        Returns
        -------
        svec : ndarray of float64, shape (npts,)
            Cumulative Euclidean distance from the first fitted vertex [m].
            The first entry is zero and entries are nondecreasing.

        Raises
        ------
        No exception is raised for a successfully constructed line.

        See Also
        --------
        get_length : Total fitted-polyline length.
        d_ds : Derivative with respect to fitted arclength.

        Notes
        -----
        The sum is over the discrete fitted vertices, not an analytic spline
        integral. It therefore depends on the configured ``npts``.

        Examples
        --------
        >>> import numpy as np
        >>> from scirel.geometry import FieldLine
        >>> line = FieldLine(0.2, np.array([[0., 0.], [.5, 0.], [1., 0.]]))
        >>> np.testing.assert_allclose(line.get_svec()[0], 0.0)
        """
        distance = np.zeros(self.verts.shape[0])
        distance[1:] = np.cumsum(np.linalg.norm(np.diff(self.verts, axis=0), axis=1))
        return distance

    def get_length(self):
        """Return total fitted-polyline length.

        Returns
        -------
        length : float
            Last entry of :meth:`get_svec` [m].

        Raises
        ------
        No exception is raised for a successfully constructed line.

        See Also
        --------
        get_svec : Cumulative fitted-polyline distance.
        get_ds : First fitted segment length.

        Notes
        -----
        The result is a sampled-geometry length. Refine ``npts`` when the
        discrete length is used as a convergence diagnostic.

        Examples
        --------
        >>> import numpy as np
        >>> from scirel.geometry import FieldLine
        >>> line = FieldLine(0.2, np.array([[0., 0.], [.5, 0.], [1., 0.]]))
        >>> np.testing.assert_allclose(line.get_length(), 1.0, atol=1e-8)
        """
        return self.get_svec()[-1]

    def get_ds(self):
        """Return the first fitted segment length.

        Returns
        -------
        ds : float
            Euclidean distance between the first two fitted vertices [m].

        Raises
        ------
        IndexError
            If the fitted vertex array contains fewer than two rows.

        See Also
        --------
        get_svec : All cumulative segment distances.
        get_length : Total fitted length.

        Notes
        -----
        This is one sampled segment, not a uniform-step guarantee for the whole
        line. Use :meth:`get_svec` for the actual sample distribution.

        Examples
        --------
        >>> import numpy as np
        >>> from scirel.geometry import FieldLine
        >>> line = FieldLine(0.2, np.array([[0., 0.], [.5, 0.], [1., 0.]]))
        >>> bool(line.get_ds() > 0.0)
        True
        """
        return np.linalg.norm(self.verts[1] - self.verts[0])

    def interpolate_onto(self, R, Z, Q, method="cubic"):
        """Interpolate a field from an R-Z grid onto fitted line vertices.

        Parameters
        ----------
        R, Z : array-like, shape (Nz, Nr)
            Rectangular coordinate grids [m]. Cubically separated rectangular
            grids use SciPy's spline path; other layouts use scattered
            interpolation.
        Q : array-like, shape (Nz, Nr)
            Field samples on the grid [field units].
        method : {'cubic', 'linear', 'nearest'}, default 'cubic'
            Interpolation method [dimensionless]. ``cubic`` uses the
            rectangular spline when the grid is separable, otherwise Clough-
            Tocher interpolation.

        Returns
        -------
        values : ndarray, shape (npts,)
            Field samples on the fitted vertices [field units]. Queries outside
            the interpolation support may contain ``NaN``.

        Raises
        ------
        ValueError, TypeError
            If the grid, field, or method cannot be represented by the selected
            SciPy interpolator. Nonfinite source samples are filtered for this
            FieldLine variant.

        See Also
        --------
        get_kappa_n : Field-direction curvature from interpolated BR and BZ.
        get_gradpsi : Poloidal-flux gradient from interpolated field components.

        Notes
        -----
        The returned array follows the fitted vertex order. A ``NaN`` means the
        interpolation was undefined or the query was unsupported; it is not an
        inferred zero. Convert to a failure in the caller when a finite result
        is required.

        Examples
        --------
        >>> import numpy as np
        >>> from scirel.geometry import FieldLine
        >>> line = FieldLine(0.2, np.array([[0.2, 0.], [.6, 0.], [1., 0.]]))
        >>> r, z = np.meshgrid(np.linspace(0.1, 1.1, 9), np.linspace(-0.2, 0.2, 9))
        >>> np.testing.assert_allclose(line.interpolate_onto(r, z, np.ones_like(r)), 1.0)
        """
        return _sample_fieldline(self.verts, R, Z, Q, method, filter_nonfinite=True)

    def get_kappa_n(self, R, Z, BR, BZ, method="cubic"):
        """Return field-direction curvature along the fitted line.

        Parameters
        ----------
        R, Z : array-like, shape (Nz, Nr)
            Rectangular coordinate grids [m].
        BR, BZ : array-like, shape (Nz, Nr)
            Magnetic-field components on the grid [T].
        method : {'cubic', 'linear', 'nearest'}, default 'cubic'
            Interpolation method [dimensionless].

        Returns
        -------
        curvature : ndarray, shape (npts, 2)
            Curvature vector ``[kappa_R, kappa_Z]`` in the fitted vertex order
            [1/m]. Its sign follows the field orientation.

        Raises
        ------
        ValueError
            If interpolated field values are nonfinite or zero, adjacent
            vertices coincide, or a tangent projection cannot be formed.

        See Also
        --------
        get_kappa_n_2 : Flux-gradient curvature from a scalar flux grid.
        interpolate_onto : Field interpolation on the line.

        Notes
        -----
        This is the derivative of the normalized interpolated field direction
        with respect to fitted arc length. Reversing both field components
        leaves the geometric curvature unchanged.

        Examples
        --------
        >>> import numpy as np
        >>> from scirel.geometry import FieldLine
        >>> line = FieldLine(0.2, np.array([[0.2, 0.], [.6, 0.], [1., 0.]]))
        >>> r, z = np.meshgrid(np.linspace(0.1, 1.1, 9), np.linspace(-0.2, 0.2, 9))
        >>> kappa = line.get_kappa_n(r, z, np.ones_like(r), np.zeros_like(r))
        >>> np.testing.assert_allclose(kappa, 0.0, atol=1e-10)
        """
        return _curve_curvature(
            self.verts,
            self.interpolate_onto(R, Z, BR, method),
            self.interpolate_onto(R, Z, BZ, method),
        )

    def get_kappa_n_2(self, R, Z, psi, method="cubic"):
        """Return curvature of flux surfaces derived from a scalar flux grid.

        Parameters
        ----------
        R, Z : array-like, shape (Nz, Nr)
            Separable, uniformly spaced rectangular coordinate grids [m], with
            at least three points on each axis.
        psi : array-like, shape (Nz, Nr)
            Poloidal-flux samples [caller flux units]. The gradient may not
            vanish anywhere on the grid.
        method : {'cubic', 'linear', 'nearest'}, default 'cubic'
            Interpolation method [dimensionless].

        Returns
        -------
        curvature : ndarray, shape (npts, 2)
            Flux-surface curvature vector in the fitted order [1/m].

        Raises
        ------
        ValueError
            If the inputs are complex, not finite, not matching 2-D arrays, not
            separable and uniform, have fewer than three nodes per axis, or
            produce a zero or nonfinite gradient. Queries outside finite
            interpolation support also raise.

        See Also
        --------
        get_kappa_n : Curvature of the interpolated magnetic-field direction.
        get_gradpsi : Interpolated poloidal-flux gradient components.

        Notes
        -----
        The grid is differentiated with :func:`numpy.gradient`, normalized by
        the gradient magnitude, and then interpolated onto the fitted line.
        This relation assumes a nondegenerate flux gradient and does not infer
        a flux-surface topology beyond the supplied grid.

        Examples
        --------
        >>> import numpy as np
        >>> from scirel.geometry import FieldLine
        >>> line = FieldLine(0.2, np.array([[0.2, 0.], [.6, 0.], [1., 0.]]))
        >>> r, z = np.meshgrid(np.linspace(0.1, 1.1, 9), np.linspace(-0.2, 0.2, 9))
        >>> kappa = line.get_kappa_n_2(r, z, r)
        >>> np.testing.assert_allclose(kappa, 0.0, atol=1e-10)
        """
        if any(np.iscomplexobj(value) for value in (R, Z, psi)):
            raise ValueError("flux curvature requires real grid and flux")
        R, Z, psi = (np.asarray(value, dtype=float) for value in (R, Z, psi))
        if (
            R.ndim != 2
            or min(R.shape) < 3
            or Z.shape != R.shape
            or psi.shape != R.shape
            or not all(np.isfinite(value).all() for value in (R, Z, psi))
        ):
            raise ValueError(
                "finite matching 2-D grid and flux, at least three nodes per axis required"
            )
        if not (
            np.array_equal(R, np.broadcast_to(R[0, :], R.shape))
            and np.array_equal(Z, np.broadcast_to(Z[:, 0, None], Z.shape))
        ):
            raise ValueError("flux curvature requires separable uniform xy grid")
        dx, dz = R[0, 1] - R[0, 0], Z[1, 0] - Z[0, 0]
        tolerance = np.finfo(float).eps
        rtol = 16 * tolerance * max(np.max(np.abs(R)), np.ptp(R))
        ztol = 16 * tolerance * max(np.max(np.abs(Z)), np.ptp(Z))
        if (
            dx == 0.0
            or dz == 0.0
            or not np.allclose(np.diff(R[0]), dx, rtol=0, atol=rtol)
            or not np.allclose(np.diff(Z[:, 0]), dz, rtol=0, atol=ztol)
        ):
            raise ValueError("flux curvature requires nondegenerate uniform xy grid")
        dpsi_dz, dpsi_dr = np.gradient(psi, dz, dx)
        gradient_magnitude = np.hypot(dpsi_dr, dpsi_dz)
        if not np.isfinite(gradient_magnitude).all() or np.any(gradient_magnitude <= 0.0):
            raise ValueError("flux curvature is undefined on zero or nonfinite gradient support")
        z1, r1 = np.gradient(-dpsi_dz / gradient_magnitude, dz, dx)
        z2, r2 = np.gradient(dpsi_dr / gradient_magnitude, dz, dx)
        kappa_r = (dpsi_dr * z1 - dpsi_dz * r1) / gradient_magnitude
        kappa_z = (dpsi_dr * z2 - dpsi_dz * r2) / gradient_magnitude
        interpolated_r = self.interpolate_onto(R, Z, kappa_r, method)
        interpolated_z = self.interpolate_onto(R, Z, kappa_z, method)
        if not np.isfinite(interpolated_r).all() or not np.isfinite(interpolated_z).all():
            raise ValueError("flux curvature queries must be inside finite interpolation support")
        return np.column_stack((interpolated_r, interpolated_z))

    def d_ds(self, Q):
        """Differentiate fitted-vertex values with respect to arclength.

        Parameters
        ----------
        Q : array-like, shape (npts,)
            Values on the fitted vertices [quantity units].

        Returns
        -------
        derivative : ndarray, shape (npts,)
            Arclength derivative at every fitted vertex [quantity/length].

        Raises
        ------
        ValueError
            If ``Q`` has the wrong shape, contains nonfinite values, or the
            fitted vertices contain duplicate adjacent points.

        See Also
        --------
        get_svec : Cumulative polyline distance used by the derivative.
        d_ds_arclength : Underlying unequal-spacing stencil.

        Notes
        -----
        Endpoints use one-sided quadratic stencils; interiors use the shared
        unequal-spacing central stencil. No periodic wrap is applied.

        Examples
        --------
        >>> import numpy as np
        >>> from scirel.geometry import FieldLine
        >>> line = FieldLine(0.2, np.array([[0., 0.], [.5, 0.], [1., 0.]]))
        >>> np.testing.assert_allclose(line.d_ds(line.verts[:, 0]), 1.0, atol=1e-8)
        """
        return d_ds_arclength(self.verts, Q)

    def get_gradpsi(self, R, Z, BR, BZ, method="cubic"):
        """Interpolate the axisymmetric poloidal-flux gradient on the line.

        Parameters
        ----------
        R, Z : array-like, shape (Nz, Nr)
            Rectangular coordinate grids [m].
        BR, BZ : array-like, shape (Nz, Nr)
            Magnetic-field components on the grid [T].
        method : {'cubic', 'linear', 'nearest'}, default 'cubic'
            Interpolation method [dimensionless].

        Returns
        -------
        grad_r, grad_z : ndarray, shape (npts,)
            Interpolated ``R*BZ`` and ``-R*BR`` components [T m], following the
            fitted vertex order.

        Raises
        ------
        ValueError, TypeError, FloatingPointError
            If interpolation fails or the supplied grid, field, or method is
            unsupported. The implementation does not substitute zero for an
            interpolation failure.

        See Also
        --------
        interpolate_onto : Generic field interpolation on the line.
        get_kappa_n_2 : Curvature from a scalar flux grid.

        Notes
        -----
        The two returned arrays are the cylindrical components implied by
        ``(BR, BZ)``; they are not multiplied by a flux normalization chosen by
        this method.

        Examples
        --------
        >>> import numpy as np
        >>> from scirel.geometry import FieldLine
        >>> line = FieldLine(0.2, np.array([[0.2, 0.], [.6, 0.], [1., 0.]]))
        >>> r, z = np.meshgrid(np.linspace(0.1, 1.1, 9), np.linspace(-0.2, 0.2, 9))
        >>> gr, gz = line.get_gradpsi(r, z, 0.3 * np.ones_like(r), 0.8 * np.ones_like(r))
        >>> np.testing.assert_allclose(gr, 0.8 * line.verts[:, 0], atol=1e-7)
        """
        return self.interpolate_onto(R, Z, R * BZ, method), -self.interpolate_onto(
            R, Z, R * BR, method
        )

    def intersection(self, boundary):
        """Find the unique fitted-parameter intersection with a boundary.

        Parameters
        ----------
        boundary : Boundary
            Fitted boundary curve [m]. It must expose ``interpolate`` and its
            fitted parameter interval.

        Returns
        -------
        u_line : float
            Line spline parameter at the intersection [dimensionless].

        Raises
        ------
        ValueError
            If no intersection is found within the fitted intervals, or if more
            than one distinct intersection remains. A finite multistart search
            does not prove global root completeness.

        See Also
        --------
        apply_boundary : Store two boundary intersections.
        get_bounded_fl : Sample between stored intersections.

        Notes
        -----
        Candidate roots are found by bounded least-squares from a finite grid of
        starts. The returned value is the line parameter, not a distance or a
        coordinate.

        Examples
        --------
        >>> import numpy as np
        >>> from scirel.geometry import Boundary, FieldLine
        >>> line = FieldLine(0.2, np.array([[0.2, 0.], [1.5, 0.], [2.8, 0.]]))
        >>> boundary = Boundary(np.column_stack([np.full(7, 1.0), np.linspace(-1., 1., 7)]))
        >>> 0.0 <= line.intersection(boundary) <= 1.0
        True
        """
        return _bounded_intersection(self, boundary)

    def apply_boundary(self, b1, b2):
        """Store the two boundary intersections used to bound the line.

        Parameters
        ----------
        b1, b2 : Boundary
            First and second fitted boundary curves [m].

        Returns
        -------
        None
            The method updates ``ubound0`` and ``ubound1`` in place
            [dimensionless].

        Raises
        ------
        ValueError
            If either boundary has no unique intersection with this line.

        See Also
        --------
        intersection : Find one boundary parameter.
        get_bounded_fl : Sample between the stored parameters.

        Notes
        -----
        Both intersections are computed before either bound is assigned, so a
        failure in the second search leaves the stored interval unchanged.

        Examples
        --------
        >>> import numpy as np
        >>> from scirel.geometry import Boundary, FieldLine
        >>> line = FieldLine(0.2, np.array([[0.2, 0.], [1.5, 0.], [2.8, 0.]]))
        >>> vertical = lambda r: Boundary(np.column_stack([np.full(7, r), np.linspace(-1., 1., 7)]))
        >>> line.apply_boundary(vertical(1.0), vertical(2.0))
        >>> line.ubound1 > line.ubound0
        True
        """
        first, second = self.intersection(b1), self.intersection(b2)
        self.ubound0, self.ubound1 = first, second

    def get_bounded_fl(self, npts=1000):
        """Sample the line between the stored boundary intersections.

        Parameters
        ----------
        npts : int, optional
            Number of equally spaced spline parameters [dimensionless]. The
            default is ``1000``.

        Returns
        -------
        points : sequence of ndarray, length 2
            Bounded ``[R, Z]`` coordinate arrays [m], each of shape ``(npts,)``.

        Raises
        ------
        AttributeError
            If :meth:`apply_boundary` has not assigned ``ubound0`` and
            ``ubound1`` yet.
        ValueError
            If the stored bounds or ``npts`` cannot form a valid sample.

        See Also
        --------
        apply_boundary : Establish the two line parameters.
        interpolate : Evaluate the underlying fitted line.

        Notes
        -----
        The samples are uniform in spline parameter ``u``, not necessarily
        uniform in physical arclength.

        Examples
        --------
        >>> import numpy as np
        >>> from scirel.geometry import FieldLine
        >>> line = FieldLine(0.2, np.array([[0., 0.], [.5, 0.], [1., 0.]]))
        >>> line.ubound0, line.ubound1 = 0.0, 1.0
        >>> vertices = np.asarray(line.get_bounded_fl(11)).T
        >>> vertices.shape
        (11, 2)
        """
        return self.interpolate(np.linspace(self.ubound0, self.ubound1, npts))


def contour_points(contourset):
    """Contour field-line collection contour_points

    Parameters
    ----------
    contourset : contour-like object
        Object exposing levels and allsegs [levels in caller flux-label units; vertices
        length] Shape: ``contour object``. Each allsegs entry contains finite planar
        segments

    Returns
    -------
    collection : Python object
        Per-level lists of target line objects [same as target line] Shape: ``dict[level,
        list[line]]``. Keys and segment lists follow contourset.levels/allsegs; each value
        is a constructed line list.

    Raises
    ------
    ValueError
        Underlying array, spline, or interpolation validation errors propagate;
        the callable adds no input repair or fallback.

    See Also
    --------
    helper_contour_points : Contour field-line collection helper_contour_points.
    FieldLine : FieldLine geometry and diagnostics.
    FieldLineSet : Contour field-line collection FieldLineSet.

    Notes
    -----
    For each contour level, construct one FieldLine per segment in the corresponding allsegs
    entry.

    **Coordinates.** Segment vertices in caller length units; levels in caller flux-label
    units.

    **Boundary.** Each segment must be accepted by the FieldLine spline constructor.

    **Preconditions.**

    * The contour object exposes levels and allsegs.
    * Segment order and level order are preserved.

    **Limits.**

    * Contour topology repair, field reconstruction, and physical flux-surface
      qualification.

    Examples
    --------
    >>> import numpy as np
    >>> from types import SimpleNamespace
    >>> from scirel.geometry.fieldline import contour_points
    >>> c=SimpleNamespace(levels=[.2],allsegs=[[np.array([[.2,0.],[.6,0.],[1.,0.]])]])
    >>> r=contour_points(c)
    >>> assert len(r[.2])==1
    """
    return {
        level: [FieldLine(level, segment) for segment in contourset.allsegs[index]]
        for index, level in enumerate(contourset.levels)
    }


class Boundary:
    """Parametric boundary interpolation

    Parameters
    ----------
    vertices : float64
        Ordered boundary vertices [length units] Shape: ``(N,2)``. Finite ordered points
        sufficient for the default quadratic splprep fit (at least three distinct points).

    Returns
    -------
    boundary : Python object
        Object with verts,tck,u and interpolation [length units] Shape: ``Python object``.
        Stored verts have (200,2); interpolation returns coordinate arrays

    Attributes
    ----------
    verts : ndarray
        Fitted boundary vertices [m], shape ``(200, 2)``.
    u : ndarray
        Spline sampling parameters [dimensionless].
    tck : tuple
        SciPy spline representation [mixed caller units]. Treat it as opaque.

    Raises
    ------
    ValueError
        Underlying array, spline, or interpolation validation errors propagate;
        the callable adds no input repair or fallback.

    See Also
    --------
    FieldLine : FieldLine geometry and diagnostics.
    HelperFieldLine : HelperFieldLine geometry and diagnostics.
    interpolate : Evaluate the fitted boundary at spline parameters.
    apply_boundary : Related geometry callable.

    Notes
    -----
    Fit a SciPy parametric spline with s=0 and sample it at 200 parameters.

    **Coordinates.** Vertex coordinates in caller length units.

    **Boundary.** No periodic closure or intersection uniqueness is inferred.

    **Preconditions.**

    * The input is finite and contains enough distinct points for splprep.
    * Stored samples are 200 fitted points.

    **Limits.**

    * Polygon interior tests, crossing selection, and uniqueness guarantees.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.geometry.fieldline import Boundary
    >>> b=Boundary(np.array([[0.,0.],[.3,.3],[.7,.7],[1.,1.]]))
    >>> assert b.verts.shape==(200,2)
    """

    def __init__(self, vertices):
        self._interpolate_verts(vertices)

    def _interpolate_verts(self, vertices, u=None, s=0.0, npts=200):
        self.tck, self.u, self.verts = _fit_parametric_curve(
            vertices, u=u, s=s, npts=npts, periodic=False
        )

    def interpolate(self, u):
        """Evaluate the fitted boundary at spline parameters ``u``.

        Parameters
        ----------
        u : real array-like
            Spline parameters in the fitted boundary interval
            [dimensionless].

        Returns
        -------
        points : sequence of ndarray
            ``[R, Z]`` boundary coordinate arrays [m]. A scalar parameter gives
            two scalars; an array of shape ``S`` gives two arrays of shape
            ``S``.

        Raises
        ------
        ValueError
            If SciPy rejects the parameter array or the fitted spline
            representation is invalid.

        See Also
        --------
        FieldLine.intersection : Use this boundary in an intersection search.

        Notes
        -----
        The boundary uses a nonperiodic quadratic spline fit. Parameter values
        are independent of arclength and no closure is inferred.

        Examples
        --------
        >>> import numpy as np
        >>> from scirel.geometry import Boundary
        >>> boundary = Boundary(np.column_stack([np.linspace(0., 1., 6), np.linspace(0., 1., 6)]))
        >>> np.testing.assert_allclose(boundary.interpolate([0., 1.]), [[0., 1.], [0., 1.]], atol=1e-8)
        """
        from scipy.interpolate import splev

        return splev(u, self.tck, der=0)


class HelperFieldLine:
    """HelperFieldLine geometry and diagnostics

    Parameters
    ----------
    psi : float64
        Contour level label [caller flux-label units] Shape: ``scalar``. Not a reconstructed
        flux field

    verts : float64
        Contour vertices [length units] Shape: ``(M,2)``. Finite ordered points sufficient
        for the default quadratic splprep fit; adjacent fitted samples must remain distinct.

    Returns
    -------
    line : Python object
        Object exposing verts,tck,u and arclength/field diagnostics [length; gradient caller
        flux per length; curvature inverse length] Shape: ``line object``. get_ds returns
        first segment length, not a uniform-step guarantee

    Attributes
    ----------
    psi : scalar
        Caller-supplied contour label [caller flux-label units].
    verts : ndarray
        Fitted planar vertices [m], shape ``(1000, 2)`` in fitted-parameter
        order.
    u : ndarray
        Sampling parameters of the fitted spline [dimensionless].
    tck : tuple
        SciPy spline representation [mixed caller units]. Treat it as opaque.
    ubound0, ubound1 : float, optional
        Intersection parameters created by ``apply_boundary`` [dimensionless].

    Raises
    ------
    ValueError
        ValueError is raised for undefined curvature support, duplicate vertices, or nonfinite tangent/field values; Intersection raises ValueError when no unique fitted-interval crossing is found;

    See Also
    --------
    FieldLine : FieldLine geometry and diagnostics.
    Boundary : Parametric boundary interpolation.
    helper_contour_points : Contour field-line collection helper_contour_points.

    Notes
    -----
    Fit an ordered parametric line; helper interpolation preserves nonfinite query behavior
    while field curvature differentiates normalized BR,BZ along fitted geometry.

    **Coordinates.** Planar R,Z in caller length units; psi is a contour label.

    **Boundary.** Intersections search only fitted parameter intervals and reject zero or
    multiple crossings.

    **Preconditions.**

    * Finite vertices are sufficient for splprep and adjacent fitted samples remain
      distinct.
    * Field curvature needs finite nonzero B and nonzero tangent projection.

    **Limits.**

    * Flux-gradient curvature, arbitrary contour topology, magnetic-axis limits, and
      universal error bounds.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.geometry.fieldline import HelperFieldLine
    >>> line=HelperFieldLine(.2,np.array([[.2,0.],[.6,0.],[1.,0.]]))
    >>> assert line.verts.shape==(1000,2)
    """

    def __init__(self, psi, verts):
        self.psi = psi
        self._verts = verts
        self._interpolate_verts()

    def is_closed(self):
        """Return whether the original helper contour closes exactly.

        Returns
        -------
        is_closed : bool
            ``True`` when the first and last input vertices are exactly equal
            [dimensionless].

        Raises
        ------
        No exception is raised for a successfully constructed helper line.

        See Also
        --------
        get_bounded_fl : Sample between two boundary intersections.

        Notes
        -----
        Closure is tested on the stored input vertices before spline fitting;
        no distance tolerance or endpoint repair is applied.

        Examples
        --------
        >>> import numpy as np
        >>> from scirel.geometry import HelperFieldLine
        >>> bool(HelperFieldLine(0.2, np.array([[0., 0.], [.5, 0.], [1., 0.]])).is_closed())
        False
        """
        return np.all(self._verts[0, :] == self._verts[-1, :])

    def _interpolate_verts(self, u=None, s=0.0, k=2, npts=1000):
        self.tck, self.u, self.verts = _fit_parametric_curve(
            self._verts, u=u, s=s, k=k, npts=npts, periodic=self.is_closed()
        )

    def interpolate(self, u):
        """Evaluate the fitted helper line at spline parameters ``u``.

        Parameters
        ----------
        u : real array-like
            Spline parameters in the fitted interval [dimensionless]. Scalars
            and arrays are accepted; no additional domain check is applied.

        Returns
        -------
        points : sequence of ndarray
            ``[R, Z]`` coordinate arrays [m], one array per planar axis. A
            scalar parameter gives two scalars; an array of shape ``S`` gives
            two arrays of shape ``S``.

        Raises
        ------
        ValueError
            If SciPy rejects the parameter array or the stored spline is invalid.

        See Also
        --------
        get_svec : Cumulative fitted polyline distance.
        get_bounded_fl : Sample between boundary intersections.

        Notes
        -----
        The parameter is not arclength. SciPy's spline evaluation controls
        extrapolation behavior; this method adds no clamp.

        Examples
        --------
        >>> import numpy as np
        >>> from scirel.geometry import HelperFieldLine
        >>> line = HelperFieldLine(0.2, np.array([[0., 0.], [.5, 0.], [1., 0.]]))
        >>> np.testing.assert_allclose(line.interpolate([0., 1.]), [[0., 1.], [0., 0.]], atol=1e-8)
        """
        from scipy.interpolate import splev

        return splev(u, self.tck, der=0)

    def get_svec(self):
        """Return cumulative fitted-polyline distance.

        Returns
        -------
        svec : ndarray of float64, shape (npts,)
            Cumulative Euclidean distance from the first fitted vertex [m].
            The first entry is zero and entries are nondecreasing.

        Raises
        ------
        No exception is raised for a successfully constructed helper line.

        See Also
        --------
        get_length : Total fitted-polyline length.
        d_ds : Derivative with respect to fitted arclength.

        Notes
        -----
        The result is a discrete sum over fitted vertices and depends on the
        configured ``npts``.

        Examples
        --------
        >>> import numpy as np
        >>> from scirel.geometry import HelperFieldLine
        >>> line = HelperFieldLine(0.2, np.array([[0., 0.], [.5, 0.], [1., 0.]]))
        >>> np.testing.assert_allclose(line.get_svec()[0], 0.0)
        """
        distance = np.zeros(self.verts.shape[0])
        distance[1:] = np.cumsum(np.linalg.norm(np.diff(self.verts, axis=0), axis=1))
        return distance

    def get_length(self):
        """Return total fitted-polyline length.

        Returns
        -------
        length : float
            Last entry of :meth:`get_svec` [m].

        Raises
        ------
        No exception is raised for a successfully constructed helper line.

        See Also
        --------
        get_svec : Cumulative fitted-polyline distance.
        get_ds : First fitted segment length.

        Notes
        -----
        This is a sampled-geometry length rather than an analytic spline
        integral.

        Examples
        --------
        >>> import numpy as np
        >>> from scirel.geometry import HelperFieldLine
        >>> line = HelperFieldLine(0.2, np.array([[0., 0.], [.5, 0.], [1., 0.]]))
        >>> np.testing.assert_allclose(line.get_length(), 1.0, atol=1e-8)
        """
        return self.get_svec()[-1]

    def get_ds(self):
        """Return the first fitted segment length.

        Returns
        -------
        ds : float
            Euclidean distance between the first two fitted vertices [m].

        Raises
        ------
        IndexError
            If the fitted vertex array contains fewer than two rows.

        See Also
        --------
        get_svec : All cumulative segment distances.
        get_length : Total fitted length.

        Notes
        -----
        One segment is not a uniform-step guarantee; inspect ``get_svec`` for
        the sample distribution.

        Examples
        --------
        >>> import numpy as np
        >>> from scirel.geometry import HelperFieldLine
        >>> line = HelperFieldLine(0.2, np.array([[0., 0.], [.5, 0.], [1., 0.]]))
        >>> bool(line.get_ds() > 0.0)
        True
        """
        return np.linalg.norm(self.verts[1] - self.verts[0])

    def interpolate_onto(self, R, Z, Q, method="cubic"):
        """Interpolate a field from an R-Z grid onto helper-line vertices.

        Parameters
        ----------
        R, Z : array-like, shape (Nz, Nr)
            Rectangular coordinate grids [m].
        Q : array-like, shape (Nz, Nr)
            Field samples on the grid [field units].
        method : {'cubic', 'linear', 'nearest'}, default 'cubic'
            Interpolation method [dimensionless].

        Returns
        -------
        values : ndarray, shape (npts,)
            Field samples on the fitted vertices [field units]. Nonfinite source
            samples and unsupported queries may produce ``NaN``.

        Raises
        ------
        ValueError, TypeError
            If the grid, field, or method cannot be represented by the selected
            SciPy interpolator.

        See Also
        --------
        get_kappa_n : Helper field-direction curvature.
        get_gradpsi : Helper poloidal-flux gradient.

        Notes
        -----
        The helper variant preserves the compatibility behavior of passing all
        source samples to SciPy; it does not filter nonfinite source values.
        A returned ``NaN`` is not replaced by zero.

        Examples
        --------
        >>> import numpy as np
        >>> from scirel.geometry import HelperFieldLine
        >>> line = HelperFieldLine(0.2, np.array([[0.2, 0.], [.6, 0.], [1., 0.]]))
        >>> r, z = np.meshgrid(np.linspace(0.1, 1.1, 9), np.linspace(-0.2, 0.2, 9))
        >>> np.testing.assert_allclose(line.interpolate_onto(r, z, np.ones_like(r)), 1.0)
        """
        return _sample_fieldline(self.verts, R, Z, Q, method, filter_nonfinite=False)

    def get_kappa_n(self, R, Z, BR, BZ, method="cubic"):
        """Return helper field-direction curvature components.

        Parameters
        ----------
        R, Z : array-like, shape (Nz, Nr)
            Rectangular coordinate grids [m].
        BR, BZ : array-like, shape (Nz, Nr)
            Magnetic-field components on the grid [T].
        method : {'cubic', 'linear', 'nearest'}, default 'cubic'
            Interpolation method [dimensionless].

        Returns
        -------
        kappa_r, kappa_z : ndarray, shape (npts,)
            Curvature components in the fitted vertex order [1/m].

        Raises
        ------
        ValueError
            If interpolated field values are nonfinite or zero, adjacent
            vertices coincide, or a tangent projection cannot be formed.

        See Also
        --------
        interpolate_onto : Field interpolation on the helper line.
        FieldLine.get_kappa_n : Array-valued field-line variant.

        Notes
        -----
        The helper returns the two components separately; the geometric
        curvature is the derivative of normalized field direction with respect
        to fitted arclength.

        Examples
        --------
        >>> import numpy as np
        >>> from scirel.geometry import HelperFieldLine
        >>> line = HelperFieldLine(0.2, np.array([[0.2, 0.], [.6, 0.], [1., 0.]]))
        >>> r, z = np.meshgrid(np.linspace(0.1, 1.1, 9), np.linspace(-0.2, 0.2, 9))
        >>> kr, kz = line.get_kappa_n(r, z, np.ones_like(r), np.zeros_like(r))
        >>> np.testing.assert_allclose(kr, 0.0, atol=1e-10)
        >>> np.testing.assert_allclose(kz, 0.0, atol=1e-10)
        """
        curvature = _curve_curvature(
            self.verts,
            self.interpolate_onto(R, Z, BR, method),
            self.interpolate_onto(R, Z, BZ, method),
        )
        return curvature[:, 0], curvature[:, 1]

    def d_ds(self, Q):
        """Differentiate helper-line values with respect to arclength.

        Parameters
        ----------
        Q : array-like, shape (npts,)
            Values on the fitted vertices [quantity units].

        Returns
        -------
        derivative : ndarray, shape (npts,)
            Arclength derivative at every fitted vertex [quantity/length].

        Raises
        ------
        ValueError
            If ``Q`` has the wrong shape, contains nonfinite values, or adjacent
            fitted vertices coincide.

        See Also
        --------
        get_svec : Cumulative fitted-polyline distance.
        d_ds_arclength : Underlying unequal-spacing stencil.

        Notes
        -----
        Endpoints use one-sided quadratic stencils; interiors use unequal-
        spacing central differences. No periodic wrap is applied.

        Examples
        --------
        >>> import numpy as np
        >>> from scirel.geometry import HelperFieldLine
        >>> line = HelperFieldLine(0.2, np.array([[0., 0.], [.5, 0.], [1., 0.]]))
        >>> np.testing.assert_allclose(line.d_ds(line.verts[:, 0]), 1.0, atol=1e-8)
        """
        return d_ds_arclength(self.verts, Q)

    def get_gradpsi(self, R, Z, BR, BZ, method="cubic"):
        """Interpolate the axisymmetric poloidal-flux gradient for a helper line.

        Parameters
        ----------
        R, Z : array-like, shape (Nz, Nr)
            Rectangular coordinate grids [m].
        BR, BZ : array-like, shape (Nz, Nr)
            Magnetic-field components on the grid [T].
        method : {'cubic', 'linear', 'nearest'}, default 'cubic'
            Interpolation method [dimensionless].

        Returns
        -------
        grad_r, grad_z : ndarray, shape (npts,)
            Interpolated ``R*BZ`` and ``-R*BR`` components [T m].

        Raises
        ------
        ValueError, TypeError
            If interpolation fails or the grid, field, or method is unsupported.

        See Also
        --------
        interpolate_onto : Generic helper-line interpolation.
        FieldLine.get_gradpsi : Array-valued field-line variant.

        Notes
        -----
        The helper preserves the historical component formula and returns the
        same convention as the primary field-line class.

        Examples
        --------
        >>> import numpy as np
        >>> from scirel.geometry import HelperFieldLine
        >>> line = HelperFieldLine(0.2, np.array([[0.2, 0.], [.6, 0.], [1., 0.]]))
        >>> r, z = np.meshgrid(np.linspace(0.1, 1.1, 9), np.linspace(-0.2, 0.2, 9))
        >>> gr, gz = line.get_gradpsi(r, z, 0.3 * np.ones_like(r), 0.8 * np.ones_like(r))
        >>> np.testing.assert_allclose(gr, 0.8 * line.verts[:, 0], atol=1e-7)
        """
        return self.interpolate_onto(R, Z, R * BZ, method), -self.interpolate_onto(
            R, Z, R * BR, method
        )

    def intersection(self, boundary):
        """Find the unique helper-line intersection with a boundary.

        Parameters
        ----------
        boundary : Boundary
            Fitted boundary curve [m].

        Returns
        -------
        u_line : float
            Helper-line spline parameter at the intersection [dimensionless].

        Raises
        ------
        ValueError
            If no intersection is found, or if more than one distinct
            intersection remains.

        See Also
        --------
        apply_boundary : Store two boundary intersections.
        get_bounded_fl : Sample between stored intersections.

        Notes
        -----
        Candidate roots use the same bounded multistart search as FieldLine;
        the finite search does not prove global root completeness.

        Examples
        --------
        >>> import numpy as np
        >>> from scirel.geometry import Boundary, HelperFieldLine
        >>> line = HelperFieldLine(0.2, np.array([[0.2, 0.], [1.5, 0.], [2.8, 0.]]))
        >>> boundary = Boundary(np.column_stack([np.full(7, 1.0), np.linspace(-1., 1., 7)]))
        >>> 0.0 <= line.intersection(boundary) <= 1.0
        True
        """
        return _bounded_intersection(self, boundary)

    def apply_boundary(self, b1, b2):
        """Store the two boundary intersections used by a helper line.

        Parameters
        ----------
        b1, b2 : Boundary
            First and second fitted boundary curves [m].

        Returns
        -------
        None
            ``ubound0`` and ``ubound1`` are assigned in place [dimensionless].

        Raises
        ------
        ValueError
            If either boundary has no unique intersection with this helper
            line.

        See Also
        --------
        intersection : Find one boundary parameter.
        get_bounded_fl : Sample between stored parameters.

        Notes
        -----
        Both intersections are computed before either bound is updated, so a
        failed second search leaves the previous interval unchanged.

        Examples
        --------
        >>> import numpy as np
        >>> from scirel.geometry import Boundary, HelperFieldLine
        >>> line = HelperFieldLine(0.2, np.array([[0.2, 0.], [1.5, 0.], [2.8, 0.]]))
        >>> vertical = lambda r: Boundary(np.column_stack([np.full(7, r), np.linspace(-1., 1., 7)]))
        >>> line.apply_boundary(vertical(1.0), vertical(2.0))
        >>> line.ubound1 > line.ubound0
        True
        """
        first, second = self.intersection(b1), self.intersection(b2)
        self.ubound0, self.ubound1 = first, second

    def get_bounded_fl(self, npts=1000):
        """Sample a helper line between its stored boundary intersections.

        Parameters
        ----------
        npts : int, optional
            Number of equally spaced spline parameters [dimensionless]. The
            default is ``1000``.

        Returns
        -------
        points : sequence of ndarray, length 2
            Bounded ``[R, Z]`` coordinate arrays [m], each of shape ``(npts,)``.

        Raises
        ------
        AttributeError
            If :meth:`apply_boundary` has not assigned ``ubound0`` and
            ``ubound1``.
        ValueError
            If the stored bounds or ``npts`` cannot form a valid sample.

        See Also
        --------
        apply_boundary : Establish the two line parameters.
        interpolate : Evaluate the fitted helper line.

        Notes
        -----
        Samples are uniform in spline parameter, not necessarily in physical
        arclength.

        Examples
        --------
        >>> import numpy as np
        >>> from scirel.geometry import HelperFieldLine
        >>> line = HelperFieldLine(0.2, np.array([[0., 0.], [.5, 0.], [1., 0.]]))
        >>> line.ubound0, line.ubound1 = 0.0, 1.0
        >>> np.asarray(line.get_bounded_fl(11)).T.shape
        (11, 2)
        """
        return self.interpolate(np.linspace(self.ubound0, self.ubound1, npts))


def helper_contour_points(contourset):
    """Contour field-line collection helper_contour_points

    Parameters
    ----------
    contourset : contour-like object
        Object exposing levels and allsegs [levels in caller flux-label units; vertices
        length] Shape: ``contour object``. Each allsegs entry contains finite planar
        segments

    Returns
    -------
    collection : Python object
        Per-level lists of target line objects [same as target line] Shape: ``dict[level,
        list[line]]``. Keys and segment lists follow contourset.levels/allsegs; each value
        is a constructed line list.

    Raises
    ------
    ValueError
        Underlying array, spline, or interpolation validation errors propagate;
        the callable adds no input repair or fallback.

    See Also
    --------
    contour_points : Contour field-line collection contour_points.
    HelperFieldLine : HelperFieldLine geometry and diagnostics.
    FieldLineSet : Contour field-line collection FieldLineSet.

    Notes
    -----
    For each contour level, construct one HelperFieldLine per segment in allsegs.

    **Coordinates.** Segment vertices in caller length units; levels in caller flux-label
    units.

    **Boundary.** Each segment must be accepted by the HelperFieldLine spline constructor.

    **Preconditions.**

    * The contour object exposes levels and allsegs.
    * Segment and level order is preserved.

    **Limits.**

    * Contour topology repair, flux reconstruction, and physical field-line qualification.

    Examples
    --------
    >>> import numpy as np
    >>> from types import SimpleNamespace
    >>> from scirel.geometry.fieldline import helper_contour_points
    >>> c=SimpleNamespace(levels=[.2],allsegs=[[np.array([[.2,0.],[.6,0.],[1.,0.]])]])
    >>> r=helper_contour_points(c)
    >>> assert len(r[.2])==1
    """
    return {
        level: [HelperFieldLine(level, segment) for segment in contourset.allsegs[index]]
        for index, level in enumerate(contourset.levels)
    }
