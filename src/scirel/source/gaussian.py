# Derived profile conventions: the profile convention, Copyright 2024 DeepMind Technologies Limited.
# Retained attribution: see licenses/.
"""Volume-normalized Gaussian radial source profile.

The explicit metric ports carry cell volumes; this is distinct from spatial
source-shape normalization and flux-surface interpolation. The retained
licence and reference are above.
"""

from __future__ import annotations
import numpy as np
from ._common import grid, normalize_log_shape, scalar, width_scalar

__all__ = ["gaussian_profile"]


def gaussian_profile(rho_norm, vpr, drho_norm, *, center, width, total):
    """Return a discrete volume-normalized Gaussian radial source profile.

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
    center : float
        Gaussian center [dimensionless]. The value must be a finite real
        scalar and may lie outside ``[0, 1]``.
    width : float
        Gaussian scale width [dimensionless]. A finite nonzero value produces
        a finite result unless the numerical result is not representable.
        Zero, NaN, and either infinity return an all-NaN profile after the
        other inputs have been validated. Negative finite widths are allowed
        because the Gaussian is even in ``width``.
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
        positive, if ``width`` is not a real scalar, or if ``center`` or
        ``total`` is not a finite real scalar. A numeric but nonfinite
        ``width`` is the documented NaN-return case and does not raise.
    FloatingPointError
        If the finite result is not representable as float64 or if float64
        rounding cannot preserve the requested discrete integral within 64
        float64 epsilons relative.

    See Also
    --------
    exponential_profile : Build the corresponding exponential radial profile.

    Notes
    -----
    The unnormalized shape is
    ``exp(-(rho_norm-center)**2 / (2 * width**2))``. The returned vector is
    the shape divided by its discrete integral and multiplied by ``total``.
    The computation shifts and factorizes the exponent for numerical
    stability, and floors the denominator ``2*width**2`` at float64 tiny.
    ``width`` is a scale parameter, not a full width at half maximum.

    The profile is defined only on the supplied cell grid. No interpolation,
    extrapolation, continuous quadrature, or array-parameter broadcasting is
    performed. Negligible tails may underflow to zero when doing so does not
    lose the requested discrete integral.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.source import gaussian_profile
    >>> r=np.array([.2,.6]); v=np.array([2.,3.]); d=np.array([.4,.6])
    >>> p=gaussian_profile(r,v,d,center=.5,width=.2,total=4.)
    >>> assert np.isclose(np.sum(p*v*d),4.)
    """
    rho, vpr_a, drho = grid(rho_norm, vpr, drho_norm)
    c = scalar(center, "center")
    w = width_scalar(width)
    total_f = scalar(total, "total")
    if w == 0 or not np.isfinite(w):
        return np.full(rho.shape, np.nan, dtype=np.float64)
    # Factor the difference of squares before subtraction. Squaring distances
    # first loses all grid-scale information for a remote finite center.
    r = np.asarray(rho, dtype=np.longdouble)
    ref = r[0] if c <= rho[0] else r[-1] if c >= rho[-1] else r[np.argmin(np.abs(r - c))]
    delta_square = (r - ref) * (r + ref - 2 * np.longdouble(c))
    # Preserve the repaired source's float64 denominator floor for tiny widths.
    with np.errstate(over="ignore", invalid="ignore"):
        den = max(
            np.longdouble(2) * np.longdouble(w) * np.longdouble(w),
            np.longdouble(np.finfo(np.float64).tiny),
        )
    log_shape = -delta_square / den
    with np.errstate(over="ignore", invalid="ignore"):
        weights = np.asarray(vpr_a, dtype=np.longdouble) * np.asarray(drho, dtype=np.longdouble)
    return normalize_log_shape(log_shape, weights, total_f)
