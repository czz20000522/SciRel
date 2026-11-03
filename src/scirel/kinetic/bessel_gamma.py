"""Vectorized exponentially scaled modified-Bessel factors and their derivatives for harmonic sums."""
from __future__ import annotations

import numpy as np


def _numeric_array(value, name):
    """Promote a numeric input without accepting object or boolean arrays."""
    try:
        values = np.asarray(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{name} must contain finite numeric values") from error
    if values.size == 0 or values.dtype.kind not in "iufc":
        raise ValueError(f"{name} must contain finite numeric values")
    return values


def evaluate_bessel_gamma(n, x):
    """Return Gamma_n(x) = exp(-x) I_n(x) and its derivative in x.

    ``n`` contains integer orders, ``x`` finite dimensionless real or complex
    arguments. Inputs broadcast; a scalar call returns zero-dimensional arrays.
    The scaled Bessel backend avoids forming unscaled I_n at large positive x.
    """
    orders = _numeric_array(n, "n")
    arguments = _numeric_array(x, "x")
    if orders.dtype.kind == "c":
        raise ValueError("n must contain integer orders")
    try:
        orders = np.asarray(orders, dtype=np.float64)
        arguments = np.asarray(arguments, dtype=np.complex128)
        orders, arguments = np.broadcast_arrays(orders, arguments)
    except (TypeError, OverflowError, ValueError) as error:
        raise ValueError("n and x must be numeric and broadcastable") from error
    if (
        not np.all(np.isfinite(orders))
        or np.any(orders != np.trunc(orders))
        or np.any(np.abs(orders) > 2**53)
    ):
        raise ValueError("n must contain exactly representable integer orders")
    if not np.all(np.isfinite(arguments)):
        raise ValueError("x must contain finite values")

    # Keep the special-function backend out of module import and rejected-input
    # paths.  SciPy remains a declared core runtime dependency; loading it only
    # after the public input contract is established preserves the exact
    # numerical implementation while keeping discovery and failure paths light.
    from scipy.special import ive

    with np.errstate(divide="ignore", invalid="ignore", over="ignore", under="ignore"):
        scale = np.exp(-arguments + np.abs(arguments.real))
        center = ive(orders, arguments)
        gamma = np.asarray(center * scale, dtype=np.complex128)
        derivative = np.asarray(
            (0.5 * (ive(orders - 1, arguments) + ive(orders + 1, arguments)) - center)
            * scale,
            dtype=np.complex128,
        )
    if not np.all(np.isfinite(gamma)) or not np.all(np.isfinite(derivative)):
        raise ValueError("Bessel-Gamma value is not representable")
    return {"Gamma_n": gamma, "Gamma_prime_n": derivative}


__all__ = ["evaluate_bessel_gamma"]
