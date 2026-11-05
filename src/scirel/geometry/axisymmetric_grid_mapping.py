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
    at_upper_z = values[ri, zi + 1] + rf * (values[ri + 1, zi + 1] - values[ri, zi + 1])
    return at_lower_z + zf * (at_upper_z - at_lower_z)


def _interpolate_cylindrical(r_axis, z_axis, values, radii, axial):
    return _evaluate_cylindrical(values, _interpolation_coordinates(r_axis, z_axis, radii, axial))


def map_axisymmetric_equilibrium_to_cartesian_grid(equilibrium, x_m, y_m, z_m):
    """Axisymmetric equilibrium map to Cartesian solver grid

    Parameters
    ----------
    equilibrium : Python mapping of array-like
        Caller-owned axisymmetric equilibrium mapping carrying r_m, z_m, psi_wb_per_rad,
        br_t, and bz_t. [mixed SI] Shape: ``mapping of arrays``. Must be a mapping. r_m and
        z_m are finite strictly increasing 1D axes of at least five points; psi_wb_per_rad,
        br_t, and bz_t are finite [N_r, N_z] arrays on the map axes. No other entry is read,
        so the flux-surface classification parameters are not part of this relation.

    x_m : real array-like
        Cartesian solver grid x axis. [m] Shape: ``[N_x]``. Finite, one-dimensional, at
        least two points, strictly increasing.

    y_m : real array-like
        Cartesian solver grid y axis. [m] Shape: ``[N_y]``. Finite, one-dimensional, at
        least two points, strictly increasing.

    z_m : real array-like
        Cartesian solver grid axial axis, shared with the map's axial coordinate. [m] Shape:
        ``[N_z]``. Finite, one-dimensional, at least two points, strictly increasing.

    Returns
    -------
    magnetic_flux_density_t : float64
        Static magnetic field on the solver grid, with the field vector in the last axis.
        [T] Shape: ``[N_x, N_y, N_z, 3]``. Finite everywhere. The transverse pair is the
        interpolated radial field split as br * (x, y) / r and is set exactly to zero on the
        axis, where that split is undefined.
    poloidal_flux_wb_per_rad : float64
        Poloidal flux per radian interpolated onto the solver grid. [Wb/rad] Shape: ``[N_x,
        N_y, N_z]``. Finite everywhere, and evaluated at the clamped query coordinates so
        that clamped points carry the box-face value.
    covered_mask : bool
        Grid points that lay inside the closed box spanned by the map axes before clamping.
        [dimensionless] Shape: ``[N_x, N_y, N_z]``. A point is covered when its radius is
        between the first and last map radial axis values and its axial coordinate is
        between the first and last map axial axis values. Because the map's radial axis is
        usually positive, the grid axis r = 0 is normally not covered.
    radially_clamped_point_count : int
        Number of grid points whose radius exceeded the outer map radius and was clamped
        onto it. [dimensionless] Shape: ``scalar``. Counts only radii above the outer map
        radius, matching the declared relation; radii below the inner map radius are clamped
        as well but are not counted.
    axially_clamped_point_count : int
        Number of grid points whose axial coordinate lay outside the map axial axis and was
        clamped onto a face. [dimensionless] Shape: ``scalar``. Counts points below the
        first and above the last map axial axis value.

    Raises
    ------
    ValueError
        Raises ValueError when equilibrium is not a mapping, when a required map entry is missing, when a map axis is not a finite strictly increasing 1D array of at least five points, when a map array does not have the [N_r, N_z] map shape or is not finite, or when a solver grid axis is not a finite strictly increasing 1D array of at least two points. Raises ValueError if floating-point interpolation or Cartesian assembly produces a non-finite poloidal flux or static field, including arithmetic overflow from finite source samples.

    See Also
    --------
    sample_rectilinear_field : Sibling sampler with a fail-closed query boundary.
    interpolate_complex_rectilinear_field : Interpolation of complex rectilinear fields.

    Notes
    -----
    Builds the radius and the axial coordinate of every Cartesian grid point, clamps each
    query coordinate onto the closed map box, evaluates the tensor-product linear
    interpolant of each map array at the clamped coordinates, splits the interpolated radial
    field into Cartesian transverse components, and marks the grid points that lay inside
    the closed map box.

    **Coordinates.** the map is cylindrical (r, z) and the target is Cartesian (x, y, z)
    with the axial coordinate shared; mesh built with C-order ij indexing over the target
    axes

    **Boundary.** the relation is defined on the closed box spanned by the map axes; a query
    point outside that box is clamped onto the nearest box face rather than rejected or
    extrapolated, and the clamping is counted

    **Preconditions.**

    * The equilibrium map is axisymmetric and finite on a strictly increasing R-Z grid of at
      least five points per axis.
    * The solver grid axes are finite and strictly increasing, and share the axial
      coordinate convention of the map.
    * The caller accepts that query points outside the map box are answered with the
      box-face value and reported through covered_mask.

    **Limits.**

    * Non-axisymmetric or three-dimensional equilibria.
    * Extrapolation beyond the map box; the relation clamps instead.
    * Spline, conservative, or flux-surface-aligned interpolation; only tensor-product
      linear interpolation is defined here.
    * Flux-surface classification, PML framing, and PEC masking, which belong to a
      separate relation.
    * Any unit conversion; the map arrays are taken in the caller's units.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.geometry import map_axisymmetric_equilibrium_to_cartesian_grid
    >>> r_axis = np.linspace(0.05, 1.0, 21)
    >>> z_axis = np.linspace(-0.5, 0.5, 21)
    >>> rr, zz = np.meshgrid(r_axis, z_axis, indexing='ij')
    >>> equilibrium = {
    ...     'r_m': r_axis,
    ...     'z_m': z_axis,
    ...     'psi_wb_per_rad': 0.9 * rr + 0.1 * np.sin(2.0 * np.pi * zz),
    ...     'br_t': 0.3 * rr - 0.1 * zz ** 2,
    ...     'bz_t': 1.0 - 0.4 * rr ** 2,
    ... }
    >>> result = map_axisymmetric_equilibrium_to_cartesian_grid(
    ...     equilibrium,
    ...     np.linspace(-0.5, 0.5, 9),
    ...     np.linspace(-0.5, 0.5, 9),
    ...     np.linspace(-0.4, 0.4, 7),
    ... )
    >>> magnetic = result['magnetic_flux_density_t']
    >>> assert magnetic.shape == (9, 9, 7, 3)
    >>> assert result['poloidal_flux_wb_per_rad'].shape == (9, 9, 7)
    >>> assert result['covered_mask'].shape == (9, 9, 7)
    >>> assert result['covered_mask'].sum() == 560
    >>> assert result['radially_clamped_point_count'] == 0
    >>> assert result['axially_clamped_point_count'] == 0
    >>> assert np.isfinite(magnetic).all()
    >>> assert magnetic[4, 4, 3, 0] == 0.0 and magnetic[4, 4, 3, 1] == 0.0
    >>> assert magnetic[4, 4, 3, 2] != 0.0
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
        (radius >= r_axis[0]) & (radius <= r_axis[-1]) & (zz >= z_axis[0]) & (zz <= z_axis[-1])
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
    if not np.isfinite(psi).all():
        raise ValueError("mapped equilibrium produced non-finite poloidal flux")
    return {
        "magnetic_flux_density_t": magnetic,
        "poloidal_flux_wb_per_rad": psi,
        "covered_mask": covered,
        "radially_clamped_point_count": int(np.count_nonzero(radius > r_axis[-1])),
        "axially_clamped_point_count": int(np.count_nonzero((zz < z_axis[0]) | (zz > z_axis[-1]))),
    }
