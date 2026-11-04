"""fluidBW's fixed N=64 Weideman plasma-dispersion variant.

Faithful port of the Weideman/Faddeeva rational (FFT) expansion of
Z(z) = i*sqrt(pi)*w(z), w(z) = exp(-z^2)*erfc(-i*z), as used by the fluidBW
kinetic family. The source science is reproduced as-is: no repair, no
normalization, no convergence improvement.

Reference: bonk/zfun.m:1-46 in the frozen fluidBW source tree.
"""

import numpy as _np
from scipy.special import erfc as _erfc

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
    f = _np.exp(-(t ** 2)) * (length ** 2 + t ** 2)
    f = _np.concatenate([_np.zeros((1, 1)), f], axis=0)
    a = _np.real(_np.fft.fft(_np.fft.fftshift(f, axes=0), axis=0)) / _M2
    a = _np.flipud(a[1:_N + 1])
    return a.ravel(), length


def _polyval(a, z):
    """MATLAB polyval semantics: a[0] is the highest-degree coefficient."""
    p = _np.full(z.shape, a[0], dtype=_np.complex128)
    for coefficient in a[1:]:
        p = p * z + coefficient
    return p


def evaluate_plasma_dispersion_weideman(z):
    """Evaluate Z(z) for complex scalar or array input.

    Parameters
    ----------
    z : scalar or array_like of real/complex
        Argument of the plasma dispersion function. Shape is preserved.

    Returns
    -------
    dict with keys
        ``Z``      : ndarray, shape == shape(z); Z(z) = i*sqrt(pi)*w(z).
        ``w``      : ndarray, same shape; Faddeeva w(z).
        ``method`` : ndarray of str, same shape; ``'erfc'`` for entries with
                     real(z) == 0, ``'rational'`` otherwise.
        ``all_purely_imaginary`` : bool; True when every entry has
                     real(z) == 0 (the source early return, zfun.m:14-17).
    """
    zeta = _np.asarray(z, dtype=_np.complex128)
    if zeta.size == 0 or not _np.all(_np.isfinite(zeta)):
        raise ValueError("z must be nonempty and finite")
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
        w[sel] = 2.0 * p / denom ** 2 + (1.0 / _np.sqrt(_np.pi)) / denom
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
