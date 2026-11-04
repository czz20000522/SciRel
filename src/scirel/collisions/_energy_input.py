"""Input contract shared by the collision-energy cross-section fits."""

from __future__ import annotations

import numpy as np


def finite_nonnegative_energy(value):
    try:
        raw = np.asarray(value)
        if raw.dtype.kind not in "iuf" or (
            isinstance(value, (list, tuple))
            and any(
                isinstance(item, (bool, np.bool_)) for item in np.asarray(value, dtype=object).flat
            )
        ):
            raise ValueError
        energy = np.asarray(raw, dtype=float)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("energy_ev must be a finite real array") from exc
    if not np.all(np.isfinite(energy)):
        raise ValueError("energy_ev must be finite")
    if np.any(energy < 0.0):
        raise ValueError("energy_ev must be nonnegative")
    return energy


def clipped_energy(value, lower, upper):
    """Validate energy and clip it to one fit's declared interval."""
    return np.clip(finite_nonnegative_energy(value), lower, upper)


def log_polynomial(log_argument, coefficients):
    """Evaluate a coefficient-first polynomial on an already logged input."""
    return np.polynomial.polynomial.polyval(log_argument, coefficients)


def positive_real_array(value, name):
    """Return a finite, strictly positive real array with a named contract."""
    try:
        raw = np.asarray(value)
        if raw.dtype.kind not in "iuf" or (
            isinstance(value, (list, tuple))
            and any(
                isinstance(item, (bool, np.bool_)) for item in np.asarray(value, dtype=object).flat
            )
        ):
            raise ValueError
        result = np.asarray(raw, dtype=float)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must contain real numeric values") from exc
    if not np.all(np.isfinite(result)):
        raise ValueError(f"{name} must be finite")
    if np.any(result <= 0.0):
        raise ValueError(f"{name} must be positive")
    return result


def bivariate_log_fit(log_x, log_y, coefficients):
    """Evaluate a 9-by-9 log-polynomial with one cached power table.

    The explicit accumulation order is intentional: it keeps the floating-point
    result stable while avoiding repeated power construction for every term.
    """
    powers_x = [log_x**i for i in range(coefficients.shape[1])]
    powers_y = [log_y**j for j in range(coefficients.shape[0])]
    result = np.zeros_like(log_x, dtype=float)
    for i, x_power in enumerate(powers_x):
        for j, y_power in enumerate(powers_y):
            result = result + coefficients[j, i] * x_power * y_power
    return result
