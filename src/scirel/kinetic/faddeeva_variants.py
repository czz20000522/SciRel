"""Vectorized rational approximations for the Faddeeva and Maxwellian response functions. Coefficients are private numerical data and the public functions own validation, continuation, and shape preservation."""

from functools import lru_cache
import operator
import numpy as np
from ._generalized_pole_data import POLES

__all__ = [
    "evaluate_faddeeva_gpdf",
    "evaluate_faddeeva_dr",
    "evaluate_maxwellian_fft",
    "evaluate_maxwellian_jpole",
]


def _order(value):
    if isinstance(value, (bool, np.bool_)):
        raise ValueError("order must be a positive integer")
    try:
        n = operator.index(value)
    except TypeError:
        raise ValueError("order must be a positive integer") from None
    if n < 1:
        raise ValueError("order must be a positive integer")
    return n


def _input(z):
    a = np.asarray(z, dtype=complex)
    if a.size == 0 or not np.all(np.isfinite(a)):
        raise ValueError("z must be finite and nonempty")
    return a


@lru_cache(maxsize=16)
def _coefficients(n):
    m = 2 * n
    length = np.sqrt(n / np.sqrt(2))
    nodes = length * np.tan(np.arange(-m + 1, m) * np.pi / (2 * m))
    samples = np.r_[0.0, np.exp(-(nodes**2)) * (length**2 + nodes**2)]
    coefficients = np.fft.fft(np.fft.fftshift(samples)).real / (2 * m)
    return coefficients[1 : n + 1][::-1], length


def _evaluate(z, n):
    a = _input(z)
    shape = a.shape
    z = a.ravel()
    upper = np.where(z.imag < 0, np.conj(z), z)
    coefficients, length = _coefficients(n)
    denom = length - 1j * upper
    w = (2 * np.polyval(coefficients, (length + 1j * upper) / denom) / denom) / denom + (
        1 / np.sqrt(np.pi)
    ) / denom
    axis = z.real == 0
    with np.errstate(over="ignore", invalid="ignore", under="ignore"):
        if np.any(axis):
            # Keep the domain import light: erfcx is only needed for the
            # positive-imaginary-axis stabilization path.
            from scipy.special import erfcx

            w[axis] = erfcx(upper[axis].imag)
        lower = z.imag < 0
        w[lower] = np.conj(
            2 * np.exp(-(upper[lower].astype(np.clongdouble) ** 2)).astype(complex) - w[lower]
        )
    if not np.all(np.isfinite(w)):
        raise FloatingPointError("Faddeeva continuation exceeds finite float64 range")
    return {"w": w.reshape(shape), "order": n}


def evaluate_faddeeva_gpdf(z, *, order=None):
    """Evaluate the 32-term Faddeeva GPDF response.

    Parameters
    ----------
    z : complex numeric, shape scalar or nonempty array
        Normalized phase points [dimensionless]. Finite after complex128
        conversion; booleans, strings and empty inputs are rejected.
    order : positive integer or None, optional
        Rational truncation order [count]. ``None`` selects the default order
        32. Positive integer only; booleans and nonpositive values are rejected.

    Returns
    -------
    w : ndarray of complex128, shape same as z
        Faddeeva response [dimensionless]. Scalar input produces a
        zero-dimensional array.
    order : int
        Effective truncation order [count].

    Raises
    ------
    ValueError
        If ``z`` is empty, nonnumeric, boolean or nonfinite, or if ``order`` is
        not a positive integer or is outside the supported range.
    FloatingPointError
        If reflection or the rational evaluation is not representable as a
        finite float64 value.

    See Also
    --------
    scirel.kinetic.evaluate_faddeeva_dr : The retained DR variant.
    scirel.kinetic.evaluate_maxwellian_fft : FFT approximation with separate
        scaled-Z failure checking.

    Notes
    -----
    The approximation uses a rational expansion of
    ``w(z)=exp(-z**2) erfc(-iz)``. The truncation order is an algorithm choice,
    not a certified global error bound. Lower-half-plane reflection can
    overflow; that case raises :class:`FloatingPointError` rather than silently
    clamping.

    References
    ----------
    Weideman (1994), Computation of the Complex Error Function,
    doi:10.1137/0731077.
    Xie (2013), Generalized Plasma Dispersion Function, arXiv:1305.6476.

    Examples
    --------
    >>> from scirel.kinetic import evaluate_faddeeva_gpdf
    >>> import numpy as np
    >>> r=evaluate_faddeeva_gpdf(0.2+0.7j)
    >>> assert np.isfinite(r["w"])
    """
    return _evaluate(z, 32 if order is None else _order(order))


def evaluate_faddeeva_dr(z, *, order=None):
    """Evaluate the retained DR Faddeeva response.

    Parameters
    ----------
    z : complex numeric, shape scalar or nonempty array
        Normalized phase points [dimensionless]. Finite after complex128
        conversion; booleans, strings and empty inputs are rejected.
    order : positive integer or None, optional
        Rational truncation order [count]. ``None`` selects the retained default
        order 16. Positive integer only; booleans and nonpositive values are
        rejected.

    Returns
    -------
    w : ndarray of complex128, shape same as z
        Faddeeva response [dimensionless]. Scalar input produces a
        zero-dimensional array.
    order : int
        Effective truncation order [count].

    Raises
    ------
    ValueError
        If ``z`` is empty, nonnumeric, boolean or nonfinite, or if ``order`` is
        not a positive integer or is outside the supported range.
    FloatingPointError
        If reflection or the rational evaluation is not representable as a
        finite float64 value.

    See Also
    --------
    scirel.kinetic.evaluate_faddeeva_gpdf : The default GPDF variant.
    scirel.kinetic.evaluate_plasma_dispersion : Direct SciPy Faddeeva path.

    Notes
    -----
    This is the retained DR approximation, with default order 16. It shares the
    same analytic continuation and finite-representability check as the GPDF
    variant; it does not claim a global truncation-error bound.

    References
    ----------
    Weideman (1994), Computation of the Complex Error Function,
    doi:10.1137/0731077.
    Xie (2013), Generalized Plasma Dispersion Function, arXiv:1305.6476.

    Examples
    --------
    >>> from scirel.kinetic import evaluate_faddeeva_dr
    >>> import numpy as np
    >>> r=evaluate_faddeeva_dr(0.2+0.7j)
    >>> assert np.isfinite(r["w"])
    """
    return _evaluate(z, 16 if order is None else _order(order))


def evaluate_maxwellian_fft(z, *, order=32):
    """Evaluate the FFT rational Maxwellian dispersion response.

    Parameters
    ----------
    z : complex numeric, shape scalar or nonempty array
        Normalized phase points [dimensionless]. Finite after complex128
        conversion; booleans, strings and empty inputs are rejected.
    order : positive integer, default=32
        Rational truncation order [count]. Explicit ``None`` is invalid for
        this function. Positive integer only; booleans are rejected.

    Returns
    -------
    Z : ndarray of complex128, shape same as z
        Maxwellian response ``i sqrt(pi) w(z)`` [dimensionless]. Scalar input
        produces a zero-dimensional array.
    order : int
        Effective truncation order [count].

    Raises
    ------
    ValueError
        If ``z`` is empty, nonnumeric, boolean or nonfinite, or if ``order`` is
        invalid or unsupported.
    FloatingPointError
        If the intermediate ``w`` or the final scaled ``Z`` is not representable
        as finite float64. A finite ``w`` alone does not establish a finite
        ``Z``.

    See Also
    --------
    scirel.kinetic.evaluate_plasma_dispersion : Direct Faddeeva Z function.
    scirel.kinetic.evaluate_maxwellian_jpole : Fixed J-pole approximation.

    Notes
    -----
    The FFT rational expansion is evaluated first and the final
    ``Z=i sqrt(pi) w`` scaling is checked separately. This is a bounded
    approximation; no global error certificate is implied.

    References
    ----------
    Weideman (1994), Computation of the Complex Error Function,
    doi:10.1137/0731077.
    Xie (2013), Generalized Plasma Dispersion Function, arXiv:1305.6476.

    Examples
    --------
    >>> from scirel.kinetic import evaluate_maxwellian_fft
    >>> import numpy as np
    >>> r=evaluate_maxwellian_fft(0.2+0.7j)
    >>> assert np.isfinite(r["Z"])
    """
    result = _evaluate(z, _order(order))
    with np.errstate(over="ignore", invalid="ignore"):
        scaled = 1j * np.sqrt(np.pi) * result["w"]
    if not np.all(np.isfinite(scaled)):
        raise FloatingPointError(
            "Maxwellian FFT response exceeds finite float64 range after scaling"
        )
    return {"Z": scaled, "order": result["order"]}


def evaluate_maxwellian_jpole(z, *, order=8):
    """Evaluate the fixed J-pole Maxwellian dispersion approximation.

    Parameters
    ----------
    z : complex numeric, shape scalar or nonempty array
        Normalized phase points [dimensionless]. Finite after complex128
        conversion; booleans, strings and empty inputs are rejected.
    order : {8, 12, 16, 24}, default=8
        Number of fixed poles [count]. Booleans and other orders are rejected.

    Returns
    -------
    Z : ndarray of complex128, shape same as z
        Maxwellian response [dimensionless]. Scalar input produces a
        zero-dimensional array.
    order : int
        Effective pole count [count].

    Raises
    ------
    ValueError
        If ``z`` is empty, nonnumeric, boolean or nonfinite, or if ``order`` is
        not one of 8, 12, 16 or 24.
    FloatingPointError
        If the continuation or pole sum is not representable as finite
        float64.

    See Also
    --------
    scirel.kinetic.evaluate_maxwellian_fft : FFT rational approximation.
    scirel.kinetic.evaluate_plasma_dispersion : Direct Faddeeva Z function.

    Notes
    -----
    The upper half-plane uses the tabulated partial fraction. Lower-plane
    values use ``Z(z)=conj(Z(conj(z)))+2 i sqrt(pi) exp(-z**2)``. The finite
    pole sum has truncation error; no arbitrary lower-plane accuracy or global
    error bound is implied.

    References
    ----------
    Weideman (1994), Computation of the Complex Error Function,
    doi:10.1137/0731077.
    Xie (2013), Generalized Plasma Dispersion Function, arXiv:1305.6476.

    Examples
    --------
    >>> from scirel.kinetic import evaluate_maxwellian_jpole
    >>> import numpy as np
    >>> r=evaluate_maxwellian_jpole(0.2+0.7j)
    >>> assert np.isfinite(r["Z"])
    """
    n = _order(order)
    if n not in POLES:
        raise ValueError("order must be 8,12,16 or 24")
    a = _input(z)
    bhalf, chalf = POLES[n]
    b = np.r_[bhalf, np.conj(bhalf)]
    c = np.r_[chalf, -np.conj(chalf)]
    upper = np.where(a.imag < 0, np.conj(a), a)
    value = np.sum(b / (upper[..., None] - c), axis=-1)
    with np.errstate(over="ignore", invalid="ignore", under="ignore"):
        value = np.where(
            a.imag < 0,
            np.conj(value)
            + 2j * np.sqrt(np.pi) * np.exp(-(a.astype(np.clongdouble) ** 2)).astype(complex),
            value,
        )
    if not np.all(np.isfinite(value)):
        raise FloatingPointError("J-pole continuation exceeds finite float64 range")
    return {"Z": value, "order": n}
