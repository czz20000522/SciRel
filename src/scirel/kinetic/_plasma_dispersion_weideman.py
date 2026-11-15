"""A fixed-order rational approximation for the dimensionless plasma dispersion function with an analytic imaginary-axis path."""

import numpy as _np

from scirel._result import Result

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


def _evaluate_weideman(z):
    """Retain the fixed N=64 kernel for already validated complex128 input."""
    zeta = z

    # Keep the scientific backend out of import-time and rejected-input paths.
    # The rational branch below is unchanged. Load the special functions only
    # after the input contract is established to preserve the source backend and
    # numerical behavior for valid calls without making namespace discovery
    # pay the SciPy import cost.
    from scipy.special import erfc as _erfc, erfcx as _erfcx

    shape = zeta.shape
    flat = zeta.reshape(-1)

    w = _np.zeros(flat.shape, dtype=_np.complex128)

    idx = _np.real(flat) == 0
    positive_axis = idx & (_np.imag(flat) > 0)
    nonpositive_axis = idx & ~positive_axis
    with _np.errstate(over="ignore", invalid="ignore", under="ignore"):
        w[positive_axis] = _erfcx(_np.imag(flat[positive_axis]))
        w[nonpositive_axis] = _np.exp(-(flat[nonpositive_axis] ** 2)) * _erfc(
            _np.imag(flat[nonpositive_axis])
        )

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

    with _np.errstate(over="ignore", invalid="ignore"):
        Z = (1j * _np.sqrt(_np.pi) * w).reshape(shape)
    if not _np.all(_np.isfinite(Z)) or not _np.all(_np.isfinite(w)):
        raise FloatingPointError(
            "w and Z must be finite complex128; received nonfinite fixed64 results; "
            "legal results: finite w and Z; see scirel.kinetic.plasma-dispersion-function"
        )
    return Result(w=w.reshape(shape), Z=Z)
