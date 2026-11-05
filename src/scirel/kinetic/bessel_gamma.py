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
    """Evaluate a scaled modified-Bessel harmonic term and its derivative.

    Parameters
    ----------
    n : real numeric, shape scalar or nonempty array
        Integer Bessel order [dimensionless integer]. It must broadcast with
        ``x``, be finite after float64 conversion, and contain exactly
        representable integers with absolute value no greater than ``2**53``.
    x : real or complex numeric, shape scalar or nonempty array
        Dimensionless argument [dimensionless]. It must broadcast with ``n``
        and be finite after complex128 conversion. Boolean, string and empty
        inputs are rejected.

    Returns
    -------
    Gamma_n : ndarray of complex128, shape broadcast of n and x
        Scaled term ``Gamma_n(x)=exp(-x) I_n(x)`` [dimensionless]. Scalar
        inputs produce a zero-dimensional array.
    Gamma_prime_n : ndarray of complex128, shape broadcast of n and x
        Neighbor-combination derivative with respect to ``x`` [dimensionless].
        Scalar inputs produce a zero-dimensional array.

    Raises
    ------
    ValueError
        If ``n`` or ``x`` is empty, boolean, nonnumeric, nonbroadcastable or
        nonfinite, if an order is complex, nonintegral or outside the declared
        representable range, or if the scaled result is not representable.
        Unexpected SciPy execution errors propagate.

    See Also
    --------
    scirel.kinetic.evaluate_generalized_dispersion : Density-family transform.
    scirel.kinetic.evaluate_plasma_dispersion : Maxwellian Z function.

    Notes
    -----
    The implementation uses the exponentially scaled Bessel backend and the
    stable neighbor combination

    ``Gamma_prime_n = (I_{n-1}/2 + I_{n+1}/2 - I_n) exp(-x)``.

    The scaling prevents an intermediate unscaled ``I_n`` from overflowing for
    large positive arguments. Inputs and outputs do not select a harmonic
    truncation; that choice belongs to the caller's dispersion assembly.

    Examples
    --------
    >>> from scirel.kinetic import evaluate_bessel_gamma
    >>> r = evaluate_bessel_gamma(0, 0.0)
    >>> assert r['Gamma_n'] == 1 and r['Gamma_prime_n'] == -1
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
            (0.5 * (ive(orders - 1, arguments) + ive(orders + 1, arguments)) - center) * scale,
            dtype=np.complex128,
        )
    if not np.all(np.isfinite(gamma)) or not np.all(np.isfinite(derivative)):
        raise ValueError("Bessel-Gamma value is not representable")
    return {"Gamma_n": gamma, "Gamma_prime_n": derivative}


__all__ = ["evaluate_bessel_gamma"]
