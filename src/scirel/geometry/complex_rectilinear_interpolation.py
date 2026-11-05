"""Complex trilinear interpolation on a strict rectilinear source grid."""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np

__all__ = ["interpolate_complex_rectilinear_field"]
_AXIS_KEYS = ("x_m", "y_m", "z_m")


def _source_axes(source_axes_m):
    if not isinstance(source_axes_m, Mapping):
        raise ValueError("source_axes_m must be a mapping of x_m, y_m, and z_m axes")
    result = []
    for name in _AXIS_KEYS:
        try:
            axis = np.asarray(source_axes_m[name], dtype=float)
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"source_axes_m requires the {name} axis") from exc
        if axis.ndim != 1 or axis.size < 2:
            raise ValueError(f"source axis {name} must be a 1-D array with at least two points")
        if not np.isfinite(axis).all():
            raise ValueError(f"source axis {name} must contain only finite values")
        if np.any(np.diff(axis) <= 0.0):
            raise ValueError(f"source axis {name} must be strictly increasing")
        result.append(axis)
    return tuple(result)


def interpolate_complex_rectilinear_field(source_axes_m, source_values, target_points_m):
    """Complex rectilinear field interpolation

    Parameters
    ----------
    source_axes_m : real array-like
        Mapping with keys x_m, y_m, and z_m holding the three strictly increasing source
        axes. [m] Shape: ``mapping of three [N_axis] arrays``. Each axis is one-dimensional,
        finite, has at least two points, and is strictly increasing.

    source_values : complex array-like
        Complex field samples on the tensor-product source grid, indexed [x, y, z]; trailing
        axes are preserved. [caller-declared field units] Shape: ``[N_x,N_y,N_z] plus
        optional trailing axes``. Leading shape must equal (N_x, N_y, N_z); values are not
        required to be finite, and non-finite entries propagate into every target point
        whose stencil touches them.

    target_points_m : real array-like
        Target Cartesian points to sample, one point per row. [m] Shape: ``[N_point,3]``.
        Two-dimensional, exactly three columns, and finite; non-finite target points are
        rejected rather than masked.

    Returns
    -------
    interpolated_values : complex128
        Interpolated complex field value per target point, with the source trailing axes
        preserved. [caller-declared field units] Shape: ``[N_point] plus optional trailing
        axes``. nan+nanj wherever valid_mask is false; finite at every valid_mask point only
        when the touched source values are finite.
    valid_mask : bool
        Geometric containment predicate: true exactly when the target point lies inside the
        closed source box expanded by tol. [dimensionless] Shape: ``[N_point]``. Independent
        of source and result finiteness; a true entry does not guarantee a finite
        interpolated value.

    Raises
    ------
    ValueError
        Raises ValueError for a missing or non-mapping source_axes_m, an axis that is not one-dimensional, has fewer than two points, is non-finite, or is not strictly increasing, for a source_values leading shape that does not match the axes, and for target points that are not a finite (N,3) array.

    See Also
    --------
    sample_rectilinear_field : Rectilinear R-Z bilinear sampling.
    map_axisymmetric_equilibrium_to_cartesian_grid : Axisymmetric equilibrium map to Cartesian solver grid.

    Notes
    -----
    Separable trilinear interpolation in [x, y, z] axis order with the source values indexed
    [N_x, N_y, N_z]; target points inside the closed source box expanded by tol are clamped
    onto the closed box and interpolated, and target points outside that expanded box return
    nan+nanj with valid_mask false.

    **Coordinates.** caller-declared Cartesian axes in metres, indexed [x, y, z]

    **Boundary.** closed-box domain expanded by tol = 32 * eps * max(1, max axis span);
    outside the expansion no extrapolation is performed

    **Preconditions.**

    * The complex field is sampled on a tensor-product rectilinear grid that is dense enough
      for trilinear reconstruction to be meaningful over the region of interest.

    **Limits.**

    * Extrapolation beyond the tolerance-expanded source box.
    * Curvilinear, cylindrical, or unstructured source grids.
    * Masking or repairing non-finite source data; that decision belongs to the caller.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.geometry import interpolate_complex_rectilinear_field
    >>> axes = {'x_m': np.array([0.0, 1.0, 2.0]), 'y_m': np.array([0.0, 1.0, 2.0]), 'z_m': np.array([0.0, 1.0, 2.0])}
    >>> values = np.zeros((3, 3, 3), dtype=complex)
    >>> values[1, 1, 1] = 4.0 + 2.0j
    >>> points = np.array([[1.0, 1.0, 1.0], [1.0 + 1.0e-15, 1.0, 1.0], [1.0, 1.0, 3.0]])
    >>> result = interpolate_complex_rectilinear_field(axes, values, points)
    >>> assert result['valid_mask'].tolist() == [True, True, False]
    >>> assert np.isfinite(result['interpolated_values'][:2]).all()
    >>> assert np.isnan(result['interpolated_values'][2].real) and np.isnan(result['interpolated_values'][2].imag)
    """
    from scipy.interpolate import RegularGridInterpolator

    axes = _source_axes(source_axes_m)
    values = np.asarray(source_values, dtype=complex)
    expected = tuple(axis.size for axis in axes)
    if values.shape[:3] != expected:
        raise ValueError("source_values leading shape must match the three source axes")
    points = np.asarray(target_points_m, dtype=float)
    if points.ndim != 2 or points.shape[1] != 3 or not np.isfinite(points).all():
        raise ValueError("target_points_m must be a finite array with shape (n_points, 3)")

    lower = np.array([axis[0] for axis in axes])
    upper = np.array([axis[-1] for axis in axes])
    scale = np.max(np.maximum(1.0, np.abs(upper - lower)))
    tolerance = 32.0 * np.finfo(float).eps * float(scale)
    valid = np.all((points >= lower - tolerance) & (points <= upper + tolerance), axis=1)
    query = np.clip(points, lower, upper)
    interpolator = RegularGridInterpolator(
        axes,
        values,
        method="linear",
        bounds_error=False,
        fill_value=np.nan + 1j * np.nan,
    )
    output = np.asarray(interpolator(query), dtype=complex)
    output[~valid] = np.nan + 1j * np.nan
    return {"interpolated_values": output, "valid_mask": valid}
