"""Polynomial-logarithmic approximation for complete ``K(m)`` and ``E(m)``."""

from __future__ import annotations

import numpy as np


def evaluate_complete_elliptic_integrals(modulus_squared):
    """Evaluate the declared ``0 <= m <= 1`` approximation elementwise.

    The endpoint is assigned its mathematical limits ``K(1)=inf`` and
    ``E(1)=1`` independently for each element, so mixed arrays do not inherit
    a batch-level sentinel.

    Parameters
    ----------
    modulus_squared : array_like
        Elliptic parameter ``m = k**2`` [dimensionless]. After float
        conversion, every entry must be finite and in ``[0, 1]``.

    Returns
    -------
    complete_k : ndarray
        First-kind complete elliptic integral approximation [dimensionless],
        with the input shape. Every ``m = 1`` entry is positive infinity.
    complete_e : ndarray
        Second-kind complete elliptic integral approximation [dimensionless],
        with the input shape. Every ``m = 1`` entry is exactly one.

    Raises
    ------
    ValueError
        If any converted entry is nonfinite or outside ``[0, 1]``.

    See Also
    --------
    scipy.special.ellipk : Library first-kind complete elliptic integral.
    scipy.special.ellipe : Library second-kind complete elliptic integral.

    Notes
    -----
    Fixed polynomials in ``p = 1-m`` are combined with ``log(p)``. This is
    a real elementwise approximation, without complex analytic continuation.
    The divergent ``K(1)`` does not represent a finite filament field.

    References
    ----------
    See ``scipy.special.ellipk`` and ``scipy.special.ellipe`` for the integral
    definitions; this function evaluates its fixed polynomial coefficients.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.field import evaluate_complete_elliptic_integrals
    >>> k, e = evaluate_complete_elliptic_integrals(np.array([0.5, 0.9]))
    >>> assert np.all(np.isfinite(k)) and np.all(np.isfinite(e))
    >>> k1, e1 = evaluate_complete_elliptic_integrals(np.array([1.0]))
    >>> assert np.isposinf(k1[0]) and e1[0] == 1.0
    >>> km, em = evaluate_complete_elliptic_integrals(np.array([0.5, 1.0]))
    >>> assert np.isposinf(km[1]) and em[1] == 1.0
    """
    m = np.asarray(modulus_squared, dtype=float)
    if not np.all(np.isfinite(m)) or np.any(m < 0.0) or np.any(m > 1.0):
        raise ValueError("modulus_squared must be finite and lie in [0,1]")
    p = 1.0 - m
    with np.errstate(divide="ignore", invalid="ignore"):
        k_a = np.polyval(
            (0.01451196212, 0.03742563713, 0.03590092383, 0.09666344259, 1.38629436112), p
        )
        k_b = np.polyval((0.00441787012, 0.03328355346, 0.06880248576, 0.12498593597, 0.5), p)
        e_a = np.polyval((0.01736506451, 0.04757383546, 0.0626060122, 0.44325141463, 1.0), p)
        e_b = p * np.polyval((0.00526449639, 0.04069697526, 0.09200180037, 0.2499836831), p)
        k_value = k_a - k_b * np.log(p)
        e_value = e_a - e_b * np.log(p)
    return np.where(m == 1.0, np.inf, k_value), np.where(m == 1.0, 1.0, e_value)


__all__ = ["evaluate_complete_elliptic_integrals"]
