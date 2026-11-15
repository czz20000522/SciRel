"""Special functions with explicit numerical approximation controls."""

from functools import lru_cache
import operator

import numpy as np

from scirel._validation import finite_complex_array

__all__ = ["evaluate_faddeeva"]

_ASSET = "scirel.numerics.faddeeva"


def _order(value):
    message = (
        f"order must be a positive integer or None; received {value!r}; "
        f"legal values: None or integers >= 1; see {_ASSET}"
    )
    if isinstance(value, (bool, np.bool_)):
        raise TypeError(message)
    try:
        n = operator.index(value)
    except TypeError:
        raise TypeError(message) from None
    if n < 1:
        raise TypeError(message)
    return n


@lru_cache(maxsize=16)
def _coefficients(n):
    m = 2 * n
    length = np.sqrt(n / np.sqrt(2))
    nodes = length * np.tan(np.arange(-m + 1, m) * np.pi / (2 * m))
    samples = np.r_[0.0, np.exp(-(nodes**2)) * (length**2 + nodes**2)]
    coefficients = np.fft.fft(np.fft.fftshift(samples)).real / (2 * m)
    return coefficients[1 : n + 1][::-1], length


def _evaluate(z, n):
    a = finite_complex_array(z, "z", asset_id=_ASSET)
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
        raise FloatingPointError(
            f"w must be finite complex128; received nonfinite results at order={n}; "
            f"legal results: finite w only; see {_ASSET}"
        )
    return w.reshape(shape)


def evaluate_faddeeva(z, *, order=None):
    """Evaluate the tunable rational approximation of Faddeeva ``w(z)``.

    Parameters
    ----------
    z : real or complex numeric array-like, shape scalar or any nonempty array shape
        Complex arguments [dimensionless], evaluated elementwise. All elements
        must be finite after complex128 conversion; masked, boolean, string and
        nonnumeric inputs are rejected.
    order : positive integer or None, optional
        Rational truncation order [count]. ``None`` selects 32; use 16 explicitly
        for the retained lower-order approximation. Any positive integer is
        accepted; booleans are rejected. No global accuracy bound is implied.

    Returns
    -------
    w : complex128 ndarray, shape same as z; scalar input yields a zero-dimensional array
        Approximation of ``exp(-z**2) erfc(-i*z)`` [dimensionless], returned
        directly. Only w must be finite; plasma-dispersion scaling is not computed
        and does not restrict this mathematical function's success domain.

    Raises
    ------
    TypeError
        If z is masked, boolean, string or nonnumeric, or order is not a positive
        integer or None.
    ValueError
        If z is empty, ragged or nonfinite after complex128 conversion.
    FloatingPointError
        If the rational evaluation or continuation produces nonfinite w.

    See Also
    --------
    scipy.special.wofz : Faddeeva function without a truncation-order control.

    Notes
    -----
    FFT-generated coefficients define the rational expansion. Imaginary-axis
    values use erfcx, and lower-plane values retain Gaussian reflection in the
    original arithmetic order. Order 16 and the default 32 retain their distinct
    sampled accuracy budgets; arbitrary positive orders have no certified global
    error bound. Finite input can still give an unrepresentable continuation.

    References
    ----------
    Weideman (1994), Computation of the Complex Error Function,
    doi:10.1137/0731077.
    Xie (2013), Generalized Plasma Dispersion Function, arXiv:1305.6476.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.numerics import evaluate_faddeeva
    >>> w = evaluate_faddeeva(0.2+0.7j)
    >>> w16 = evaluate_faddeeva(0.2+0.7j, order=16)
    >>> assert np.isfinite(w) and np.isfinite(w16)
    """
    return _evaluate(z, 32 if order is None else _order(order))
