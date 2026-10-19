"""Polynomial and cubic basis evaluators used by SciRel geometry operators.

The spline classes implement piecewise cubic Hermite interpolation.  Knot
slopes are obtained from the declared natural, clamped, or retained
cylindrical boundary equations; evaluation is zero outside the finite knot
interval.  The module intentionally keeps the public selector and failure
contracts of the geometry basis API, while all numerical assembly is local to
SciRel and uses NumPy only.
"""

import numpy as np


def _lazy_special(name):
    """Resolve an optional SciPy special function only when it is called."""

    def _call(*args, **kwargs):
        from scipy import special

        return getattr(special, name)(*args, **kwargs)

    _call.__name__ = name
    _call.__qualname__ = name
    return _call


def _validated_spline_data(x_data, y_data):
    """Return finite, strictly increasing one-dimensional spline samples."""

    try:
        raw_x = np.asarray(x_data)
        raw_y = np.asarray(y_data)
    except (TypeError, ValueError) as exc:
        raise ValueError("spline knots and ordinates must be finite real arrays") from exc

    valid_shape = (
        raw_x.ndim == 1
        and raw_y.ndim == 1
        and raw_x.dtype.kind in "iuf"
        and raw_y.dtype.kind in "iuf"
        and raw_x.size == raw_y.size
        and raw_x.size >= 3
    )
    if not valid_shape:
        raise ValueError(
            "spline knots and ordinates must be finite real one-dimensional arrays "
            "with equal length at least 3"
        )

    x = np.asarray(raw_x, dtype=float)
    y = np.asarray(raw_y, dtype=float)
    if not np.all(np.isfinite(x)) or not np.all(np.isfinite(y)):
        raise ValueError("spline knots and ordinates must be finite")
    if not np.all(np.diff(x) > 0.0):
        raise ValueError("spline knots must be strictly increasing")
    return x, y


def _interior_system(x_step, y_step):
    """Assemble the C2 continuity system for the interior knot slopes."""

    h = np.asarray(x_step, dtype=float)
    delta = np.asarray(y_step, dtype=float)
    n_interior = h.size - 1
    matrix = np.zeros((n_interior, n_interior), dtype=float)
    diagonal = 2.0 * (1.0 / h[:-1] + 1.0 / h[1:])
    np.fill_diagonal(matrix, diagonal)
    if n_interior > 1:
        off_diagonal = 1.0 / h[1:-1]
        matrix[np.arange(n_interior - 1), np.arange(1, n_interior)] = off_diagonal
        matrix[np.arange(1, n_interior), np.arange(n_interior - 1)] = off_diagonal
    rhs = 3.0 * (delta[:-1] / h[:-1] ** 2 + delta[1:] / h[1:] ** 2)
    return matrix, rhs


def _solve_natural_slopes(x_step, y_step):
    """Solve slopes for zero second derivative at both endpoints."""

    h = np.asarray(x_step, dtype=float)
    delta = np.asarray(y_step, dtype=float)
    n = h.size + 1
    matrix = np.zeros((n, n), dtype=float)
    matrix[0, 0] = 2.0 / h[0]
    matrix[0, 1] = 1.0 / h[0]
    matrix[1, 0] = 1.0 / h[0]
    matrix[-1, -2] = 1.0 / h[-1]
    matrix[-1, -1] = 2.0 / h[-1]
    matrix[-2, -1] = 1.0 / h[-1]
    interior, rhs = _interior_system(h, delta)
    matrix[1:-1, 1:-1] = interior
    right_hand_side = np.empty(n, dtype=float)
    right_hand_side[0] = 3.0 * delta[0] / h[0] ** 2
    right_hand_side[-1] = 3.0 * delta[-1] / h[-1] ** 2
    right_hand_side[1:-1] = rhs
    return np.linalg.solve(matrix, right_hand_side)


def _hermite_values(x_value, x_data, y_data, slopes, deriv):
    """Evaluate one Hermite spline for an arbitrary shaped query array."""

    query = np.array(x_value, dtype=float)
    result = np.zeros_like(query)
    inside = (query >= x_data[0]) & (query <= x_data[-1])
    if not np.any(inside):
        return result

    points = np.asarray(query[inside]).reshape(-1)
    interval = np.searchsorted(x_data, points, side="right") - 1
    interval = np.minimum(interval, x_data.size - 2)
    left_x = x_data[interval]
    step = x_data[interval + 1] - left_x
    left_y = y_data[interval]
    right_y = y_data[interval + 1]
    left_slope = slopes[interval]
    right_slope = slopes[interval + 1]
    t = (points - left_x) / step

    # Hermite basis polynomials.  The endpoint forms are exact at t=0 and 1.
    t2 = t * t
    t3 = t2 * t
    h00 = 2.0 * t3 - 3.0 * t2 + 1.0
    h10 = t3 - 2.0 * t2 + t
    h01 = -2.0 * t3 + 3.0 * t2
    h11 = t3 - t2
    if deriv == 1:
        values = (
            (6.0 * t2 - 6.0 * t) * left_y
            + (3.0 * t2 - 4.0 * t + 1.0) * step * left_slope
            + (-6.0 * t2 + 6.0 * t) * right_y
            + (3.0 * t2 - 2.0 * t) * step * right_slope
        ) / step
    elif deriv == 2:
        values = (
            (12.0 * t - 6.0) * left_y
            + (6.0 * t - 4.0) * step * left_slope
            + (-12.0 * t + 6.0) * right_y
            + (6.0 * t - 2.0) * step * right_slope
        ) / step**2
    else:
        values = h00 * left_y + h10 * step * left_slope + h01 * right_y + h11 * step * right_slope
    result[inside] = values
    return result


class spline:
    """Base container for validated one-dimensional spline samples."""

    def __init__(self, x_data, y_data):
        x_data, y_data = _validated_spline_data(x_data, y_data)
        self.x_data = x_data
        self.y_data = y_data
        self.dimension = x_data.size
        self.d_x = np.diff(x_data)
        self.d_y = np.diff(y_data)

    def __call__(self, x_value, deriv=0):
        return self._interpolate(x_value, deriv)

    def _interpolate(self, x_value, deriv=0):
        return


class CubicSpline(spline):
    """Base class for cubic Hermite spline evaluators."""

    def __init__(self, x_data, y_data):
        spline.__init__(self, x_data, y_data)

    def _interpolate(self, x_value, deriv=0):
        return _hermite_values(x_value, self.x_data, self.y_data, self.k, deriv)


class NaturalCubicSpline(CubicSpline):
    """Construct a natural cubic Hermite spline.

    Parameters
    ----------
    x_data : array_like, shape (N,)
        Finite, strictly increasing interpolation knots with ``N >= 3``.
    y_data : array_like, shape (N,)
        Finite ordinates matched to ``x_data``.

    Returns
    -------
    NaturalCubicSpline
        Callable spline retaining the validated data and solved knot slopes.
        Query arrays preserve their shape; values outside the knot interval
        are zero.

    Raises
    ------
    ValueError
        If the knot or ordinate arrays are nonfinite, unsorted, mismatched or
        shorter than the supported minimum.
    numpy.linalg.LinAlgError
        If the natural boundary slope system cannot be solved.

    Notes
    -----
    ``deriv=1`` and ``deriv=2`` select derivative evaluations.  Other
    selectors retain the value-evaluation compatibility behavior.
    """

    def __init__(self, x_data, y_data):
        CubicSpline.__init__(self, x_data, y_data)
        self.k = _solve_natural_slopes(self.d_x, self.d_y)


class ClampedCubicSpline(CubicSpline):
    """Construct a cubic spline with prescribed endpoint slopes.

    Parameters
    ----------
    x_data : array_like, shape (N,)
        Finite, strictly increasing interpolation knots with ``N >= 3``.
    y_data : array_like, shape (N,)
        Finite ordinates matched to ``x_data``.
    yp : array_like, shape (2,), default=[0, 0]
        Left and right endpoint first derivatives.

    Returns
    -------
    ClampedCubicSpline
        Callable spline retaining the validated data and solved knot slopes.
        Query arrays preserve their shape; values outside the knot interval
        are zero.

    Raises
    ------
    AssertionError
        If ``yp`` does not contain exactly two endpoint slopes.
    ValueError
        If the knot or ordinate arrays are nonfinite, unsorted, mismatched or
        shorter than the supported minimum.
    numpy.linalg.LinAlgError
        If the clamped boundary slope system cannot be solved.

    Notes
    -----
    ``deriv=1`` and ``deriv=2`` select derivative evaluations.  Other
    selectors retain the value-evaluation compatibility behavior.
    """

    def __init__(self, x_data, y_data, yp=[0, 0]):
        CubicSpline.__init__(self, x_data, y_data)
        assert len(yp) == 2, "yp must be a vector of length 2"
        interior, rhs = _interior_system(self.d_x, self.d_y)
        rhs = rhs.copy()
        rhs[0] -= yp[0] / self.d_x[0]
        rhs[-1] -= yp[-1] / self.d_x[-1]
        interior_slopes = np.linalg.solve(interior, rhs)
        self.k = np.empty(self.dimension, dtype=float)
        self.k[0] = yp[0]
        self.k[-1] = yp[-1]
        self.k[1:-1] = interior_slopes


class FirstClampedCubicSpline(CubicSpline):
    """Construct the retained left-clamped cylindrical spline.

    Parameters
    ----------
    x_data : array_like, shape (N,)
        Finite, strictly increasing knots with ``N >= 3``.
    y_data : array_like, shape (N,)
        Finite ordinates matched to ``x_data``.
    yp : float, default=0
        Prescribed first derivative at the left endpoint.
    m : float, default=0
        Coefficient in the retained right-hand Robin row.  No physical mode
        interpretation is asserted by this API.

    Returns
    -------
    FirstClampedCubicSpline
        Callable spline retaining the solved knot slopes.  Query arrays
        preserve their shape; values outside the knot interval are zero.

    Raises
    ------
    ValueError
        If the knots or ordinates violate the finite, increasing and matched
        input contract.
    numpy.linalg.LinAlgError
        If the left-clamped/Robin slope system cannot be solved.

    Notes
    -----
    The qualified domain includes ``x_data[-1] > 0`` and in-domain
    ``deriv=0/1/2``.  Other derivative selectors retain source behavior.
    The cylindrical boundary interpretation remains an implementation
    convention rather than a physical qualification.
    """

    def __init__(self, x_data, y_data, yp=0, m=0):
        CubicSpline.__init__(self, x_data, y_data)
        h = self.d_x
        delta = self.d_y
        x_last = self.x_data[-1]
        y_last = self.y_data[-1]
        n_unknown = self.dimension - 1
        matrix = np.zeros((n_unknown, n_unknown), dtype=float)
        interior, rhs = _interior_system(h, delta)
        matrix[:-1, :-1] = interior
        matrix[-2, -1] = 1.0 / h[-1]
        matrix[-1, -2] = 2.0 / h[-1]
        matrix[-1, -1] = 4.0 / h[-1] + 1.0 / x_last
        right_hand_side = np.empty(n_unknown, dtype=float)
        right_hand_side[:-1] = rhs
        right_hand_side[-1] = 6.0 * delta[-1] / h[-1] ** 2 + m**2 * y_last / x_last**2
        right_hand_side[0] -= yp / h[0]
        solved = np.linalg.solve(matrix, right_hand_side)
        self.k = np.empty(self.dimension, dtype=float)
        self.k[0] = yp
        self.k[1:] = solved


class SecondClampedCubicSpline(CubicSpline):
    """Construct the retained origin-natural cylindrical spline.

    Parameters
    ----------
    x_data : array_like, shape (N,)
        Finite, strictly increasing knots with ``N >= 3`` and
        ``x_data[0] == 0``.
    y_data : array_like, shape (N,)
        Finite ordinates matched to ``x_data`` with ``y_data[0] == 0``.
    m : float, default=1
        Coefficient in the retained right-hand Robin row.  No physical mode
        interpretation is asserted by this API.

    Returns
    -------
    SecondClampedCubicSpline
        Callable spline retaining the solved knot slopes.  Query arrays
        preserve their shape; values outside the knot interval are zero.

    Raises
    ------
    ValueError
        If the knots or ordinates violate the finite, increasing, matched
        input contract.
    numpy.linalg.LinAlgError
        If the origin/Robin slope system cannot be solved.

    Notes
    -----
    The qualified domain includes ``x_data[-1] > 0`` and in-domain
    ``deriv=0/1/2``.  Other derivative selectors retain source behavior.
    The boundary row is not a natural boundary for arbitrary nonzero origin
    data and does not establish a physical cylindrical fitting model.
    """

    def __init__(self, x_data, y_data, m=1):
        CubicSpline.__init__(self, x_data, y_data)
        h = self.d_x
        delta = self.d_y
        x_last = self.x_data[-1]
        y_last = self.y_data[-1]
        n = self.dimension
        matrix = np.zeros((n, n), dtype=float)
        interior, rhs = _interior_system(h, delta)
        matrix[1:-1, 1:-1] = interior
        matrix[0, 0] = 2.0
        matrix[0, 1] = 1.0
        matrix[1, 0] = 1.0 / h[0]
        matrix[-2, -1] = 1.0 / h[-1]
        matrix[-1, -2] = 2.0 / h[-1]
        matrix[-1, -1] = 4.0 / h[-1] + 1.0 / x_last
        right_hand_side = np.zeros(n, dtype=float)
        right_hand_side[1:-1] = rhs
        right_hand_side[0] = 3.0 * self.y_data[1] / self.x_data[1]
        right_hand_side[-1] = (
            6.0 * delta[-1] / h[-1] ** 2 + m**2 * y_last / x_last**2
        )
        self.k = np.linalg.solve(matrix, right_hand_side)


class QuarticSpline(spline):
    """Placeholder for the explicitly unsupported quartic selector."""

    def __init__(self, x_data, y_data):
        raise NotImplementedError("Upstream quartic spline coefficient construction is incomplete")


basis_map = {
    "natural_cubic_spline": NaturalCubicSpline,
    "clamped_cubic_spline": ClampedCubicSpline,
    "clamped_cubic_spline1": FirstClampedCubicSpline,
    "clamped_cubic_spline2": SecondClampedCubicSpline,
    "quartic_spline": QuarticSpline,
    "poly": np.polynomial.polynomial.Polynomial,
    "j0": _lazy_special("j0"),
    "j1": _lazy_special("j1"),
    "y0": _lazy_special("y0"),
    "y1": _lazy_special("y1"),
    "i0": _lazy_special("i0"),
    "i1": _lazy_special("i1"),
    "k0": _lazy_special("k0"),
    "k1": _lazy_special("k1"),
}


def build_basis(basis="poly", **kwargs):
    """Construct the selected polynomial or retained cubic-spline basis.

    Parameters
    ----------
    basis : str, default='poly'
        Case-insensitive selector.  Supported selectors include ``poly`` and
        the retained natural, clamped, first-clamped and second-clamped cubic
        splines.
    **kwargs
        Basis-specific options such as ``poly_deg``/``coeffs`` for polynomial
        bases or ``n_knots``, ``domain``, ``xdata`` and ``ydata`` for splines.

    Returns
    -------
    list of callable
        Independent basis evaluators in their declared column order.

    Raises
    ------
    KeyError
        If ``basis`` is not a registered selector.
    TypeError
        If a basis-specific keyword is unknown.
    NotImplementedError
        If a retained selector such as the quartic or special-function path
        has no supported basis construction in this package.
    """

    basis = basis.lower()
    basis_fn = basis_map[basis]
    if basis == "poly":
        return _poly_basis(**kwargs)
    if "spline" in basis:
        return _spline_basis(basis_fn, **kwargs)
    raise NotImplementedError


def _poly_basis(**kwargs):
    poly_deg = kwargs.pop("poly_deg", 3)
    coeffs = kwargs.pop("coeffs", None)
    if kwargs:
        unknown = ", ".join(sorted(kwargs))
        raise TypeError(f"build_basis() got unexpected keyword argument(s): {unknown}")
    if coeffs is None:
        coeffs = np.eye(poly_deg)
    return [np.polynomial.polynomial.Polynomial(coeffs[:, i]) for i in range(coeffs.shape[1])]


def _spline_basis(spline_fn, **kwargs):
    n_knots = kwargs.pop("n_knots", 5)
    domain = tuple(kwargs.pop("domain", (0, 1)))
    xdata = kwargs.pop("xdata", None)
    ydata = kwargs.pop("ydata", None)
    if xdata is None:
        xdata = np.linspace(domain[0], domain[1], n_knots)
    if ydata is None:
        ydata = np.eye(n_knots)
    if len(xdata.squeeze().shape) == 1:
        xdata = xdata.squeeze()
        return [spline_fn(xdata, ydata[:, i], **kwargs) for i in range(ydata.shape[1])]
    return [spline_fn(xdata[:, i], ydata[:, i], **kwargs) for i in range(ydata.shape[1])]


class BasisMatrix(object):
    """Evaluate a selected basis as columns of a design matrix.

    Parameters
    ----------
    basis : str
        Case-insensitive selector passed to :func:`build_basis`.
    **kwargs
        Basis-specific construction options.  Polynomial bases accept
        ``poly_deg`` and ``coeffs``; spline bases accept their knot/domain
        options and boundary parameters.

    Attributes
    ----------
    basis_fns : list of callable
        The retained basis evaluators in column order.
    basis_dim : int
        Number of columns produced for each one-dimensional domain.

    Returns
    -------
    BasisMatrix
        A callable object whose ``matrix(domain)`` result has shape
        ``(len(domain), basis_dim)``.

    Raises
    ------
    KeyError, TypeError, ValueError, NotImplementedError
        Exceptions from the selected :func:`build_basis` path propagate for
        unknown selectors, unsupported options or invalid basis data.
    """

    def __init__(self, basis, **kwargs):
        self._basis_fns = build_basis(basis=basis, **kwargs)
        self._basis_dim = len(self._basis_fns)

    @property
    def basis_fns(self):
        return self._basis_fns

    @property
    def basis_dim(self):
        return self._basis_dim

    def __call__(self, domain, **kwargs):
        result = np.zeros((len(domain), self._basis_dim))
        for index, fn in enumerate(self._basis_fns):
            result[:, index] = fn(domain, **kwargs)
        return result


__all__ = [
    "NaturalCubicSpline",
    "ClampedCubicSpline",
    "FirstClampedCubicSpline",
    "SecondClampedCubicSpline",
    "build_basis",
    "BasisMatrix",
]
