"""Projection and validation of real x-z wavevector grids."""

from __future__ import annotations

import numpy as np

__all__ = ["project_planar_wavevector"]


def _contains_boolean_pseudo_number(value):
    if isinstance(value, np.ndarray):
        return value.dtype.kind == "b"
    if isinstance(value, (list, tuple)):
        return any(isinstance(item, (bool, np.bool_)) for item in value)
    return isinstance(value, (bool, np.bool_))


def _finite_real_vector(value, name):
    if _contains_boolean_pseudo_number(value):
        raise ValueError(f"{name} must be a nonempty finite real vector")
    try:
        original = np.asarray(value)
        if original.ndim != 1 or original.size == 0 or original.dtype.kind not in "iuf":
            raise ValueError
        result = original.astype(float)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be a nonempty finite real vector") from exc
    if not np.isfinite(result).all():
        raise ValueError(f"{name} must be a nonempty finite real vector")
    return result


def _finite_real_angle(value):
    if value is None:
        return 0.0
    try:
        original = np.asarray(value)
        if original.ndim != 0 or original.dtype.kind not in "iuf":
            raise ValueError
        result = float(original)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("theta_rad must be a finite real scalar") from exc
    if not np.isfinite(result):
        raise ValueError("theta_rad must be a finite real scalar")
    return result


def project_planar_wavevector(*, k_grid=None, theta_rad=None, kx_grid=None, kz_grid=None):
    """Planar real wavevector projection

    Parameters
    ----------
    k_grid : real array-like, optional
        Wavevector magnitude sweep in polar mode. [1/m] Shape: ``[N]``. Nonempty,
        one-dimensional, finite and nonnegative; boolean pseudo-numbers are rejected even
        where NumPy would coerce a mixed container such as [1, True] to integers; exclusive
        with component grids. Optional; default ``None``.

    theta_rad : real scalar, optional
        Propagation angle from +z toward +x; ignored in Cartesian mode. [rad] Shape:
        ``scalar``. Defaults to zero in polar mode and must be finite there; boolean and
        string surrogates are rejected. Optional; default ``None``.

    kx_grid : real array-like, optional
        Perpendicular component sweep in Cartesian mode. [1/m] Shape: ``[N]``. Requires a
        same-length kz_grid; boolean pseudo-numbers are rejected; exclusive with k_grid.
        Optional; default ``None``.

    kz_grid : real array-like, optional
        Parallel component sweep in Cartesian mode. [1/m] Shape: ``[N]``. Requires a
        same-length kx_grid; boolean pseudo-numbers are rejected; exclusive with k_grid.
        Optional; default ``None``.

    Returns
    -------
    kx : float64
        Perpendicular x component. [1/m] Shape: ``[N]``. Finite for accepted input.
    kz : float64
        Parallel z component. [1/m] Shape: ``[N]``. Finite for accepted input.
    k : float64
        Nonnegative wavevector magnitude. [1/m] Shape: ``[N]``. Finite for accepted input.
    theta_rad : float or null
        Declared polar angle or null in Cartesian mode. [rad or null] Shape: ``scalar or
        null``. Not a derived Cartesian angle.
    projection_mode : string
        Selected declaration mode. [dimensionless] Shape: ``scalar``. polar or cartesian.

    Raises
    ------
    ValueError
        Raises ValueError for missing or mixed modes, non-real or nonfinite vectors, boolean pseudo-numbers including mixed containers that NumPy would coerce (for example [1, True]), negative polar magnitude, non-real or nonfinite polar angle, invalid component shape, or nonfinite computed Cartesian magnitude.

    See Also
    --------
    scirel.geometry : Geometry namespace

    Notes
    -----
    Polar: kx = k sin(theta_rad), kz = k cos(theta_rad). Cartesian: k = hypot(kx, kz). The
    two input modes are exclusive.

    **Coordinates.** Cartesian x-z components with z parallel to the background field

    **Boundary.** Magnitude is nonnegative; zero magnitude keeps the supplied polar angle,
    whereas Cartesian mode returns no angle.

    **Preconditions.**

    * Caller has already converted all wave numbers to 1/m.
    * Arrays are finite real vectors; paired components have equal length.

    **Limits.**

    * Scan-driver selection, logarithmic controls, parameter-state updates and derived angle
      output.
    * Complex wavevectors, y components, coordinate rotations and dispersion physics.

    Examples
    --------
    >>> from scirel.geometry import project_planar_wavevector
    >>> result = project_planar_wavevector(kx_grid=[3.0], kz_grid=[4.0])
    >>> assert result['k'][0] == 5.0
    """
    if k_grid is not None:
        if kx_grid is not None or kz_grid is not None:
            raise ValueError("choose a magnitude sweep or paired components")
        magnitude = _finite_real_vector(k_grid, "k_grid")
        if np.any(magnitude < 0.0):
            raise ValueError("k_grid must be a nonempty finite nonnegative vector")
        theta = _finite_real_angle(theta_rad)
        return {
            "kx": magnitude * np.sin(theta),
            "kz": magnitude * np.cos(theta),
            "k": magnitude.copy(),
            "theta_rad": theta,
            "projection_mode": "polar",
        }
    if kx_grid is None or kz_grid is None:
        raise ValueError("both component grids are required")
    kx = _finite_real_vector(kx_grid, "kx_grid")
    kz = _finite_real_vector(kz_grid, "kz_grid")
    if kx.shape != kz.shape:
        raise ValueError("component grids must be finite paired nonempty vectors")
    with np.errstate(over="ignore"):
        magnitude = np.hypot(kx, kz)
    if not np.isfinite(magnitude).all():
        raise ValueError("wavevector magnitude exceeds the finite numeric domain")
    return {
        "kx": kx.copy(),
        "kz": kz.copy(),
        "k": magnitude,
        "theta_rad": None,
        "projection_mode": "cartesian",
    }
