"""Shared independent reference for the Bessel-based kinetic responses.

Why ``mpmath``'s Bessel functions and not a recurrence: a recurrence reproduces the
implementation's *error* as well as its value, so it cannot separate "the Taylor
recurrence converged" from "the harmonic sum is right".  ``mpmath.besseli`` and
``mpmath.besselj``/``mpmath.bessely`` are computed from a different algorithm at
arbitrary precision, so agreement to 40 digits is a statement about the relation,
not about a shared recurrence.

The two relations this module supplies:

``ronnmark_r_function``
    The contract's own definition, ``R = sum_n n**2 Gamma_n / (lambda (x - n))``
    and ``H = d(lambda R)/d lambda = sum_n n**2 Gamma'_n / (x - n)`` with
    ``Gamma_n = exp(-lambda) I_n(lambda)``.  The sum runs over all integers; here it
    is truncated at ``|n| <= N`` with ``N`` grown until the tail is below the working
    precision, which is the one place a truncation could hide an error, so the tail
    mass is asserted rather than assumed.

``relativistic_codrift``
    Nothing Bessel-specific: that pencil is checked against its own generalized
    eigenproblem.  ``besselj``/``bessely`` are provided because the oscillatory
    (unmagnetised) representation of the same response is the other branch a reader
    may reach for, and having both here keeps the "no home-made recurrence" rule in
    one place.
"""

from __future__ import annotations

import mpmath as mp

PRECISION = 40


def high_precision(precision: int = PRECISION) -> None:
    """Set the reference precision; ``mpmath`` precision is process-global."""
    mp.mp.dps = precision


# --- Ronnmark harmonic response -------------------------------------------------


def gamma_harmonic(order: int, lam) -> "mp.mpc":
    """``Gamma_n(lambda) = exp(-lambda) * I_n(lambda)`` at the working precision.

    ``lambda`` may be complex; ``mpmath.besseli`` accepts a complex argument, which
    is what the complex-``k_perp`` scan needs.
    """
    high_precision()
    lam = mp.mpmathify(lam)
    return mp.e ** (-lam) * mp.besseli(int(order), lam)


def gamma_harmonic_derivative(order: int, lam) -> "mp.mpc":
    """``d Gamma_n / d lambda`` using ``I_n' = (I_{n-1} + I_{n+1})/2``.

    The derivative is taken analytically, not by finite differences: a difference
    quotient would carry a truncation error of its own and could not be used to
    separate a wrong ``Gamma'_n`` from a wrong sum.
    """
    high_precision()
    lam = mp.mpmathify(lam)
    n = int(order)
    return mp.e ** (-lam) * ((mp.besseli(n - 1, lam) + mp.besseli(n + 1, lam)) / 2 - mp.besseli(n, lam))


def _harmonic_series(lam, x, weight, limit_min: int = 80) -> tuple:
    """Sum ``weight(n) * Gamma_n(lambda) / (x - n)`` over ``-N..N`` and report the tail.

    The truncation limit is doubled until two successive partial sums agree to the
    working precision, and the last increment is returned as ``tail`` so a caller can
    assert the truncation is negligible instead of trusting it.
    """
    high_precision()
    lam = mp.mpmathify(lam)
    x = mp.mpmathify(x)
    limit = limit_min
    previous = None
    for _ in range(12):
        total = mp.mpc(0)
        for n in range(-limit, limit + 1):
            if n == 0:
                continue
            denominator = x - n
            if denominator == 0:
                raise ZeroDivisionError("harmonic pole at integer x")
            total += weight(n) * gamma_harmonic(n, lam) / denominator
        if previous is not None:
            increment = abs(total - previous)
            if increment <= abs(total) * mp.mpf(10) ** (-(mp.mp.dps - 5)) or total == 0:
                return total, increment
        previous = total
        limit *= 2
    raise RuntimeError("harmonic truncation did not converge")


def ronnmark_r(x, lam) -> "mp.mpc":
    """``R = sum_n n**2 Gamma_n / (lambda (x - n))`` at the working precision.

    At exact ``lambda = 0`` the definition degenerates to ``R = x/(x**2 - 1)``, which
    is the reported limit and is returned directly instead of dividing by zero.
    """
    high_precision()
    lam = mp.mathify = mp.mpmathify(lam)
    if lam == 0:
        xv = mp.mpmathify(x)
        return xv / (xv * xv - 1)
    total, _tail = _harmonic_series(lam, x, lambda n: mp.mpf(n) ** 2 / lam)
    return total


def ronnmark_h(x, lam) -> "mp.mpc":
    """``H = sum_n n**2 Gamma'_n / (x - n)``, equal to ``d(lambda R)/d lambda``."""
    high_precision()
    lam = mp.mpmathify(lam)
    if lam == 0:
        xv = mp.mpmathify(x)
        return xv / (xv * xv - 1)
    total, _tail = _harmonic_series(lam, x, lambda n: mp.mpf(n) ** 2, )
    # The weight above supplies n**2 only; the derivative replaces Gamma by Gamma'.
    total = mp.mpc(0)
    for n in range(-80, 81):
        if n == 0:
            continue
        total += mp.mpf(n) ** 2 * gamma_harmonic_derivative(n, lam) / (mp.mpmathify(x) - n)
    return total


def ronnmark_truncation_tail(x, lam, limit: int = 80) -> float:
    """``|sum over |n| > limit| / |sum over |n| <= limit|`` for the R series."""
    high_precision()
    lam = mp.mpmathify(lam)
    head = mp.mpc(0)
    for n in range(-limit, limit + 1):
        if n == 0:
            continue
        head += mp.mpf(n) ** 2 * gamma_harmonic(n, lam) / (mp.mpmathify(x) - n)
    tail = mp.mpc(0)
    for n in list(range(-4 * limit, -limit)) + list(range(limit + 1, 4 * limit + 1)):
        tail += mp.mpf(n) ** 2 * gamma_harmonic(n, lam) / (mp.mpmathify(x) - n)
    if head == 0:
        return float(abs(tail))
    return float(abs(tail) / abs(head))


# --- oscillatory Bessel pair ----------------------------------------------------


def bessel_jv(order, argument) -> "mp.mpc":
    """``J_order(argument)`` from ``mpmath``, for the unmagnetised representation."""
    high_precision()
    return mp.besselj(order, mp.mpmathify(argument))


def bessel_yv(order, argument) -> "mp.mpc":
    """``Y_order(argument)`` from ``mpmath``."""
    high_precision()
    return mp.bessely(order, mp.mpmathify(argument))


def relative(measured, reference) -> float:
    """``|measured - reference| / |reference|`` as a float, complex-safe."""
    high_precision()
    measured = mp.mpmathify(measured)
    reference = mp.mpmathify(reference)
    if reference == 0:
        return float(abs(measured))
    return float(abs(measured - reference) / abs(reference))
