"""Dimensionless Coulomb-logarithm estimates used by SciRel collision models.

Temperatures are in keV, densities in m^-3, charge numbers are dimensionless,
and each result is dimensionless.  These are mathematical weak-coupling
estimates: positive finite inputs are required, while deciding whether a
computed logarithm is physically adequate (for example, positive and large
enough for a selected collision model) remains the caller's responsibility.

The relations are evaluated in logarithmic form so the dimensional product
``1000*T`` is never formed. They are mathematical weak-coupling estimates;
the caller remains responsible for selecting a collision model and checking
whether a returned logarithm is physically adequate.
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "calculate_log_lambda_ee",
    "calculate_log_lambda_ei",
    "calculate_log_lambda_ii",
]


def _positive_broadcast(*values):
    """Convert and broadcast named positive real inputs."""
    arrays = []
    for name, value in values:
        try:
            raw = np.asarray(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{name} must be a finite positive real value") from exc
        if (
            raw.dtype.kind not in "iuf"
            or raw.size == 0
            or np.ma.isMaskedArray(value)
            or any(
                isinstance(item, (bool, np.bool_))
                for item in np.asarray(value, dtype=object).flat
            )
        ):
            raise ValueError(f"{name} must be a finite positive real value")
        arr = np.asarray(raw, dtype=np.float64)
        if np.any(~np.isfinite(arr)) or np.any(arr <= 0):
            raise ValueError(f"{name} must be finite and strictly positive")
        arrays.append(arr)
    try:
        return np.broadcast_arrays(*arrays)
    except ValueError as exc:
        raise ValueError("Coulomb-log inputs must be broadcast-compatible") from exc


def _finite_result(value, name):
    """Reject a valid input whose result left binary64 range."""
    if not np.all(np.isfinite(value)):
        raise FloatingPointError(f"{name} is not representable")
    return value


def calculate_log_lambda_ee(T_e, n_e):
    """Return ``31 - 0.5*ln(n_e) + ln(1000*T_e)`` for e-e collisions."""
    T, n = _positive_broadcast(("T_e", T_e), ("n_e", n_e))
    with np.errstate(over="ignore", invalid="ignore"):
        result = 31.0 + np.log(1000.0) + np.log(T) - 0.5 * np.log(n)
    return _finite_result(result, "electron-electron Coulomb logarithm")


def calculate_log_lambda_ei(T_e, n_e):
    """Return ``31.3 - 0.5*ln(n_e) + ln(1000*T_e)`` for e-i collisions."""
    T, n = _positive_broadcast(("T_e", T_e), ("n_e", n_e))
    with np.errstate(over="ignore", invalid="ignore"):
        result = 31.3 + np.log(1000.0) + np.log(T) - 0.5 * np.log(n)
    return _finite_result(result, "electron-ion Coulomb logarithm")


def calculate_log_lambda_ii(T_i, n_i, Z_i):
    """Return ``30 - .5 ln(n_i) + 1.5 ln(1000*T_i) - 3 ln(Z_i)``."""
    T, n, z = _positive_broadcast(("T_i", T_i), ("n_i", n_i), ("Z_i", Z_i))
    with np.errstate(over="ignore", invalid="ignore"):
        result = (
            30.0
            + 1.5 * (np.log(1000.0) + np.log(T))
            - 0.5 * np.log(n)
            - 3.0 * np.log(z)
        )
    return _finite_result(result, "ion-ion Coulomb logarithm")
