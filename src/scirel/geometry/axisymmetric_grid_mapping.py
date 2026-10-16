"""Cylindrical-to-Cartesian reconstruction of an axisymmetric equilibrium map.

This is the first of the two scientific relations that the retained coarse-CAD
full-wave entry performs before any field solve: it reads an axisymmetric
equilibrium map in cylindrical coordinates, reconstructs the static field on a
Cartesian solver grid, and reports where the query grid left the map's support.

The declared relation is the **tensor-product (bilinear) interpolant** of the
map on its R-Z axes.  The retained docstring claimed that the two-stage
interpolation *ordering* was part of the relation; the review measured that
claim on a deliberately non-separable map and found it vacuous.  Both stages are
linear on a rectilinear grid, so the composition is the tensor-product
interpolant however the stages are ordered: the retained order, the swapped
order, this implementation, and scipy's ``RegularGridInterpolator`` all agree to
within float association (about 1.1e-16).  The two-stage form is therefore kept
as an implementation invariant, not as a discriminating choice, and the tests
assert the tensor-product identity rather than an ordering.

SciRel already samples *real* rectilinear R-Z fields through
:func:`scirel.geometry.bilinear_grid_sampling.sample_rectilinear_field`.  The
relation here is a sibling, not a duplicate, and this module deliberately does
not import, shadow, or re-export it.  Four differences make it a distinct
identity:

* the source is an equilibrium *mapping* with named arrays and 1-D axes, not a
  pair of 2-D coordinate meshes;
* the output is the whole Cartesian solver grid, including the cylindrical
  split into ``(Br*x/r, Br*y/r, Bz)`` and the poloidal flux, not a flat vector of
  scalars at caller-chosen points;
* the out-of-domain policy is clamp-and-report, not fail-closed: the frozen
  sampler raises for a point outside its grid, whereas this relation clamps onto
  the closed map box and reports the clamping through ``covered_mask`` and the
  two counters;
* the dtype is real in both, but the flux and field arrays are reconstructed
  together from one map rather than one scalar quantity at a time.

The relation is defined on the closed box spanned by the map axes, so a query
point outside that box is clamped onto the box face rather than rejected.  The
clamping is reported rather than hidden: ``covered_mask`` marks the query points
that lay inside the box, and the two clamp counters count the query points that
were moved onto the outer radius and onto either axial face.
"""
from __future__ import annotations

from collections.abc import Mapping

import numpy as np

__all__ = ["map_axisymmetric_equilibrium_to_cartesian_grid"]

_REQUIRED_MAP_ARRAYS = ("psi_wb_per_rad", "br_t", "bz_t")


def _grid_axes(x_m, y_m, z_m):
    axes = []
    for name, value in (("x_m", x_m), ("y_m", y_m), ("z_m", z_m)):
        array = np.asarray(value, dtype=float)
        if array.ndim != 1 or array.size < 2:
            raise ValueError(f"grid axis {name} must be a 1D array of at least two points")
        if not np.all(np.isfinite(array)):
            raise ValueError(f"grid axis {name} must be finite")
        if not np.all(np.diff(array) > 0.0):
            raise ValueError(f"grid axis {name} must be strictly increasing")
        axes.append(array)
    return tuple(axes)


def _map_axes(r_m, z_m):
    r_axis = np.asarray(r_m, dtype=float)
    z_axis = np.asarray(z_m, dtype=float)
    if r_axis.ndim != 1 or z_axis.ndim != 1 or r_axis.size < 5 or z_axis.size < 5:
        raise ValueError("equilibrium axes must be 1D arrays of at least five points")
    if not np.all(np.isfinite(r_axis)) or not np.all(np.isfinite(z_axis)):
        raise ValueError("equilibrium axes must be finite")
    if not np.all(np.diff(r_axis) > 0.0) or not np.all(np.diff(z_axis) > 0.0):
        raise ValueError("equilibrium axes must be strictly increasing")
    return r_axis, z_axis


def _interpolate_cylindrical(r_axis, z_axis, values, radii, axial):
    """Evaluate the tensor-product linear interpolant on flat query arrays.

    The retained source expressed this relation as radial interpolation
    followed by axial interpolation.  On strictly increasing rectilinear axes
    that is the same tensor-product bilinear interpolant as the direct
    four-corner expression below.  Resolving both enclosing cells at once
    avoids the source implementation's Python loop over query points and,
    crucially, avoids materializing a ``(n_queries, n_z)`` intermediate array.
    ``side='right'`` preserves ``numpy.interp`` endpoint behavior: an exact
    last-axis query selects the final cell with fraction one.
    """
    r_index = np.clip(
        np.searchsorted(r_axis, radii, side="right") - 1,
        0,
        r_axis.size - 2,
    )
    r_fraction = (radii - r_axis[r_index]) / (r_axis[r_index + 1] - r_axis[r_index])

    z_index = np.clip(
        np.searchsorted(z_axis, axial, side="right") - 1,
        0,
        z_axis.size - 2,
    )
    z_fraction = (axial - z_axis[z_index]) / (z_axis[z_index + 1] - z_axis[z_index])
    # Gather only the four enclosing cell corners.  Expanding the two stages
    # this way preserves the retained radial-then-axial order without creating
    # the O(points * map_z) intermediate used by the original column loop.
    radial_at_z0 = values[r_index, z_index] + r_fraction * (
        values[r_index + 1, z_index] - values[r_index, z_index]
    )
    radial_at_z1 = values[r_index, z_index + 1] + r_fraction * (
        values[r_index + 1, z_index + 1] - values[r_index, z_index + 1]
    )
    return radial_at_z0 + z_fraction * (radial_at_z1 - radial_at_z0)


def map_axisymmetric_equilibrium_to_cartesian_grid(equilibrium, x_m, y_m, z_m):
    """Reconstruct the axisymmetric static field on a Cartesian solver grid.

    ``equilibrium`` is a caller-owned mapping carrying the map axes ``r_m`` and
    ``z_m``, the map arrays ``psi_wb_per_rad``, ``br_t``, and ``bz_t`` on the
    ``[r, z]`` map grid, and nothing else: the flux-surface classification
    parameters belong to the material-support relation, not to this one.
    """
    if not isinstance(equilibrium, Mapping):
        raise ValueError("equilibrium must be a mapping of caller-owned arrays")
    x_axis, y_axis, z_axis_grid = _grid_axes(x_m, y_m, z_m)
    for key in ("r_m", "z_m", *_REQUIRED_MAP_ARRAYS):
        if key not in equilibrium:
            raise ValueError(f"equilibrium is missing the required entry: {key}")
    r_axis, z_axis = _map_axes(equilibrium["r_m"], equilibrium["z_m"])
    expected = (r_axis.size, z_axis.size)
    arrays = {}
    for name in _REQUIRED_MAP_ARRAYS:
        array = np.asarray(equilibrium[name], dtype=float)
        if array.shape != expected:
            raise ValueError(f"equilibrium {name} must have shape {expected}")
        if not np.all(np.isfinite(array)):
            raise ValueError(f"equilibrium {name} must be finite")
        arrays[name] = array

    xx, yy, zz = np.meshgrid(x_axis, y_axis, z_axis_grid, indexing="ij")
    radii = np.hypot(xx, yy)
    clamped_r = np.clip(radii, r_axis[0], r_axis[-1])
    clamped_z = np.clip(zz, z_axis[0], z_axis[-1])

    flat_r = clamped_r.ravel()
    flat_z = clamped_z.ravel()
    br = _interpolate_cylindrical(r_axis, z_axis, arrays["br_t"], flat_r, flat_z)
    bz = _interpolate_cylindrical(r_axis, z_axis, arrays["bz_t"], flat_r, flat_z)
    psi = _interpolate_cylindrical(
        r_axis, z_axis, arrays["psi_wb_per_rad"], flat_r, flat_z
    )

    shape = (x_axis.size, y_axis.size, z_axis_grid.size)
    br = br.reshape(shape)
    bz = bz.reshape(shape)
    psi = psi.reshape(shape)
    magnetic = np.zeros(shape + (3,), dtype=float)
    non_axis = radii > 0.0
    magnetic[..., 0][non_axis] = br[non_axis] * xx[non_axis] / radii[non_axis]
    magnetic[..., 1][non_axis] = br[non_axis] * yy[non_axis] / radii[non_axis]
    magnetic[..., 2] = bz

    covered = (
        (radii >= r_axis[0])
        & (radii <= r_axis[-1])
        & (zz >= z_axis[0])
        & (zz <= z_axis[-1])
    )
    if not np.all(np.isfinite(magnetic)):
        raise ValueError("mapped equilibrium produced non-finite static B0")

    return {
        "magnetic_flux_density_t": magnetic,
        "poloidal_flux_wb_per_rad": psi,
        "covered_mask": covered,
        "radially_clamped_point_count": int(np.count_nonzero(radii > r_axis[-1])),
        "axially_clamped_point_count": int(
            np.count_nonzero((zz < z_axis[0]) | (zz > z_axis[-1]))
        ),
    }
