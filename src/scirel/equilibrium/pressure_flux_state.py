"""Pressure spline and derivative state for the isotropic flux solver."""
from __future__ import annotations

import numpy as np

from ._pressure_current import fit_pressure_spline, pressure_derivative as _pressure_derivative

__all__ = ["build_pressure_flux_state"]


def _finite_grid(name, value, shape=None):
    array = np.asarray(value, dtype=float)
    if array.ndim != 2:
        raise ValueError(f"{name} must be a two-dimensional [Z,R] array")
    if shape is not None and array.shape != shape:
        raise ValueError(f"{name} must have shape {shape}")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must contain only finite values")
    return array


def _representation(spline, psi_samples, pressure_samples):
    knots, coefficients, degree = spline._eval_args
    return {
        "psi_samples": np.asarray(psi_samples, dtype=float),
        "pressure_samples": np.asarray(pressure_samples, dtype=float),
        "knots": np.asarray(knots, dtype=float),
        "coefficients": np.asarray(coefficients, dtype=float),
        "degree": int(degree),
        "extrapolation": "zeros",
        "evaluation": "InterpolatedUnivariateSpline(psi_samples, pressure_samples, ext='zeros')",
    }


def build_pressure_flux_state(r_grid, z_grid, psi, pressure_of_radius, plasma_mask=None):
    """Fit the midplane pressure prefix and return its clipped flux derivative."""
    r_grid = _finite_grid("r_grid", r_grid)
    z_grid = _finite_grid("z_grid", z_grid, r_grid.shape)
    psi = _finite_grid("psi", psi, r_grid.shape)
    if not callable(pressure_of_radius):
        raise ValueError("pressure_of_radius must be callable as pressure_of_radius(R)")

    flat_r, flat_z, flat_psi = r_grid.ravel(), z_grid.ravel(), psi.ravel()
    midplane = np.where(flat_z == 0.0)[0]
    zero_rows = np.where(np.all(z_grid == 0.0, axis=1))[0]
    if zero_rows.size != 1 or midplane.size != r_grid.shape[1]:
        raise ValueError("z_grid must contain exactly one complete zero midplane row")
    midplane = midplane[np.argsort(flat_r[midplane])]
    radii = flat_r[midplane]
    if np.any(np.diff(radii) <= 0.0):
        raise ValueError("midplane radii must be distinct")

    pressure = np.asarray([pressure_of_radius(radius) for radius in radii], dtype=float)
    if pressure.ndim != 1 or not np.all(np.isfinite(pressure)) or np.any(pressure < 0.0):
        raise ValueError("pressure_of_radius must return finite nonnegative scalar values")
    zero = np.flatnonzero(pressure == 0.0)
    if zero.size == 0:
        raise ValueError("pressure_of_radius must define an exact zero-pressure boundary")
    limiter = int(zero[0])
    psi_prefix = flat_psi[midplane][:limiter + 1]
    if psi_prefix.size < 4 or not np.all(np.diff(psi_prefix) > 0.0):
        raise ValueError("midplane psi samples must be strictly increasing with at least four points")

    spline = fit_pressure_spline(psi_prefix, pressure[:limiter + 1])
    psi_edge = float(flat_psi[midplane][limiter])
    if plasma_mask is not None:
        mask = np.asarray(plasma_mask)
        if mask.shape != r_grid.shape or mask.dtype.kind != "b":
            raise ValueError("plasma_mask must have the same shape as r_grid and be boolean")
    else:
        mask = None
    derivative = _pressure_derivative(spline, flat_psi, psi_edge, None if mask is None else mask.ravel())
    return {
        "pressure_derivative": derivative,
        "zero_currents": np.zeros_like(derivative),
        "psi_edge": psi_edge,
        "pressure_of_psi": _representation(spline, psi_prefix, pressure[:limiter + 1]),
        "limiter_index": limiter,
    }
