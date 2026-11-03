"""Inverse-field line measures and flux-surface averages."""

from __future__ import annotations

import numpy as np

__all__ = ["compute_flux_surface_inverse_field_average"]


def compute_flux_surface_inverse_field_average(
    r_grid, z_grid, magnetic_field, field_line_points, quantity=None
):
    """Compute ``integral(ds/B)`` and optionally ``integral(Q ds/B) / integral(ds/B)``.

    Parameters
    ----------
    r_grid : real array-like, shape [N_Z,N_R]
        Rectilinear cylindrical radius coordinate grid [m]. Finite, strictly
        increasing across columns and rectilinear within NumPy allclose
        tolerance; N_R and N_Z each at least four. Nonnegative radius is a
        physical caller precondition, not an implementation check.
    z_grid : real array-like, shape [N_Z,N_R]
        Rectilinear axial coordinate grid [m]. Finite, strictly increasing down
        rows and constant across columns; same shape as r_grid.
    magnetic_field : real array-like, shape [N_Z,N_R]
        Magnetic-field magnitude sampled on the R-Z grid [T]. Finite and
        strictly positive at grid nodes; same shape as r_grid; interpolated path
        values must also remain positive and finite.
    field_line_points : real array-like, shape [N_point,2]
        Ordered path coordinates [R_m,Z_m] for the discrete integral [m,m]. At
        least two finite points within the grid rectangle; no repeated
        consecutive points.
    quantity : real array-like or None, shape [N_Z,N_R] or null, default None
        Optional scalar field to average using the dl/B path weight
        [caller-defined scalar unit]. None omits flux_surface_average; otherwise
        finite and exactly the grid shape.

    Returns
    -------
    dl_B : float
        Trapezoidal integral of 1/B over cumulative polyline length [m/T].
        Finite and strictly positive on successful return.
    flux_surface_average : float or None, shape scalar or null, default None
        Trapezoidal integral of quantity/B divided by dl_B, present only when
        quantity is supplied [same as quantity]. Absent from the result mapping
        when quantity is None; otherwise finite.

    Raises
    ------
    ValueError
        Raises ValueError for wrong shapes, nonfinite values,
        nonrectilinear/undersized grid, nonpositive grid or interpolated B,
        out-of-grid or repeated path points, or nonpositive/nonfinite dl_B.
        SciPy interpolation and quadrature errors propagate; a nonfinite
        interpolated quantity or weighted mean raises ValueError.

    See Also
    --------
    scirel.geometry.flux_surface_avg : Overlapping dl/|B| weighted line integral.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.geometry.flux_surface_inverse_field_average import compute_flux_surface_inverse_field_average
    >>> r_grid, z_grid = np.meshgrid(np.linspace(0.0, 1.0, 5), np.linspace(-1.0, 1.0, 5))
    >>> line = np.array([[0.2, -0.5], [0.4, 0.0], [0.6, 0.5]])
    >>> result = compute_flux_surface_inverse_field_average(r_grid, z_grid, np.full_like(r_grid, 2.0), line, np.full_like(r_grid, 3.0))
    >>> length = np.linalg.norm(np.diff(line, axis=0), axis=1).sum()
    >>> np.testing.assert_allclose(result['dl_B'], length / 2.0)
    >>> np.testing.assert_allclose(result['flux_surface_average'], 3.0)
    """
    r_grid = np.asarray(r_grid, dtype=float)
    z_grid = np.asarray(z_grid, dtype=float)
    magnetic_field = np.asarray(magnetic_field, dtype=float)
    line = np.asarray(field_line_points, dtype=float)
    if r_grid.ndim != 2 or z_grid.shape != r_grid.shape:
        raise ValueError("r_grid and z_grid must be equal-shape 2-D grids")
    if magnetic_field.shape != r_grid.shape:
        raise ValueError("magnetic_field must match the R-Z grid")
    if line.ndim != 2 or line.shape[1] != 2:
        raise ValueError("field_line_points must have shape (n_points, 2)")
    if line.shape[0] < 2:
        raise ValueError("field_line_points needs at least two points")
    if quantity is not None:
        quantity = np.asarray(quantity, dtype=float)
        if quantity.shape != r_grid.shape:
            raise ValueError("quantity must match the R-Z grid")
    for name, array in (
        ("r_grid", r_grid),
        ("z_grid", z_grid),
        ("magnetic_field", magnetic_field),
        ("field_line_points", line),
    ):
        if not np.isfinite(array).all():
            raise ValueError(f"{name} must contain only finite values")
    if quantity is not None and not np.isfinite(quantity).all():
        raise ValueError("quantity must contain only finite values")

    r_axis, z_axis = r_grid[0], z_grid[:, 0]
    if (
        np.any(np.diff(r_axis) <= 0.0)
        or np.any(np.diff(z_axis) <= 0.0)
        or not np.allclose(r_grid, r_axis[None, :])
        or not np.allclose(z_grid, z_axis[:, None])
    ):
        raise ValueError("r_grid and z_grid must be strictly increasing rectilinear grids")
    if min(r_axis.size, z_axis.size) < 4:
        raise ValueError(
            "r_grid and z_grid need at least four points per axis for cubic interpolation"
        )
    if np.any(magnetic_field <= 0.0):
        raise ValueError("magnetic_field must be strictly positive")
    if (
        np.any(line[:, 0] < r_axis[0])
        or np.any(line[:, 0] > r_axis[-1])
        or np.any(line[:, 1] < z_axis[0])
        or np.any(line[:, 1] > z_axis[-1])
    ):
        raise ValueError("field_line_points must lie inside the R-Z grid")
    lengths = np.linalg.norm(np.diff(line, axis=0), axis=1)
    if np.any(lengths <= 0.0):
        raise ValueError(
            "field_line_points must define a nondegenerate polyline without repeated consecutive points"
        )

    from scipy.integrate import trapezoid
    from scipy.interpolate import RectBivariateSpline

    magnetic_values = np.asarray(
        RectBivariateSpline(z_axis, r_axis, magnetic_field)(line[:, 1], line[:, 0], grid=False),
        dtype=float,
    )
    if not np.isfinite(magnetic_values).all() or np.any(magnetic_values <= 0.0):
        raise ValueError("interpolated magnetic field must be finite and strictly positive")
    distance = np.r_[0.0, np.cumsum(lengths)]
    denominator = float(trapezoid(1.0 / magnetic_values, x=distance))
    if not np.isfinite(denominator) or denominator <= 0.0:
        raise ValueError("dl_B must be finite and strictly positive")
    result = {"dl_B": denominator}
    if quantity is not None:
        q_values = np.asarray(
            RectBivariateSpline(z_axis, r_axis, quantity)(line[:, 1], line[:, 0], grid=False),
            dtype=float,
        )
        if not np.isfinite(q_values).all():
            raise ValueError("interpolated quantity must be finite")
        average = float(trapezoid(q_values / magnetic_values, x=distance) / denominator)
        if not np.isfinite(average):
            raise ValueError("flux_surface_average must be finite")
        result["flux_surface_average"] = average
    return result
