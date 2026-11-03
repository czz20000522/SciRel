"""Finite pressure-spline, current, and Green-map primitives."""
from __future__ import annotations

import numpy as np


def fit_pressure_spline(psi_samples, pressure_samples):
    """Fit the supplied pressure edge prefix with zero extrapolation."""
    flux = np.asarray(psi_samples, dtype=float)
    pressure = np.asarray(pressure_samples, dtype=float)
    valid = (
        flux.ndim == 1 and flux.size >= 4 and pressure.shape == flux.shape
        and np.all(np.isfinite(flux)) and np.all(np.isfinite(pressure))
        and np.all(np.diff(flux) > 0.0)
    )
    if not valid:
        raise FloatingPointError(
            "midplane flux must be finite and strictly increasing with at least four points"
        )
    from scipy.interpolate import InterpolatedUnivariateSpline
    fitted = InterpolatedUnivariateSpline(flux, pressure, ext="zeros")
    if not np.all(np.isfinite(fitted.get_coeffs())):
        raise FloatingPointError("nonfinite pressure-current spline coefficients")
    return fitted


def pressure_derivative(fitted, flux, edge, clip=None):
    """Evaluate a fitted derivative and zero points beyond the pressure edge."""
    values = np.asarray(fitted.derivative()(flux), dtype=float)
    if not np.all(np.isfinite(values)):
        raise FloatingPointError("nonfinite pressure-current derivative")
    values = np.array(values, copy=True)
    values[np.asarray(flux) > edge] = 0.0
    if clip is not None:
        values[np.asarray(clip, dtype=bool)] = 0.0
    return values


def current_target(radius, derivative, dr, dz):
    """Return cell currents ``R*dP/dpsi*dR*dZ`` without masking failures."""
    with np.errstate(over="ignore", invalid="ignore"):
        target = np.asarray(radius) * np.asarray(derivative) * dr * dz
    if not np.all(np.isfinite(target)):
        raise FloatingPointError("nonfinite pressure-current target")
    return target


def relaxed_green_update(target, old, relax, green, vacuum):
    """Mix cell currents, contract the Green matrix, and add vacuum flux."""
    with np.errstate(over="ignore", invalid="ignore"):
        currents = (1.0 - relax) * target + relax * old
        plasma = green @ currents
        flux = plasma + vacuum
    if not np.all(np.isfinite(currents)):
        raise FloatingPointError("nonfinite relaxed current")
    if not np.all(np.isfinite(plasma)):
        raise FloatingPointError("nonfinite Green update")
    if not np.all(np.isfinite(flux)):
        raise FloatingPointError("nonfinite total flux")
    return currents, flux
