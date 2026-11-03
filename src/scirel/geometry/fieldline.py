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
    """Differentiate values with respect to cumulative polyline arclength."""
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
            # including a zero value at a node.
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
    """Map contour levels to fitted :class:`FieldLine` instances.

    Parameters
    ----------
    contourset : object
        Object exposing ``levels`` and matching ``allsegs`` sequences.
    **kwargs
        Spline options forwarded to each line.

    Attributes
    ----------
    flset : dict
        Contour level to list of fitted lines.

    Raises
    ------
    Exception
        Construction errors from a member line or contour object.
    """

    def __init__(self, contourset, **kwargs):
        self.flset = {
            level: [FieldLine(level, segment, **kwargs) for segment in contourset.allsegs[index]]
            for index, level in enumerate(contourset.levels)
        }


class FieldLine:
    """Fitted contour with field interpolation, curvature, and diagnostics.

    Parameters
    ----------
    psi : scalar
        Contour level label.
    verts : array_like, shape (N, 2)
        Ordered planar contour vertices.
    **kwargs
        Spline parameters accepted by the interpolation helper.

    Attributes
    ----------
    verts, u, tck
        Fitted samples, sample parameters, and spline representation.

    Raises
    ------
    ValueError
        Invalid diagnostic support, duplicate vertices, or rejected crossings.
    Exception
        Underlying SciPy spline and interpolation failures.
    """

    def __init__(self, psi, verts, **kwargs):
        self.psi = psi
        self._verts = verts
        self._interpolate_verts(**kwargs)
        self.reorder_verts()

    def is_closed(self):
        return np.all(self._verts[0, :] == self._verts[-1, :])

    def _interpolate_verts(self, u=None, s=0.0, k=2, npts=1000):
        self.tck, self.u, self.verts = _fit_parametric_curve(
            self._verts, u=u, s=s, k=k, npts=npts, periodic=self.is_closed()
        )

    def interpolate(self, u):
        from scipy.interpolate import splev

        return splev(u, self.tck, der=0)

    def reorder_verts(self, steptol=0.1):
        return None

    def get_svec(self):
        distance = np.zeros(self.verts.shape[0])
        distance[1:] = np.cumsum(np.linalg.norm(np.diff(self.verts, axis=0), axis=1))
        return distance

    def get_length(self):
        return self.get_svec()[-1]

    def get_ds(self):
        return np.linalg.norm(self.verts[1] - self.verts[0])

    def interpolate_onto(self, R, Z, Q, method="cubic"):
        return _sample_fieldline(self.verts, R, Z, Q, method, filter_nonfinite=True)

    def get_kappa_n(self, R, Z, BR, BZ, method="cubic"):
        return _curve_curvature(
            self.verts,
            self.interpolate_onto(R, Z, BR, method),
            self.interpolate_onto(R, Z, BZ, method),
        )

    def get_kappa_n_2(self, R, Z, psi, method="cubic"):
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
        return d_ds_arclength(self.verts, Q)

    def get_gradpsi(self, R, Z, BR, BZ, method="cubic"):
        return self.interpolate_onto(R, Z, R * BZ, method), -self.interpolate_onto(
            R, Z, R * BR, method
        )

    def intersection(self, boundary):
        return _bounded_intersection(self, boundary)

    def apply_boundary(self, b1, b2):
        first, second = self.intersection(b1), self.intersection(b2)
        self.ubound0, self.ubound1 = first, second

    def get_bounded_fl(self, npts=1000):
        return self.interpolate(np.linspace(self.ubound0, self.ubound1, npts))


def contour_points(contourset):
    """Build a :class:`FieldLine` list for each contour level.

    Parameters
    ----------
    contourset : object
        Object exposing ``levels`` and matching ``allsegs`` sequences.

    Returns
    -------
    dict
        Mapping from contour levels to fitted lines.

    Raises
    ------
    Exception
        Construction errors from the spline fit.
    """
    return {
        level: [FieldLine(level, segment) for segment in contourset.allsegs[index]]
        for index, level in enumerate(contourset.levels)
    }


class Boundary:
    """Fitted nonperiodic spline used as a crossing boundary.

    Parameters
    ----------
    vertices : array_like, shape (N, 2)
        Ordered boundary vertices.

    Attributes
    ----------
    verts, u, tck
        Fitted samples, parameters, and spline representation used by
        :meth:`interpolate`.

    Raises
    ------
    Exception
        Errors from the SciPy spline fit.
    """

    def __init__(self, vertices):
        self._interpolate_verts(vertices)

    def _interpolate_verts(self, vertices, u=None, s=0.0, npts=200):
        self.tck, self.u, self.verts = _fit_parametric_curve(
            vertices, u=u, s=s, npts=npts, periodic=False
        )

    def interpolate(self, u):
        from scipy.interpolate import splev

        return splev(u, self.tck, der=0)


class HelperFieldLine:
    """Field-line helper retaining the historical tuple curvature diagnostics.

    Parameters
    ----------
    psi : scalar
        Contour level label.
    verts : array_like, shape (N, 2)
        Ordered planar contour vertices.

    Attributes
    ----------
    verts, u, tck
        Fitted samples, parameters, and spline representation.

    Raises
    ------
    ValueError
        Invalid diagnostic support, duplicate vertices, or rejected crossings.
    Exception
        Underlying SciPy spline and interpolation failures.
    """

    def __init__(self, psi, verts):
        self.psi = psi
        self._verts = verts
        self._interpolate_verts()
        self.reorder_verts()

    def is_closed(self):
        return np.all(self._verts[0, :] == self._verts[-1, :])

    def _interpolate_verts(self, u=None, s=0.0, k=2, npts=1000):
        self.tck, self.u, self.verts = _fit_parametric_curve(
            self._verts, u=u, s=s, k=k, npts=npts, periodic=self.is_closed()
        )

    def interpolate(self, u):
        from scipy.interpolate import splev

        return splev(u, self.tck, der=0)

    def reorder_verts(self, steptol=0.1):
        return None

    def get_svec(self):
        distance = np.zeros(self.verts.shape[0])
        distance[1:] = np.cumsum(np.linalg.norm(np.diff(self.verts, axis=0), axis=1))
        return distance

    def get_length(self):
        return self.get_svec()[-1]

    def get_ds(self):
        return np.linalg.norm(self.verts[1] - self.verts[0])

    def interpolate_onto(self, R, Z, Q, method="cubic"):
        return _sample_fieldline(self.verts, R, Z, Q, method, filter_nonfinite=False)

    def get_kappa_n(self, R, Z, BR, BZ, method="cubic"):
        curvature = _curve_curvature(
            self.verts,
            self.interpolate_onto(R, Z, BR, method),
            self.interpolate_onto(R, Z, BZ, method),
        )
        return curvature[:, 0], curvature[:, 1]

    def d_ds(self, Q):
        return d_ds_arclength(self.verts, Q)

    def get_gradpsi(self, R, Z, BR, BZ, method="cubic"):
        return self.interpolate_onto(R, Z, R * BZ, method), -self.interpolate_onto(
            R, Z, R * BR, method
        )

    def intersection(self, boundary):
        return _bounded_intersection(self, boundary)

    def apply_boundary(self, b1, b2):
        first, second = self.intersection(b1), self.intersection(b2)
        self.ubound0, self.ubound1 = first, second

    def get_bounded_fl(self, npts=1000):
        return self.interpolate(np.linspace(self.ubound0, self.ubound1, npts))


def helper_contour_points(contourset):
    """Build a :class:`HelperFieldLine` list for each contour level.

    Parameters
    ----------
    contourset : object
        Object exposing ``levels`` and matching ``allsegs`` sequences.

    Returns
    -------
    dict
        Mapping from contour levels to ``HelperFieldLine`` objects.

    Raises
    ------
    Exception
        Construction errors from the spline fit.
    """
    return {
        level: [HelperFieldLine(level, segment) for segment in contourset.allsegs[index]]
        for index, level in enumerate(contourset.levels)
    }
