"""Real x-z wavevector projection in caller-normalized inverse-metre units."""

from __future__ import annotations

import numpy as np

__all__ = ["project_planar_wavevector"]


def _contains_boolean_pseudo_number(value):
    # np.asarray coerces [1, True] to an integer array and [np.bool_(True), 1.0]
    # to float, so dtype-kind inspection after conversion cannot see the booleans.
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
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError(f"{name} must be a nonempty finite real vector") from error
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
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError("theta_rad must be a finite real scalar") from error
    if not np.isfinite(result):
        raise ValueError("theta_rad must be a finite real scalar")
    return result


def project_planar_wavevector(
    *, k_grid=None, theta_rad=None, kx_grid=None, kz_grid=None
):
    """Project polar data or measure paired Cartesian components in the x-z plane.

    The caller must convert source-specific wave numbers to inverse metres first.
    This relation does not implement a dispersion model or PDRK scan state.
    """
    if k_grid is not None:
        if kx_grid is not None or kz_grid is not None:
            raise ValueError("choose a magnitude sweep or paired components")
        k = _finite_real_vector(k_grid, "k_grid")
        if np.any(k < 0):
            raise ValueError("k_grid must be a nonempty finite nonnegative vector")
        theta = _finite_real_angle(theta_rad)
        return {
            "kx": k * np.sin(theta),
            "kz": k * np.cos(theta),
            "k": k.copy(),
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
