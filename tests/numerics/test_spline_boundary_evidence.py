"""Independent evidence for the four public cubic-spline boundary families.

Assets: ``scirel.numerics.natural-cubic-spline``,
``scirel.numerics.clamped-cubic-spline``,
``scirel.numerics.first-clamped-cubic-spline``,
``scirel.numerics.second-clamped-cubic-spline``.

Evidence, and why each source is independent of the implementation under test
and of its original regression fixtures:

1. **Analytic identities of cubic Hermite interpolation.**  A piecewise cubic
   interpolant is fixed by its knot ordinates and knot slopes; it interpolates
   the nodes, is C2 across interior knots, and reproduces any cubic exactly when
   its knot slopes equal that cubic's derivative.  These are properties of the
   form, checked here from the public ``x_data``/``y_data``/``k`` attributes
   without calling the evaluator's slope solver.
2. **Declared boundary conditions.**  ``NaturalCubicSpline`` states zero second
   derivative at both ends; ``ClampedCubicSpline`` states end slopes ``yp``;
   ``FirstClampedCubicSpline`` states left slope ``yp`` and the cylindrical row
   ``f'' + f'/x - m^2 f/x^2 = 0`` at the last knot; ``SecondClampedCubicSpline``
   states that row plus an origin row that fixes ``x_data[0] = y_data[0] = 0``.
   Each is evaluated on the produced spline, not re-derived from the code.
3. **Independent reference implementation.**  SciPy ``CubicSpline`` solves for
   knot *second derivatives* through a different system and different code, so
   agreement on values and on both derivative orders is a genuine cross-check
   for the two families that have a SciPy equivalent (``bc_type='natural'`` and
   two first-derivative ends).  The two cylindrical families have no SciPy
   counterpart; they rest on 1 and 2 only.
4. **Truncation budget, fixed before measurement.**  A cubic spline interpolating
   a C4 function on a uniform grid has an O(h^4) error.  The test fixes the
   expected refinement ratio at 16 and accepts 10..22 for a 4x error drop plus
   floating-point floor; it never widens a tolerance after seeing the value.

Residual tolerances are expressed in units of ``eps * scale`` with the scale
named at each assertion, so a failure reports how far the identity is violated
relative to binary64 resolution rather than against an arbitrary threshold.
"""

from __future__ import annotations

import numpy as np
import pytest
from scipy.interpolate import CubicSpline

from scirel.numerics import (
    ClampedCubicSpline,
    FirstClampedCubicSpline,
    NaturalCubicSpline,
    SecondClampedCubicSpline,
)

EPS = np.finfo(float).eps


def _hermite_second_derivative_at_left(x, y, k, index):
    """S'' at the left end of interval ``index``, from the Hermite form."""
    h = x[index + 1] - x[index]
    return (
        -6.0 * y[index] - 4.0 * h * k[index] + 6.0 * y[index + 1] - 2.0 * h * k[index + 1]
    ) / h**2


def _hermite_second_derivative_at_right(x, y, k, index):
    """S'' at the right end of interval ``index``, from the Hermite form."""
    h = x[index + 1] - x[index]
    return (
        6.0 * y[index] + 2.0 * h * k[index] - 6.0 * y[index + 1] + 4.0 * h * k[index + 1]
    ) / h**2


# A nonuniform knot set keeps the tests off the uniform-spacing special case.
X = np.array([0.0, 0.4, 1.5, 2.2, 3.0])
Y = np.array([0.0, 1.3, -0.4, 0.8, 2.1])
X0 = np.array([0.0, 0.3, 1.0])
Y0 = np.array([0.0, 0.2, 1.0])


def _families():
    return [
        NaturalCubicSpline(X, Y),
        ClampedCubicSpline(X, Y, yp=(0.7, -1.1)),
        FirstClampedCubicSpline(X, Y, yp=0.7, m=0.0),
        SecondClampedCubicSpline(X0, Y0, m=1.0),
    ]


@pytest.mark.parametrize(
    "spline", _families(), ids=["natural", "clamped", "first-clamped", "second-clamped"]
)
def test_nodes_are_interpolated_exactly(spline):
    """Identity 1: the interpolant passes through every sample."""
    x = np.asarray(spline.x_data)
    y = np.asarray(spline.y_data)
    got = np.asarray(spline(x))
    scale = max(1.0, float(np.max(np.abs(y))))
    assert np.max(np.abs(got - y)) <= 8.0 * EPS * scale


@pytest.mark.parametrize(
    "spline", _families(), ids=["natural", "clamped", "first-clamped", "second-clamped"]
)
def test_second_derivative_is_continuous_at_interior_knots(spline):
    """Identity 1: C2 continuity, computed from the Hermite form, not the evaluator."""
    x = np.asarray(spline.x_data, dtype=float)
    y = np.asarray(spline.y_data, dtype=float)
    k = np.asarray(spline.k, dtype=float)

    # Cross-check the formula itself against the evaluator inside one interval,
    # so a wrong Hermite convention cannot masquerade as a passing identity.
    probe = x[0] + 0.37 * (x[1] - x[0])
    reported = float(np.asarray(spline(np.array([probe]), 2))[0])
    h = x[1] - x[0]
    t = (probe - x[0]) / h
    expected = (
        (12.0 * t - 6.0) * y[0]
        + (6.0 * t - 4.0) * h * k[0]
        + (-12.0 * t + 6.0) * y[1]
        + (6.0 * t - 2.0) * h * k[1]
    ) / h**2
    assert reported == pytest.approx(expected, rel=1e-12, abs=1e-12)

    scale = max(1.0, float(np.max(np.abs(k))) / float(np.min(np.diff(x))))
    for index in range(1, x.size - 1):
        left = _hermite_second_derivative_at_right(x, y, k, index - 1)
        right = _hermite_second_derivative_at_left(x, y, k, index)
        assert abs(left - right) <= 64.0 * EPS * scale


def test_natural_family_matches_scipy_natural_boundary():
    """Evidence 3: agreement with SciPy's independent natural-boundary solve."""
    spline = NaturalCubicSpline(X, Y)
    reference = CubicSpline(X, Y, bc_type="natural")
    query = np.linspace(X[0], X[-1], 41)
    scale = max(1.0, float(np.max(np.abs(Y))))
    for deriv, tolerance_scale in ((0, scale), (1, scale), (2, scale)):
        got = np.asarray(spline(query, deriv), dtype=float)
        want = reference(query, deriv)
        assert np.max(np.abs(got - want)) <= 64.0 * EPS * tolerance_scale

    # The natural boundary itself, read off the produced spline.
    ends = float(np.max(np.abs(np.asarray(spline(X[[0, -1]], 2), dtype=float))))
    assert ends <= 64.0 * EPS * scale


def test_clamped_family_matches_scipy_first_derivative_boundaries():
    """Evidence 3: agreement with SciPy for two prescribed end slopes."""
    slopes = (0.7, -1.1)
    spline = ClampedCubicSpline(X, Y, yp=slopes)
    reference = CubicSpline(X, Y, bc_type=((1, slopes[0]), (1, slopes[1])))
    query = np.linspace(X[0], X[-1], 41)
    scale = max(1.0, float(np.max(np.abs(Y))))
    for deriv in (0, 1, 2):
        got = np.asarray(spline(query, deriv), dtype=float)
        assert np.max(np.abs(got - reference(query, deriv))) <= 64.0 * EPS * scale

    ends = np.asarray(spline(X[[0, -1]], 1), dtype=float)
    assert ends == pytest.approx(np.array(slopes), rel=0.0, abs=64.0 * EPS)


def test_clamped_family_reproduces_a_cubic_exactly():
    """Identity 1: with exact end slopes the clamped spline is the cubic itself."""

    def cubic(t):
        return 2.0 * t**3 - 3.0 * t**2 + t + 1.0

    def cubic_slope(t):
        return 6.0 * t**2 - 6.0 * t + 1.0

    x = np.array([0.0, 0.5, 1.5, 2.5])
    spline = ClampedCubicSpline(x, cubic(x), yp=(cubic_slope(0.0), cubic_slope(2.5)))
    query = np.linspace(0.0, 2.5, 53)
    scale = max(1.0, float(np.max(np.abs(cubic(query)))))
    assert (
        np.max(np.abs(np.asarray(spline(query), dtype=float) - cubic(query))) <= 64.0 * EPS * scale
    )


def test_natural_family_reproduces_affine_samples():
    """Identity 1: an affine datum satisfies the natural condition, so it is reproduced."""
    x = np.array([0.0, 0.4, 1.5, 2.2, 3.0])
    spline = NaturalCubicSpline(x, 2.5 * x - 1.0)
    query = np.linspace(0.0, 3.0, 31)
    assert (
        np.max(np.abs(np.asarray(spline(query), dtype=float) - (2.5 * query - 1.0)))
        <= 16.0 * EPS * 10.0
    )
    assert np.max(np.abs(np.asarray(spline(query, 2), dtype=float))) <= 64.0 * EPS * 10.0


@pytest.mark.parametrize("m", [0.0, 0.7])
def test_first_clamped_satisfies_its_declared_cylindrical_row(m):
    """Identity 2: left slope is ``yp`` and the last knot satisfies the Robin row."""
    yp = 0.35
    spline = FirstClampedCubicSpline(X, Y, yp=yp, m=m)
    x_last = float(X[-1])

    assert float(np.asarray(spline(np.array([X[0]]), 1))[0]) == pytest.approx(yp, abs=64.0 * EPS)

    second = float(np.asarray(spline(np.array([x_last]), 2))[0])
    first = float(np.asarray(spline(np.array([x_last]), 1))[0])
    value = float(np.asarray(spline(np.array([x_last])))[0])
    residual = second + first / x_last - m**2 * value / x_last**2
    scale = max(1.0, abs(second), abs(first / x_last), abs(m**2 * value / x_last**2))
    assert abs(residual) <= 256.0 * EPS * scale


@pytest.mark.parametrize("m", [1.0, 0.5])
def test_second_clamped_satisfies_its_declared_origin_and_robin_rows(m):
    """Identity 2: origin row fixes x0=y0=0; the last knot satisfies the Robin row."""
    spline = SecondClampedCubicSpline(X0, Y0, m=m)
    x_last = float(X0[-1])

    assert float(np.asarray(spline(np.array([0.0])))[0]) == pytest.approx(0.0, abs=0.0)

    second = float(np.asarray(spline(np.array([x_last]), 2))[0])
    first = float(np.asarray(spline(np.array([x_last]), 1))[0])
    value = float(np.asarray(spline(np.array([x_last])))[0])
    residual = second + first / x_last - m**2 * value / x_last**2
    scale = max(1.0, abs(second), abs(first / x_last), abs(m**2 * value / x_last**2))
    assert abs(residual) <= 256.0 * EPS * scale


def test_the_two_cylindrical_families_select_different_splines():
    """Branch evidence: the origin row changes the solution, so the families differ."""
    first = np.asarray(FirstClampedCubicSpline(X0, Y0, yp=0.0, m=1.0).k, dtype=float)
    second = np.asarray(SecondClampedCubicSpline(X0, Y0, m=1.0).k, dtype=float)
    assert np.max(np.abs(first - second)) > 1e-3


def _refinement_ratio(make_spline, exact, interval, coarse_points=11, fine_points=21):
    """Max-error ratio between two uniform grids, both evaluated on one fine query."""
    low, high = interval
    query = np.linspace(low, high, 4001)
    errors = []
    for count in (coarse_points, fine_points):
        x = np.linspace(low, high, count)
        spline = make_spline(x, exact(x))
        errors.append(float(np.max(np.abs(np.asarray(spline(query), dtype=float) - exact(query)))))
    return errors[0] / errors[1], errors


@pytest.mark.parametrize(
    "_label, make_spline, exact, interval",
    [
        pytest.param(
            "natural",
            lambda x, y: NaturalCubicSpline(x, y),
            np.sin,
            (0.0, np.pi),
            id="natural-sin-both-natural-ends",
        ),
        pytest.param(
            "clamped",
            lambda x, y: ClampedCubicSpline(x, y, yp=(np.cos(0.0), np.cos(np.pi))),
            np.sin,
            (0.0, np.pi),
            id="clamped-sin-exact-end-slopes",
        ),
        pytest.param(
            "first-clamped",
            lambda x, y: FirstClampedCubicSpline(x, y, yp=1.0, m=0.0),
            np.log,
            (1.0, 2.0),
            id="first-clamped-m0-log-x",
        ),
    ],
)
def test_consistent_data_converges_at_the_declared_fourth_order(
    _label, make_spline, exact, interval
):
    """Budget 4: with boundary data the declared rows actually satisfy, error is O(h^4).

    The boundary data matter: ``f(x) = log x`` satisfies ``f'' + f'/x = 0`` for
    ``m = 0`` and has ``f'(1) = 1``, so the first-clamped family carries no
    boundary inconsistency.  Forcing ``yp = 0`` onto ``sin`` instead gives an
    O(1) boundary error and an observed ratio of about 2, which is why the
    clamped families are not exercised that way here; that drop from the O(h^4)
    interior rate is recorded as a limitation on the contract.
    """
    ratio, errors = _refinement_ratio(make_spline, exact, interval)
    assert errors[1] < errors[0]
    assert 10.0 <= ratio <= 22.0, f"observed refinement ratio {ratio:.2f} is not O(h^4)"


def test_second_clamped_rows_are_second_derivative_zero_at_origin_and_robin_at_last():
    """Identity 2: both retained rows pinned by one exactly consistent cubic.

    ``f = x^3`` has ``f(0) = 0`` and ``f''(0) = 0``, so the origin row (which is
    the zero second derivative at the origin once ``y_data[0] = 0``) holds, and
    it satisfies ``f'' + f'/x - m^2 f/x^2 = 0`` only for ``m = 3``.  The spline
    then reproduces the cubic to rounding, which pins both rows without
    referring to how the slope system is assembled.
    """
    x = np.linspace(0.0, 1.0, 6)
    spline = SecondClampedCubicSpline(x, x**3, m=3.0)
    x_last = float(x[-1])
    at = lambda value, deriv=0: float(np.asarray(spline(np.array([value]), deriv))[0])

    assert abs(at(0.0, 2)) <= 256.0 * EPS
    robin = at(x_last, 2) + at(x_last, 1) / x_last - 9.0 * at(x_last) / x_last**2
    assert abs(robin) <= 1024.0 * EPS * max(1.0, abs(at(x_last, 2)))

    query = np.linspace(0.0, 1.0, 101)
    assert np.max(np.abs(np.asarray(spline(query), dtype=float) - query**3)) <= 256.0 * EPS
