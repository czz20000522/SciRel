"""Polynomial and cubic basis evaluators used by SciRel geometry operators.

The spline classes implement piecewise cubic Hermite interpolation.  Knot
slopes are obtained from the declared natural, clamped, or retained
cylindrical boundary equations.  Finite queries outside the closed knot
interval are zero-filled exactly, and nonfinite query values use the same
convention.  The module intentionally keeps the public selector and failure
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
    """Natural cubic spline

    Parameters
    ----------
    x_data : float64
        Interpolation knots [coordinate units] Shape: ``(N,)``. Finite strictly increasing
        N>=3

    y_data : float64
        Ordinate samples [ordinate units] Shape: ``(N,)``. Finite, same N as x_data

    Returns
    -------
    spline : Python callable object
        Callable spline retaining x_data,y_data,k and deriv=0/1/2 evaluation [ordinate
        units; derivative units per coordinate power] Shape: ``object``. Query array shape
        preserved; finite values outside the closed knot interval return zero; nonfinite
        queries are zero-filled

    Raises
    ------
    ValueError
        Raises ValueError or AssertionError for unsupported basis selectors, nonfinite or mismatched samples, unsorted knots, or invalid boundary parameters;

    See Also
    --------
    ClampedCubicSpline : Clamped cubic spline.
    FirstClampedCubicSpline : Left-clamped cylindrical spline.
    SecondClampedCubicSpline : Origin-natural cylindrical spline.

    Notes
    -----
    Piecewise cubic Hermite interpolation with a boundary-specific linear slope system.
    ``deriv=1`` returns the first derivative and ``deriv=2`` the second; finite
    queries outside the knot interval return zero.

    **Coordinates.** Knots in arbitrary coherent coordinate units

    **Boundary.** Second derivatives vanish at both ends

    **Preconditions.**

    * Finite strictly increasing matched one-dimensional knots and values with N>=3
    * In-domain deriv=0/1/2 for the qualified numerical claim
    * For spline selections, finite queries outside the closed knot interval and
      nonfinite query values use the zero-fill convention

    **Limits.**

    * Zero extrapolation and deriv selectors other than 1/2 returning values remain
      compatibility conventions
    * Duplicate, unsorted or nonfinite knots are outside numerical qualification
    * For spline selections, nonfinite query values are outside the numerical
      qualification; the implementation zero-fills them as a compatibility
      convention. Polynomial selections do not zero-fill them.
    * Knot-interval membership is exact; a point one representable step outside returns zero

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.geometry.basis import NaturalCubicSpline
    >>> spline = NaturalCubicSpline(np.array([0.0, 0.3, 1.0]), np.array([0.0, 0.2, 1.0]))
    >>> np.testing.assert_allclose(spline(np.array([0.3])), [0.2])
    """

    def __init__(self, x_data, y_data):
        CubicSpline.__init__(self, x_data, y_data)
        self.k = _solve_natural_slopes(self.d_x, self.d_y)


class ClampedCubicSpline(CubicSpline):
    """Clamped cubic spline

    Parameters
    ----------
    x_data : float64
        Interpolation knots [coordinate units] Shape: ``(N,)``. Finite strictly increasing
        N>=3

    y_data : float64
        Ordinate samples [ordinate units] Shape: ``(N,)``. Finite, same N as x_data

    yp : float64, optional
        Left/right endpoint slopes [ordinate per coordinate] Shape: ``(2,)``. Finite two
        slopes Optional; default ``[0, 0]``.

    Returns
    -------
    spline : Python callable object
        Callable spline retaining x_data,y_data,k and deriv=0/1/2 evaluation [ordinate
        units; derivative units per coordinate power] Shape: ``object``. Query array shape
        preserved; finite values outside the closed knot interval return zero; nonfinite
        queries are zero-filled

    Raises
    ------
    ValueError
        Raises ValueError or AssertionError for unsupported basis selectors, nonfinite or mismatched samples, unsorted knots, or invalid boundary parameters;

    See Also
    --------
    NaturalCubicSpline : Natural cubic spline.
    FirstClampedCubicSpline : Left-clamped cylindrical spline.
    SecondClampedCubicSpline : Origin-natural cylindrical spline.

    Notes
    -----
    Piecewise cubic Hermite interpolation with a boundary-specific linear slope system.
    ``yp`` supplies both endpoint slopes: ``yp[0]`` for the left boundary and
    ``yp[-1]`` for the right boundary. These are numerical derivative constraints,
    not a physical qualification of the model.

    **Coordinates.** Knots in arbitrary coherent coordinate units

    **Boundary.** Specified first derivatives at both ends

    **Preconditions.**

    * Finite strictly increasing matched one-dimensional knots and values with N>=3
    * In-domain deriv=0/1/2 for the qualified numerical claim
    * For spline selections, finite queries outside the closed knot interval and
      nonfinite query values use the zero-fill convention

    **Limits.**

    * Zero extrapolation and deriv selectors other than 1/2 returning values remain
      compatibility conventions
    * Duplicate, unsorted or nonfinite knots are outside numerical qualification
    * For spline selections, nonfinite query values are outside the numerical
      qualification; the implementation zero-fills them as a compatibility
      convention. Polynomial selections do not zero-fill them.
    * Knot-interval membership is exact; a point one representable step outside returns zero

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.geometry.basis import ClampedCubicSpline
    >>> x = np.array([0.0, 0.3, 1.0])
    >>> y = np.array([0.0, 0.2, 1.0])
    >>> spline = ClampedCubicSpline(x, y)
    >>> np.testing.assert_allclose(spline(np.array([0.3])), [0.2])
    """

    def __init__(self, x_data, y_data, yp=(0, 0)):
        CubicSpline.__init__(self, x_data, y_data)
        assert len(yp) == 2, "yp must be a vector of length 2"
        if not np.all(np.isfinite(yp)):
            raise ValueError("yp must contain finite endpoint slopes")
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
    """Left-clamped cylindrical spline

    Parameters
    ----------
    x_data : float64
        Interpolation knots [coordinate units] Shape: ``(N,)``. Finite strictly increasing
        N>=3; x_data[-1] must be positive

    y_data : float64
        Ordinate samples [ordinate units] Shape: ``(N,)``. Finite, same N as x_data

    yp : float64, optional
        Left endpoint slope [ordinate per coordinate] Shape: ``scalar``. Finite Optional;
        default ``0``.

    m : float64, optional
        Coefficient in the cylindrical Robin row [dimensionless] Shape: ``scalar``. Finite;
        no physical mode interpretation asserted Optional; default ``0``.

    Returns
    -------
    spline : Python callable object
        Callable spline retaining x_data,y_data,k and deriv=0/1/2 evaluation [ordinate
        units; derivative units per coordinate power] Shape: ``object``. Query array shape
        preserved; finite values outside the closed knot interval return zero; nonfinite
        queries are zero-filled

    Raises
    ------
    ValueError
        Raises ValueError or AssertionError for unsupported basis selectors, nonfinite or mismatched samples, unsorted knots, or invalid boundary parameters; a nonpositive last knot x_data[-1] is rejected with ValueError before the boundary system is assembled;

    See Also
    --------
    NaturalCubicSpline : Natural cubic spline.
    ClampedCubicSpline : Clamped cubic spline.
    SecondClampedCubicSpline : Origin-natural cylindrical spline.

    Notes
    -----
    Piecewise cubic Hermite interpolation with a boundary-specific linear slope system.
    ``yp`` sets the left endpoint slope and the retained right boundary row is a
    numerical convention, not a physical qualification of the cylindrical model.

    **Coordinates.** Knots in arbitrary coherent coordinate units

    **Boundary.** Left first derivative yp and right fdd+fd/x-m^2 f/x^2=0; x_data[-1]>0

    **Preconditions.**

    * Finite strictly increasing matched one-dimensional knots and values with N>=3
    * In-domain deriv=0/1/2 for the qualified numerical claim
    * x_data[-1]>0; a nonpositive last knot is rejected with ValueError before boundary
      assembly
    * For spline selections, finite queries outside the closed knot interval and
      nonfinite query values use the zero-fill convention

    **Limits.**

    * Zero extrapolation and deriv selectors other than 1/2 returning values remain
      compatibility conventions
    * Duplicate, unsorted or nonfinite knots are outside numerical qualification
    * Physical cylindrical magnetic-fitting boundary interpretation remains unresolved
    * For spline selections, nonfinite query values are outside the numerical
      qualification; the implementation zero-fills them as a compatibility
      convention. Polynomial selections do not zero-fill them.
    * Knot-interval membership is exact; a point one representable step outside returns zero

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.geometry.basis import FirstClampedCubicSpline
    >>> spline = FirstClampedCubicSpline(np.array([0.0, 0.3, 1.0]), np.array([0.0, 0.2, 1.0]))
    >>> np.testing.assert_allclose(spline(np.array([0.3])), [0.2])
    """

    def __init__(self, x_data, y_data, yp=0, m=0):
        CubicSpline.__init__(self, x_data, y_data)
        if not np.isfinite(yp) or not np.isfinite(m):
            raise ValueError("yp and m must be finite")
        if not self.x_data[-1] > 0.0:
            raise ValueError(
                "x_data[-1] must be positive: the cylindrical Robin boundary "
                "divides by the last knot"
            )
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
    """Origin-natural cylindrical spline

    Parameters
    ----------
    x_data : float64
        Interpolation knots [coordinate units] Shape: ``(N,)``. Finite strictly increasing
        N>=3; x_data[0] must be 0 and x_data[-1] positive

    y_data : float64
        Ordinate samples [ordinate units] Shape: ``(N,)``. Finite, same N as x_data;
        y_data[0] must be 0

    m : float64, optional
        Coefficient in the cylindrical Robin row [dimensionless] Shape: ``scalar``. Finite;
        no physical mode interpretation asserted Optional; default ``1``.

    Returns
    -------
    spline : Python callable object
        Callable spline retaining x_data,y_data,k and deriv=0/1/2 evaluation [ordinate
        units; derivative units per coordinate power] Shape: ``object``. Query array shape
        preserved; finite values outside the closed knot interval return zero; nonfinite
        queries are zero-filled

    Raises
    ------
    ValueError
        Raises ValueError or AssertionError for unsupported basis selectors, nonfinite or mismatched samples, unsorted knots, or invalid boundary parameters;

    See Also
    --------
    NaturalCubicSpline : Natural cubic spline.
    ClampedCubicSpline : Clamped cubic spline.
    FirstClampedCubicSpline : Left-clamped cylindrical spline.

    Notes
    -----
    Piecewise cubic Hermite interpolation with a boundary-specific linear slope system.
    The origin row requires ``x_data[0] == 0`` and the retained right boundary row is
    a numerical convention, not a physical cylindrical qualification.

    **Coordinates.** Knots in arbitrary coherent coordinate units

    **Boundary.** Origin row and right fdd+fd/x-m²f/x²=0

    **Preconditions.**

    * Finite strictly increasing matched one-dimensional knots and values with N>=3
    * In-domain deriv=0/1/2 for the qualified numerical claim
    * x_data[0]=y_data[0]=0 and x_data[-1]>0
    * The origin ordinate y_data[0] must be exactly zero
    * For spline selections, finite queries outside the closed knot interval and
      nonfinite query values use the zero-fill convention

    **Limits.**

    * Zero extrapolation and deriv selectors other than 1/2 returning values remain
      compatibility conventions
    * Duplicate, unsorted or nonfinite knots are outside numerical qualification
    * Physical cylindrical magnetic-fitting boundary interpretation remains unresolved
    * For spline selections, nonfinite query values are outside the numerical
      qualification; the implementation zero-fills them as a compatibility
      convention. Polynomial selections do not zero-fill them.
    * Knot-interval membership is exact; a point one representable step outside returns zero
    * Nonzero origin ordinates are rejected rather than silently ignored
    * The retained origin row is not a physical cylindrical fitting model

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.geometry.basis import SecondClampedCubicSpline
    >>> spline = SecondClampedCubicSpline(np.array([0.0, 0.3, 1.0]), np.array([0.0, 0.2, 1.0]))
    >>> np.testing.assert_allclose(spline(np.array([0.3])), [0.2])
    """

    def __init__(self, x_data, y_data, m=1):
        CubicSpline.__init__(self, x_data, y_data)
        if self.x_data[0] != 0.0 or not self.x_data[-1] > 0.0:
            raise ValueError("x_data must start at 0 and end above 0")
        if self.y_data[0] != 0.0:
            raise ValueError("y_data[0] must be 0 for the origin-natural boundary")
        if not np.isfinite(m):
            raise ValueError("m must be finite")
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
        right_hand_side[-1] = 6.0 * delta[-1] / h[-1] ** 2 + m**2 * y_last / x_last**2
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
    """Basis evaluator factory

    Parameters
    ----------
    basis : str, optional
        Basis selector [dimensionless] Shape: ``string``. poly or cubic-spline selector;
        lowercased Optional; default ``'poly'``.

    **kwargs : keyword arguments, optional
        Basis-specific controls such as ``poly_deg``, ``n_knots``, ``domain``, ``xdata``,
        ``ydata``, and ``yp``.

    Returns
    -------
    basis_fns : list
        List of independent basis evaluators [caller units] Shape: ``list(K)``. Polynomial
        or spline callables; spline callables zero-fill finite values outside the closed
        knot interval and nonfinite queries

    Raises
    ------
    ValueError
        If spline samples, knots, or boundary parameters are invalid, or if a
        clamped basis requests nonzero endpoint slopes.
    TypeError
        If an unknown keyword is supplied or a control has an incompatible type.
    KeyError
        If the basis selector is not registered.
    NotImplementedError
        If a retained basis selector is not implemented.

    See Also
    --------
    BasisMatrix : Basis design matrix.
    NaturalCubicSpline : Natural cubic spline.
    ClampedCubicSpline : Clamped cubic spline.

    Notes
    -----
    Construct a list of ascending-power polynomial or cubic-spline evaluators

    **Coordinates.** Generic coordinate and ordinate units

    **Boundary.** Spline evaluation is zero outside the finite knot interval; no
    extrapolation is performed. Polynomial evaluation continues outside the
    construction domain and does not apply this zero-fill convention.

    **Preconditions.**

    * Finite constructor samples and boundary-specific assumptions
    * Polynomial coefficients are ascending-power columns; poly_deg default3 means three
      basis functions
    * Spline keyword defaults n_knots=5,domain=(0,1); xdata/ydata supplied arrays must match
    * Clamped spline bases require yp=0; nonzero slopes define an affine family, not a
      linear basis
    * The second-clamped default basis omits the origin identity column and therefore has
      n_knots-1 columns
    * Spline basis construction requires n_knots>=3
    * For spline selections, finite queries outside the closed knot interval and
      nonfinite query values use the zero-fill convention

    **Limits.**

    * Quartic and special-function factory selections are rejected; no invented
      implementations
    * Physical special-spline closures and unsupported knot domains remain unresolved
    * Nonzero endpoint slopes for clamped basis construction are rejected
    * For spline selections, nonfinite query values are outside the numerical
      qualification; the implementation zero-fills them as a compatibility
      convention. Polynomial selections do not zero-fill them.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.geometry.basis import build_basis
    >>> evaluators = build_basis()
    >>> assert len(evaluators) == 3
    >>> np.testing.assert_allclose([fn(0.5) for fn in evaluators], [1.0, 0.5, 0.25])
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
    if spline_fn is ClampedCubicSpline:
        yp = np.asarray(kwargs["yp"] if "yp" in kwargs else (0.0, 0.0), dtype=float)
        if np.any(yp != 0.0):
            raise ValueError(
                "clamped spline basis requires yp=0 (zero endpoint slopes); nonzero slopes make an affine family"
            )
    elif spline_fn is FirstClampedCubicSpline:
        yp = np.asarray(kwargs["yp"] if "yp" in kwargs else 0.0, dtype=float)
        if np.any(yp != 0.0):
            raise ValueError(
                "clamped spline basis requires yp=0 (zero endpoint slopes); nonzero slopes make an affine family"
            )
    n_knots = kwargs.pop("n_knots", 5)
    if n_knots < 3:
        raise ValueError("n_knots must be at least 3 for spline basis construction")
    domain = tuple(kwargs.pop("domain", (0, 1)))
    xdata = kwargs.pop("xdata", None)
    ydata = kwargs.pop("ydata", None)
    if xdata is None:
        xdata = np.linspace(domain[0], domain[1], n_knots)
    if ydata is None:
        ydata = np.eye(n_knots)
        if spline_fn is SecondClampedCubicSpline:
            # The origin boundary is homogeneous.  The first identity column
            # has y_data[0] == 1 and therefore cannot belong to this basis.
            ydata = ydata[:, 1:]
    if len(xdata.squeeze().shape) == 1:
        xdata = xdata.squeeze()
        return [spline_fn(xdata, ydata[:, i], **kwargs) for i in range(ydata.shape[1])]
    return [spline_fn(xdata[:, i], ydata[:, i], **kwargs) for i in range(ydata.shape[1])]


class BasisMatrix(object):
    """Basis design matrix

    Parameters
    ----------
    basis : str
        Basis selector [dimensionless] Shape: ``string``. As build_basis

    **kwargs : keyword arguments, optional
        Forwarded to :func:`build_basis`; the accepted keys depend on the selected basis.

    Returns
    -------
    matrix : Python callable object
        Evaluator yielding matrix of basis values [basis-value units] Shape: ``(M,K)``.
        Caller provides a one-dimensional domain; K follows the selected basis.
        Spline selections zero-fill finite domain-outside and nonfinite query
        rows; polynomial selections evaluate the polynomials directly.

    Attributes
    ----------
    basis_fns : list of callable
        Independent basis evaluators in column order [basis-value units].
    basis_dim : int
        Number of basis columns [dimensionless].

    Raises
    ------
    ValueError
        If spline samples, knots, or boundary parameters are invalid, or if a
        clamped basis requests nonzero endpoint slopes.
    TypeError
        If an unknown keyword is supplied or a control has an incompatible type.
    KeyError
        If the basis selector is not registered.
    NotImplementedError
        If a retained basis selector is not implemented.

    See Also
    --------
    build_basis : Basis evaluator factory.
    scirel.geometry : Geometry namespace

    Notes
    -----
    Evaluate selected basis functions into columns of a design matrix

    **Coordinates.** Rows follow input domain; columns follow basis order

    **Boundary.** Spline evaluation is zero outside the finite knot interval; no
    extrapolation is performed. Polynomial evaluation continues outside the
    construction domain and does not apply this zero-fill convention.

    **Preconditions.**

    * Finite constructor samples and boundary-specific assumptions
    * Polynomial coefficients are ascending-power columns; poly_deg default3 means three
      basis functions
    * Spline keyword defaults n_knots=5,domain=(0,1); xdata/ydata supplied arrays must match
    * Clamped spline bases require yp=0; nonzero slopes define an affine family, not a
      linear basis
    * The second-clamped default basis has n_knots-1 columns because y_data[0] is fixed to
      zero
    * Spline basis construction requires n_knots>=3
    * For spline selections, finite queries outside the closed knot interval and
      nonfinite query values use the zero-fill convention

    **Limits.**

    * Quartic and special-function factory selections are rejected; no invented
      implementations
    * Physical special-spline closures and unsupported knot domains remain unresolved
    * Nonzero endpoint slopes for clamped basis construction are rejected
    * For spline selections, nonfinite query values are outside the numerical
      qualification; the implementation zero-fills them as a compatibility
      convention. Polynomial selections do not zero-fill them.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.geometry.basis import BasisMatrix
    >>> samples = np.array([0.0, 1.0])
    >>> matrix = BasisMatrix("poly")(samples)
    >>> np.testing.assert_allclose(matrix, [[1.0, 0.0, 0.0], [1.0, 1.0, 1.0]])
    """

    def __init__(self, basis, **kwargs):
        self._basis_fns = build_basis(basis=basis, **kwargs)
        self._basis_dim = len(self._basis_fns)

    @property
    def basis_fns(self):
        """Return the ordered list of independent basis evaluators."""
        return self._basis_fns

    @property
    def basis_dim(self):
        """Return the number of basis columns produced by the evaluator."""
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
