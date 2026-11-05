"""Small validated finite-difference operators."""

from __future__ import annotations

import numpy as np

__all__ = ["NumericalContractError", "diff_12_central"]


class NumericalContractError(ValueError):
    """Input violates the supported numerical contract."""


def _validated_pair(x, y):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if x.ndim != 1 or y.ndim != 1 or x.size != y.size or x.size < 3:
        raise NumericalContractError("x and y must be 1-D arrays of equal length >= 3")
    if not np.isfinite(x).all() or not np.isfinite(y).all():
        raise NumericalContractError("x and y must be finite")
    if np.any(np.diff(x) <= 0.0):
        raise NumericalContractError("x must be strictly increasing")
    return x, y


def diff_12_central(x, y):
    r"""Return first and second derivatives at interior points of ``x``.

    Parameters
    ----------
    x : array_like, shape (N,)
        Strictly increasing abscissae [coordinate units]. Values are converted
        to float64 and must be finite, one-dimensional, and contain at least
        three entries; only interior points receive derivative outputs.
    y : array_like, shape (N,)
        Sampled values [value units] at the entries of ``x``. Values are
        converted to float64 and must be finite with the same shape as ``x``.

    Returns
    -------
    d_one : ndarray of float64, shape (N-2,)
        First derivative at the interior abscissae [value per coordinate].
        The three-point unequal-spacing operator is exact for a local
        quadratic.
    d_two : ndarray of float64, shape (N-2,)
        Second derivative at the interior abscissae [value per coordinate
        squared]. The same three-point operator is exact for a local
        quadratic.

    Raises
    ------
    NumericalContractError
        If ``x`` or ``y`` is not a finite one-dimensional pair of equal length
        at least three, or if ``x`` is not strictly increasing. This exception
        is a ValueError subclass.
    TypeError
        If an input contains a value that NumPy cannot convert to float64.
    ValueError
        If NumPy cannot convert an input to a float64 array.

    See Also
    --------
    scirel.geometry.diff_central : Return only the first derivative from this
        operator.

    Notes
    -----
    For interior index ``i``, define ``h_left = x[i] - x[i-1]`` and
    ``h_right = x[i+1] - x[i]``. The returned estimates are

    .. math:: d_1 = \frac{h_L (y_{i+1}-y_i)/h_R + h_R (y_i-y_{i-1})/h_L}{h_L+h_R}

    and

    .. math:: d_2 = 2\left(\frac{y_{i-1}}{h_L(h_L+h_R)} - \frac{y_i}{h_Lh_R} + \frac{y_{i+1}}{h_R(h_L+h_R)}\right).

    No endpoint values are fabricated, and descending coordinates are not
    silently reversed. Nearby abscissae can make the stencil ill-conditioned;
    this function does not regularize the samples or estimate data noise.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.geometry.numerics import diff_12_central
    >>> x = np.array([0.0, 0.3, 1.0])
    >>> first, second = diff_12_central(x, x * x)
    >>> np.testing.assert_allclose(first, [0.6])
    >>> np.testing.assert_allclose(second, [2.0])
    """
    x, y = _validated_pair(x, y)
    h_left = x[1:-1] - x[:-2]
    h_right = x[2:] - x[1:-1]
    first = (h_left * (y[2:] - y[1:-1]) / h_right + h_right * (y[1:-1] - y[:-2]) / h_left) / (
        h_left + h_right
    )
    second = 2.0 * (
        y[:-2] / (h_left * (h_left + h_right))
        - y[1:-1] / (h_left * h_right)
        + y[2:] / (h_right * (h_left + h_right))
    )
    return first, second
