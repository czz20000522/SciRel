# Derived profile conventions: the profile convention, Copyright 2024 DeepMind Technologies Limited.
# Retained attribution: see licenses/.
"""Volume-normalized exponential radial source profile.

Normalization cancels decay_start; this is not a cutoff profile or a
velocity-space Maxwellian. The retained licence and reference are above.
"""

from __future__ import annotations
import numpy as np
from ._common import grid, normalize_log_shape, scalar, width_scalar

__all__ = ["exponential_profile"]


def exponential_profile(rho_norm, vpr, drho_norm, *, decay_start, width, total):
    """Return a discrete volume-normalized exponential radial source profile.

    Parameters
    ----------
    rho_norm : array_like, shape (N,)
        Cell-center normalized radius [dimensionless]. The input must be a
        nonempty one-dimensional real array that is finite, strictly
        increasing, and contained in ``[0, 1]``. Integer values are converted
        to float64; boolean, complex, string, masked, and multidimensional
        inputs are rejected.
    vpr : array_like, shape (N,)
        Volume metric at each cell center, per unit normalized radius [m^3].
        The input must have the same shape as ``rho_norm`` and contain only
        finite, strictly positive real values.
    drho_norm : array_like, shape (N,)
        Quadrature width of each radial cell [dimensionless]. The input must
        have the same shape as ``rho_norm`` and contain only finite, strictly
        positive real values. The discrete cell volume is ``vpr*drho_norm``.
    decay_start : float
        Reference decay location [dimensionless]. The value must be a finite
        real scalar. It cancels under normalization and therefore does not
        change the returned profile.
    width : float
        Exponential scale width [dimensionless]. A finite nonzero value
        produces a finite result unless the numerical result is not
        representable. Zero, NaN, and either infinity return an all-NaN
        profile after the other inputs have been validated. A positive width
        increases with ``rho_norm``; a negative width decreases with it.
    total : float
        Target discrete volume integral [profile quantity*m^3]. The value must
        be a finite real scalar and may be positive, negative, or zero.

    Returns
    -------
    profile : ndarray of float64, shape (N,)
        Cell-centered source profile [total quantity per m^3]. On a successful
        return, ``sum(profile*vpr*drho_norm)`` equals ``total`` within float64
        rounding error.

    Raises
    ------
    ValueError
        If a grid input is not a nonempty finite real one-dimensional array,
        if the grid is not strictly increasing in ``[0, 1]``, if the array
        lengths differ, if a volume weight or quadrature width is not strictly
        positive, if ``width`` is not a real scalar, or if ``decay_start`` or
        ``total`` is not a finite real scalar. A numeric but nonfinite
        ``width`` is the documented NaN-return case and does not raise.
    FloatingPointError
        If the finite result is not representable as float64 or if float64
        rounding cannot preserve the requested discrete integral within 64
        float64 epsilons relative.

    See Also
    --------
    gaussian_profile : Build the corresponding Gaussian radial profile.

    Notes
    -----
    The unnormalized shape is
    ``exp(-(decay_start-rho_norm) / width)``. The returned vector is the shape
    divided by its discrete integral and multiplied by ``total``. Because the
    same shape appears in the numerator and denominator, ``decay_start``
    cancels exactly from the normalized values even though it remains part of
    the validated public interface.

    The computation subtracts a grid endpoint before exponentiation and floors
    ``abs(width)`` at float64 tiny while retaining its sign. This is a single
    exponential shape on the supplied cells, not a cutoff profile, a
    Maxwellian, or a continuous-space quadrature rule. No interpolation,
    extrapolation, or array-parameter broadcasting is performed. Negligible
    tails may underflow to zero when doing so does not lose the requested
    discrete integral.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.source import exponential_profile
    >>> r=np.array([.2,.6]); v=np.array([2.,3.]); d=np.array([.4,.6])
    >>> p=exponential_profile(r,v,d,decay_start=.8,width=.2,total=4.)
    >>> assert np.isclose(np.sum(p*v*d),4.)
    """
    rho, vpr_a, drho = grid(rho_norm, vpr, drho_norm)
    scalar(decay_start, "decay_start")
    w = width_scalar(width)
    total_f = scalar(total, "total")
    if w == 0 or not np.isfinite(w):
        return np.full(rho.shape, np.nan, dtype=np.float64)
    # Subtract a grid endpoint before exponentiation; this is algebraically
    # identical to the source normalization and avoids overflow in start/w.
    reference = rho[0] if np.signbit(w) else rho[-1]
    safe_width = np.copysign(max(abs(w), np.finfo(np.float64).tiny), w)
    log_shape = (np.asarray(rho, dtype=np.longdouble) - np.longdouble(reference)) / np.longdouble(
        safe_width
    )
    weights = np.asarray(vpr_a, dtype=np.longdouble) * np.asarray(drho, dtype=np.longdouble)
    return normalize_log_shape(log_shape, weights, total_f)
