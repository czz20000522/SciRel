"""Complex trilinear interpolation on a strict rectilinear grid.

SciRel already samples *real* rectilinear R-Z fields through
:func:`scirel.geometry.bilinear_grid_sampling.sample_rectilinear_field`.  That
operator is deliberately fail-closed: a query point outside the grid raises.
The relation here is the complex-valued, three-dimensional analogue used by
RF/antenna workflows, where the caller queries every cell of a Cartesian solver
grid and needs a per-point answer rather than an abort.  The two operators are
siblings, not duplicates: the sampling order, the dtype, the rank of the source
axes, and the out-of-domain policy all differ.

Out-of-domain policy (this is the honest contract; see the review-unit document
for why the earlier "finite if and only if valid" claim was withdrawn):

* ``valid_mask`` is a *geometric* predicate.  It is true exactly when the query
  point lies inside the closed source box expanded by ``tol``.
* Points that are inside the expanded box but outside the closed box are
  clamped onto the box before interpolation, so a finite source yields a finite
  value for every ``valid_mask`` point.
* Points outside the expanded box are not interpolated at all: the value is
  ``nan+nanj`` and ``valid_mask`` is false.
* ``valid_mask`` says nothing about the *source*.  A non-finite ``source_values``
  entry still propagates into every target point whose interpolation stencil
  touches it, and ``valid_mask`` stays true there.  Callers that need
  "value is finite" must test the returned values, not the mask.
"""
from __future__ import annotations

from collections.abc import Mapping

import numpy as np
from scipy.interpolate import RegularGridInterpolator

__all__ = ["interpolate_complex_rectilinear_field"]

_AXIS_KEYS = ("x_m", "y_m", "z_m")


def _source_axes(source_axes_m):
    if not isinstance(source_axes_m, Mapping):
        raise ValueError("source_axes_m must be a mapping of x_m, y_m, and z_m axes")
    axes = []
    for key in _AXIS_KEYS:
        try:
            axis = np.asarray(source_axes_m[key], dtype=float)
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"source_axes_m requires the {key} axis") from exc
        if axis.ndim != 1 or axis.size < 2:
            raise ValueError(f"source axis {key} must be a 1-D array with at least two points")
        if not np.all(np.isfinite(axis)):
            raise ValueError(f"source axis {key} must contain only finite values")
        if not np.all(np.diff(axis) > 0.0):
            raise ValueError(f"source axis {key} must be strictly increasing")
        axes.append(axis)
    return tuple(axes)


def interpolate_complex_rectilinear_field(source_axes_m, source_values, target_points_m):
    """Trilinearly interpolate a complex field at caller-owned target points.

    The source grid is the tensor product of three strictly increasing axes; the
    field array is indexed ``[x, y, z]``.  Points inside the tolerance-expanded
    source box are clamped onto the closed box and interpolated; points outside
    it return ``nan+nanj`` with ``valid_mask`` false.
    """
    axes = _source_axes(source_axes_m)
    values = np.asarray(source_values, dtype=complex)
    if values.shape[:3] != tuple(axis.size for axis in axes):
        raise ValueError("source_values leading shape must match the three source axes")
    points = np.asarray(target_points_m, dtype=float)
    if points.ndim != 2 or points.shape[1] != 3:
        raise ValueError("target_points_m must be a finite array with shape (n_points, 3)")
    if not np.all(np.isfinite(points)):
        raise ValueError("target_points_m must be a finite array with shape (n_points, 3)")

    lower = np.array([axis[0] for axis in axes], dtype=float)
    upper = np.array([axis[-1] for axis in axes], dtype=float)
    tolerance = 32.0 * np.finfo(float).eps * float(np.max(np.maximum(1.0, np.abs(upper - lower))))
    valid_mask = np.all((points >= lower - tolerance) & (points <= upper + tolerance), axis=1)
    # Invalid points are never handed to the interpolator, so they cannot come
    # back as a finite face value.  Only the valid points are clamped onto the
    # closed box, which is what keeps their interpolation finite.
    clamped = np.where(valid_mask[:, None], np.clip(points, lower, upper), lower)
    interpolator = RegularGridInterpolator(
        axes, values, method="linear", bounds_error=False, fill_value=np.nan + 1j * np.nan
    )
    mapped = np.asarray(interpolator(clamped), dtype=complex)
    mapped[~valid_mask] = np.nan + 1j * np.nan
    return {"interpolated_values": mapped, "valid_mask": valid_mask}
