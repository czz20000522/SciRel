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
    """Interpolate ``source_values[x, y, z]`` at target points.

    The closed source box is expanded by a machine-scale tolerance.  Points
    within that tolerance are clamped to the box and marked valid; other points
    receive ``nan+nanj`` and ``False``.  Source non-finite values intentionally
    propagate through an otherwise geometrically valid stencil.
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
        axes, values, method="linear", bounds_error=False,
        fill_value=np.nan + 1j * np.nan,
    )
    output = np.asarray(interpolator(query), dtype=complex)
    output[~valid] = np.nan + 1j * np.nan
    return {"interpolated_values": output, "valid_mask": valid}
