"""Reconstruct an axisymmetric R-Z equilibrium on a Cartesian grid.

This mapping is a sibling of ``sample_rectilinear_field``: it consumes named
1-D equilibrium axes, returns a complete Cartesian vector field, and clamps
out-of-box queries while reporting coverage.
"""
from __future__ import annotations

from collections.abc import Mapping

import numpy as np

__all__ = ["map_axisymmetric_equilibrium_to_cartesian_grid"]
_REQUIRED_FIELDS = ("psi_wb_per_rad", "br_t", "bz_t")


def _grid_axes(x_m, y_m, z_m):
    axes = []
    for name, values in (("x_m", x_m), ("y_m", y_m), ("z_m", z_m)):
        axis = np.asarray(values, dtype=float)
        if axis.ndim != 1 or axis.size < 2:
            raise ValueError(f"grid axis {name} must be a 1D array of at least two points")
        if not np.isfinite(axis).all():
            raise ValueError(f"grid axis {name} must be finite")
        if np.any(np.diff(axis) <= 0.0):
            raise ValueError(f"grid axis {name} must be strictly increasing")
        axes.append(axis)
    return tuple(axes)


def _map_axes(r_m, z_m):
    r_axis, z_axis = np.asarray(r_m, dtype=float), np.asarray(z_m, dtype=float)
    if r_axis.ndim != 1 or z_axis.ndim != 1 or min(r_axis.size, z_axis.size) < 5:
        raise ValueError("equilibrium axes must be 1D arrays of at least five points")
    if not np.isfinite(r_axis).all() or not np.isfinite(z_axis).all():
        raise ValueError("equilibrium axes must be finite")
    if np.any(np.diff(r_axis) <= 0.0) or np.any(np.diff(z_axis) <= 0.0):
        raise ValueError("equilibrium axes must be strictly increasing")
    return r_axis, z_axis


def _interpolation_coordinates(r_axis, z_axis, radii, axial):
    """Return cell indices and normalized coordinates for bilinear evaluation."""
    r_index = np.clip(np.searchsorted(r_axis, radii, side="right") - 1, 0, r_axis.size - 2)
    z_index = np.clip(np.searchsorted(z_axis, axial, side="right") - 1, 0, z_axis.size - 2)
    r_fraction = (radii - r_axis[r_index]) / (r_axis[r_index + 1] - r_axis[r_index])
    z_fraction = (axial - z_axis[z_index]) / (z_axis[z_index + 1] - z_axis[z_index])
    return r_index, r_fraction, z_index, z_fraction


def _evaluate_cylindrical(values, coordinates):
    """Evaluate a pre-resolved tensor-product cell using four corners."""
    ri, rf, zi, zf = coordinates
    at_lower_z = values[ri, zi] + rf * (values[ri + 1, zi] - values[ri, zi])
    at_upper_z = values[ri, zi + 1] + rf * (
        values[ri + 1, zi + 1] - values[ri, zi + 1]
    )
    return at_lower_z + zf * (at_upper_z - at_lower_z)


def _interpolate_cylindrical(r_axis, z_axis, values, radii, axial):
    return _evaluate_cylindrical(
        values, _interpolation_coordinates(r_axis, z_axis, radii, axial)
    )


def map_axisymmetric_equilibrium_to_cartesian_grid(equilibrium, x_m, y_m, z_m):
    """Interpolate cylindrical equilibrium fields onto an ``(x, y, z)`` grid.

    Query points are clamped to the closed R-Z map box.  ``covered_mask`` and
    the two counters report which points required that clamp.  At ``R=0`` the
    radial Cartesian components are defined as zero because their cylindrical
    direction is undefined.
    """
    if not isinstance(equilibrium, Mapping):
        raise ValueError("equilibrium must be a mapping of caller-owned arrays")
    x_axis, y_axis, z_grid = _grid_axes(x_m, y_m, z_m)
    for name in ("r_m", "z_m", *_REQUIRED_FIELDS):
        if name not in equilibrium:
            raise ValueError(f"equilibrium is missing the required entry: {name}")
    r_axis, z_axis = _map_axes(equilibrium["r_m"], equilibrium["z_m"])
    expected = (r_axis.size, z_axis.size)
    fields = {}
    for name in _REQUIRED_FIELDS:
        field = np.asarray(equilibrium[name], dtype=float)
        if field.shape != expected:
            raise ValueError(f"equilibrium {name} must have shape {expected}")
        if not np.isfinite(field).all():
            raise ValueError(f"equilibrium {name} must be finite")
        fields[name] = field

    xx, yy, zz = np.meshgrid(x_axis, y_axis, z_grid, indexing="ij")
    radius = np.hypot(xx, yy)
    covered = (
        (radius >= r_axis[0]) & (radius <= r_axis[-1])
        & (zz >= z_axis[0]) & (zz <= z_axis[-1])
    )
    query_r = np.clip(radius, r_axis[0], r_axis[-1]).ravel()
    query_z = np.clip(zz, z_axis[0], z_axis[-1]).ravel()
    coordinates = _interpolation_coordinates(r_axis, z_axis, query_r, query_z)
    shape = radius.shape
    br = _evaluate_cylindrical(fields["br_t"], coordinates).reshape(shape)
    bz = _evaluate_cylindrical(fields["bz_t"], coordinates).reshape(shape)
    psi = _evaluate_cylindrical(fields["psi_wb_per_rad"], coordinates).reshape(shape)

    magnetic = np.zeros(shape + (3,), dtype=float)
    off_axis = radius > 0.0
    magnetic[..., 0] = np.divide(br * xx, radius, out=np.zeros_like(br), where=off_axis)
    magnetic[..., 1] = np.divide(br * yy, radius, out=np.zeros_like(br), where=off_axis)
    magnetic[..., 2] = bz
    if not np.isfinite(magnetic).all():
        raise ValueError("mapped equilibrium produced non-finite static B0")
    return {
        "magnetic_flux_density_t": magnetic,
        "poloidal_flux_wb_per_rad": psi,
        "covered_mask": covered,
        "radially_clamped_point_count": int(np.count_nonzero(radius > r_axis[-1])),
        "axially_clamped_point_count": int(np.count_nonzero((zz < z_axis[0]) | (zz > z_axis[-1]))),
    }
