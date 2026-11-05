"""A fixed-order rational approximation for the dimensionless plasma dispersion function with an analytic imaginary-axis path."""

import numpy as _np

__all__ = ["evaluate_plasma_dispersion_weideman"]

_N = 64
_M = 2 * _N
_M2 = 2 * _M


def _expansion_coefficients():
    """Weideman/Faddeeva rational-expansion coefficients (bonk/zfun.m:27-37)."""
    k = _np.arange(-_M + 1, _M, dtype=_np.float64).reshape(-1, 1)
    length = _np.sqrt(_N / _np.sqrt(2.0))
    theta = k * _np.pi / _M
    t = length * _np.tan(theta / 2.0)
    f = _np.exp(-(t**2)) * (length**2 + t**2)
    f = _np.concatenate([_np.zeros((1, 1)), f], axis=0)
    a = _np.real(_np.fft.fft(_np.fft.fftshift(f, axes=0), axis=0)) / _M2
    a = _np.flipud(a[1 : _N + 1])
    return a.ravel(), length


def _polyval(a, z):
    """the reference environment polyval semantics: a[0] is the highest-degree coefficient."""
    p = _np.full(z.shape, a[0], dtype=_np.complex128)
    for coefficient in a[1:]:
        p = p * z + coefficient
    return p


def evaluate_plasma_dispersion_weideman(z):
    """Evaluate the fixed-order Weideman plasma dispersion response.

    Parameters
    ----------
    z : real or complex numeric, shape scalar or nonempty array
        Argument of the plasma dispersion function [dimensionless]. The input
        is converted to complex128 and its shape is preserved.

    Returns
    -------
    Z : ndarray of complex128, shape same as z
        Plasma dispersion value ``i sqrt(pi) w(z)`` [dimensionless]. A scalar
        input produces a zero-dimensional array.
    w : ndarray of complex128, shape same as z
        Faddeeva response [dimensionless].
    method : ndarray of str, shape same as z
        Per-entry algorithm label [dimensionless], either ``'erfc'`` for
        exactly imaginary input or ``'rational'`` otherwise.
    all_purely_imaginary : bool
        ``True`` when every entry has exactly zero real part [dimensionless].

    Raises
    ------
    ValueError
        If ``z`` is empty or non-finite, if the returned ``Z`` or ``w`` is
        non-finite, or if the pure-imaginary branch exceeds its float64
        numerical range.

    Notes
    -----
    The pure-imaginary branch evaluates ``exp(-z**2) * erfc(imag(z))``
    directly. It is finite for magnitudes of about ``26.6`` or less. A larger
    pure-imaginary magnitude raises ``ValueError`` even when the asymptotic
    limit itself would still be representable.

    See Also
    --------
    scirel.kinetic.evaluate_plasma_dispersion : Direct Faddeeva evaluation.
    scirel.kinetic.evaluate_faddeeva_dr : Fixed-order Faddeeva variant.

    References
    ----------
    H. S. Xie, Phys. Plasmas 32, 082110 (2025).

    Examples
    --------
    >>> from scirel.kinetic import evaluate_plasma_dispersion_weideman
    >>> r=evaluate_plasma_dispersion_weideman(0j); assert abs(r['Z']-1j*__import__('math').sqrt(__import__('math').pi))<1e-12
    """
    zeta = _np.asarray(z, dtype=_np.complex128)
    if zeta.size == 0 or not _np.all(_np.isfinite(zeta)):
        raise ValueError("z must be nonempty and finite")

    # Keep the scientific backend out of import-time and rejected-input paths.
    # The rational branch below is unchanged; importing ``erfc`` only after
    # the input contract is established preserves the source backend and
    # numerical behavior for valid calls without making namespace discovery
    # pay the SciPy import cost.
    from scipy.special import erfc as _erfc

    shape = zeta.shape
    flat = zeta.reshape(-1)

    w = _np.zeros(flat.shape, dtype=_np.complex128)
    method = _np.full(flat.shape, "rational", dtype=object)

    idx = _np.real(flat) == 0
    method[idx] = "erfc"
    with _np.errstate(over="ignore", invalid="ignore", under="ignore"):
        w[idx] = _np.exp(-(flat[idx] ** 2)) * _erfc(_np.imag(flat[idx]))

    all_purely_imaginary = bool(_np.all(idx))
    if not all_purely_imaginary:
        sel = ~idx
        lower = sel & (_np.imag(flat) < 0)
        work = flat.copy()
        work[lower] = _np.conj(work[lower])

        a, length = _expansion_coefficients()
        denom = length - 1j * work[sel]
        zc = (length + 1j * work[sel]) / denom
        p = _polyval(a, zc)
        w[sel] = 2.0 * p / denom**2 + (1.0 / _np.sqrt(_np.pi)) / denom
        with _np.errstate(over="ignore", invalid="ignore"):
            w[lower] = _np.conj(2.0 * _np.exp(-(work[lower] ** 2)) - w[lower])

    Z = (1j * _np.sqrt(_np.pi) * w).reshape(shape)
    if not _np.all(_np.isfinite(Z)) or not _np.all(_np.isfinite(w)):
        raise ValueError("Weideman Z and w must be finite")
    return {
        "Z": Z,
        "w": w.reshape(shape),
        "method": method.reshape(shape),
        "all_purely_imaginary": all_purely_imaginary,
    }
