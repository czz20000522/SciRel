"""Flux Green matrix for a symmetric rectilinear plasma grid."""

from __future__ import annotations

import numpy as np

from scirel._result import Result
from scirel.electromagnetism.greens import get_gpsi


def build_mirror_plasma_flux_green(r_grid, z_grid):
    """Build a mirror-grid flux Green matrix as a named result.

    Parameters
    ----------
    r_grid : real array-like, shape [N_Z,N_R]
        Cylindrical radius mesh shared by source and target cells [m]. Finite,
        rectilinear, with nonnegative strictly increasing R axis and at least
        two points per axis.
    z_grid : real array-like, shape [N_Z,N_R]
        Axial coordinate mesh shared by source and target cells [m]. Finite,
        rectilinear, with a uniformly spaced and reflection-symmetric Z axis.

    Returns
    -------
    g_psi : ndarray of float64, shape [N_Z*N_R,N_Z*N_R]
        Field ``g_psi`` of the returned ``scirel._result.Result`` mapping:
        source-compatible flux response per source current [Wb/rad/A], with
        target rows and source columns in C-order grid flattening.

    Raises
    ------
    ValueError
        If coordinates are complex or nonfinite, shapes differ, either axis
        has fewer than two points, the grid is not rectilinear and strictly
        increasing, or the Z axis is not uniformly spaced and reflection
        symmetric.
    FloatingPointError
        If the underlying flux kernel produces a nonfinite response.

    See Also
    --------
    scirel.electromagnetism.get_gpsi : Circular-filament flux kernel.
    scirel.field.dense_axisymmetric_green_response : General dense response.

    Notes
    -----
    The single array is stored directly in one ``scirel._result.Result``
    mapping. No nested mapping is returned, and mapping access remains
    available alongside attribute access.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel._result import Result
    >>> from scirel.field import build_mirror_plasma_flux_green
    >>> r_grid, z_grid = np.meshgrid(
    ...     np.linspace(0.0, 0.3, 4), np.linspace(-0.4, 0.4, 3)
    ... )
    >>> result = build_mirror_plasma_flux_green(r_grid, z_grid)
    >>> assert isinstance(result, Result)
    >>> assert list(result) == ['g_psi']
    >>> assert result.g_psi is result['g_psi']
    >>> assert result['g_psi'].shape == (r_grid.size, r_grid.size)
    >>> assert np.isfinite(result['g_psi']).all()
    >>> for source_plane in range(3):
    ...     np.testing.assert_allclose(
    ...         result['g_psi'][:, source_plane * 4], 0.0
    ...     )
    >>> np.testing.assert_allclose(
    ...     result['g_psi'][0:4, 4:8], result['g_psi'][4:8, 0:4]
    ... )
    """
    if np.iscomplexobj(r_grid) or np.iscomplexobj(z_grid):
        raise ValueError("grid coordinates must be real")
    radius, height = np.asarray(r_grid, dtype=float), np.asarray(z_grid, dtype=float)
    if radius.ndim != 2 or height.shape != radius.shape or min(radius.shape) < 2:
        raise ValueError(
            "r_grid and z_grid must be equal-shape 2-D grids with at least two points per axis"
        )
    if not np.all(np.isfinite(radius)) or not np.all(np.isfinite(height)):
        raise ValueError("r_grid and z_grid must be finite")
    radial, axial = radius[0], height[:, 0]
    if (
        not np.allclose(radius, radial[None, :])
        or not np.allclose(height, axial[:, None])
        or np.any(radial < 0.0)
        or np.any(np.diff(radial) <= 0.0)
        or np.any(np.diff(axial) <= 0.0)
    ):
        raise ValueError(
            "the source-compatible matrix requires a strictly increasing rectilinear R-Z grid"
        )
    if not np.allclose(axial, -axial[::-1], rtol=0.0, atol=1.0e-12):
        raise ValueError("the reflection construction requires an axis-reflection-symmetric Z grid")
    if not np.allclose(np.diff(axial), np.diff(axial)[0], rtol=1.0e-12, atol=1.0e-14):
        raise ValueError("the reflection construction requires a uniformly spaced Z grid")
    return Result({"g_psi": get_gpsi(radius, height)})


__all__ = ["build_mirror_plasma_flux_green"]
