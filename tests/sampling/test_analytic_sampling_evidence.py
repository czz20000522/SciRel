"""Independent evidence for the analytic and low-degree-exact relations.

Assets:

* ``scirel.sampling.meridional-polar-forward`` (``transform_to_rtheta``)
* ``scirel.sampling.meridional-polar-inverse`` (``transform_to_rhoz``)
* ``scirel.sampling.nonuniform-first-derivative`` (``diff_central``)
* ``scirel.sampling.rectangular-spline`` (``interp``)
* ``scirel.sampling.regular-grid`` (``regular_grid``)

Each relation has an oracle that is written down independently of the code
under test, so the comparison is a physical/mathematical identity rather than a
restatement of the implementation:

1. **Orthonormal meridional basis.**  ``transform_to_rtheta`` documents
   ``theta`` as the angle from ``+Z`` toward ``+rho``.  That convention is
   testable without any reference table: ``sin(theta) = rho/r`` and
   ``cos(theta) = z/r``, the basis ``(sin, cos)`` is orthonormal, and the vector
   projection must preserve ``u_rho**2 + u_z**2``.  The rejected alternative
   convention ``pi/2 + atan2(z, rho)`` yields ``cos(theta) = -z/r`` and fails
   the first assertion, so the test discriminates between the two conventions
   instead of pinning today's output.
2. **Exact axis cases.**  ``sin`` and ``cos`` are formed as the ratios
   ``rho/r`` and ``z/r``, so on the axis one of them is exactly ``0.0`` or
   ``1.0``.  Those cases therefore carry a **zero-tolerance** assertion, while
   the general round trip carries the rounding budget stated below.
3. **Three-point Lagrange derivative.**  ``diff_central`` returns the derivative
   of the unique quadratic through ``(x[i-1], x[i], x[i+1])``, so its value at
   interior nodes equals ``2*x[i]`` for ``f = x**2`` **exactly** (the weights are
   rational and the products are exact for the grids used here).  The truth
   value is the analytic derivative, not a Lagrange recomputation, so an
   operator that reproduced only the interpolant's value would still fail.
4. **Degree-three reproduction.**  A cubic spline interpolant of a polynomial of
   degree ``<= 3`` in each variable is that polynomial.  The oracle is the
   polynomial itself, evaluated at the query points.
5. **Affine reproduction.**  Linear scattered interpolation on a Delaunay
   triangulation is exact for affine data inside the convex hull, and the
   generated grid axes are ``linspace(min, max)`` in ``ij`` order, which makes
   every axis entry an independent exact assertion (endpoints, monotonicity,
   constant along the other axis).

Precision budget, fixed before measurement:

* exact rational cases (axis-aligned polar, quadratic derivative): no tolerance,
  ``==`` / ``array_equal``;
* one rotation-composed round trip: ``4 * eps * max(1, |value|)``, the rounding of
  four correctly-rounded operations (multiply, add, multiply, add) per component;
* spline and linear-interpolation reproduction: ``16 * eps * scale`` where
  ``scale`` is the largest magnitude on the grid, i.e. about one ulp growth per
  floating operation of the spline evaluation.

Measured order, declared only where it was measured: on uniform grids of
``n = 20, 40, 80`` nodes over ``[-1, 1]`` and ``f = x**3``, the observed
``diff_central`` error falls by the square of the mesh-refinement factor, so the
operator is second order on that configuration; the test asserts
``ratio / h_ratio**2`` in ``[0.95, 1.05]`` on those three grids, and this test
does not claim second order for any other configuration.  No accuracy order is
established for the spline or the linear interpolant beyond degree-three and
affine reproduction.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from scirel.geometry.sampling import (
    diff_central,
    interp,
    regular_grid,
    transform_to_rtheta,
    transform_to_rhoz,
)

EPS = np.finfo(float).eps


def _budget(value, factor=4.0):
    return factor * EPS * max(1.0, abs(float(value)))


# ---------------------------------------------------------------------------
# meridional polar: forward
# ---------------------------------------------------------------------------


def test_polar_forward_satisfies_the_documented_angle_convention():
    """sin(theta) = rho/r and cos(theta) = z/r, the basis of the stated convention.

    The alternative convention ``pi/2 + atan2(z, rho)`` gives ``cos = -z/r`` and
    fails this assertion, so the check discriminates between the two.
    """
    rho, z = 3.0, 4.0
    r, theta, _, _ = transform_to_rtheta(rho, z, 1.0, 1.0)
    assert r == 5.0  # 3-4-5 is exact in binary64
    assert abs(math.sin(theta) - rho / r) <= _budget(1.0)
    assert abs(math.cos(theta) - z / r) <= _budget(1.0)
    assert abs(math.sin(theta) ** 2 + math.cos(theta) ** 2 - 1.0) <= _budget(1.0)


@pytest.mark.parametrize(
    "rho, z, expected_radius, expected_theta, expected_radial, expected_angular",
    [
        (0.0, 2.0, 2.0, 0.0, 11.0, 7.0),
        (3.0, 0.0, 3.0, math.pi / 2, 7.0, -11.0),
        (-3.0, 0.0, 3.0, -math.pi / 2, -7.0, 11.0),
        (0.0, -2.0, 2.0, math.pi, -11.0, -7.0),
    ],
)
def test_polar_forward_is_exact_on_the_axes(
    rho, z, expected_radius, expected_theta, expected_radial, expected_angular
):
    """One ratio is exactly 0 and the other exactly 1, so nothing rounds."""
    r, theta, radial, angular = transform_to_rtheta(rho, z, 7.0, 11.0)
    assert (r, theta, radial, angular) == (
        expected_radius,
        expected_theta,
        expected_radial,
        expected_angular,
    )


def test_polar_forward_preserves_the_vector_norm():
    """The projection is a rotation, so |u| is invariant."""
    for rho, z in [(3.0, 4.0), (-1.5, 0.25), (0.1, -7.0), (2.0, 2.0)]:
        _, _, radial, angular = transform_to_rtheta(rho, z, 1.5, -2.5)
        assert abs((radial**2 + angular**2) - (1.5**2 + (-2.5) ** 2)) <= _budget(1.5**2 + 2.5**2)


def test_polar_forward_rounds_the_45_degree_case_only_at_the_budget():
    """A non-Pythagorean radius still conserves the norm and the angle ratios."""
    rho = z = 1.0
    r, theta, radial, angular = transform_to_rtheta(rho, z, 2.0, 0.0)
    # u_rho = 2, u_z = 0 and sin = cos = 1/sqrt(2): both projections are sqrt(2).
    assert abs(r - math.sqrt(2.0)) <= _budget(math.sqrt(2.0))
    assert abs(math.sin(theta) - 0.5 * math.sqrt(2.0)) <= _budget(1.0)
    assert abs(radial - math.sqrt(2.0)) <= _budget(2.0)
    assert abs(angular - math.sqrt(2.0)) <= _budget(2.0)
    assert abs(radial - angular) <= _budget(2.0)  # the basis is orthonormal


def test_polar_forward_rejects_the_origin_and_nonfinite_input():
    """invalid_input channel: origin has no polar basis; non-finite is refused."""
    with pytest.raises(ValueError):
        transform_to_rtheta(0.0, 0.0, 1.0, 1.0)
    with pytest.raises(ValueError):
        transform_to_rtheta(np.nan, 1.0, 1.0, 1.0)
    with pytest.raises(ValueError):
        transform_to_rtheta(1.0, 1.0, np.inf, 1.0)


def test_polar_forward_returns_nothing_on_rejection():
    """partial_results channel: no partial tuple escapes a rejected request."""
    result = None
    with pytest.raises(ValueError):
        result = transform_to_rtheta(0.0, 0.0, 1.0, 1.0)
    assert result is None


def test_polar_forward_broadcasts_and_keeps_shape():
    """Broadcasting follows NumPy; silent shape narrowing would fail here."""
    rho = np.array([[1.0], [2.0]])
    z = np.array([1.0, 2.0, 3.0])
    r, theta, radial, angular = transform_to_rtheta(rho, z, 1.0, 0.0)
    assert r.shape == theta.shape == radial.shape == angular.shape == (2, 3)


# ---------------------------------------------------------------------------
# meridional polar: inverse
# ---------------------------------------------------------------------------


def test_polar_inverse_is_exact_on_the_axis():
    """theta = 0 makes sin exactly 0 and cos exactly 1."""
    rho, z, radial, axial = transform_to_rhoz(2.0, 0.0, 7.0, 11.0)
    assert (rho, z, radial, axial) == (0.0, 2.0, 11.0, 7.0)


@pytest.mark.parametrize("rho, z", [(3.0, 4.0), (-1.5, 0.25), (0.1, -7.0), (2.0, 2.0)])
def test_polar_round_trip_recovers_position_and_vector(rho, z):
    """forward then inverse is the identity within the four-operation budget."""
    r, theta, radial, angular = transform_to_rtheta(rho, z, 1.5, -2.5)
    back_rho, back_z, back_radial, back_axial = transform_to_rhoz(r, theta, radial, angular)
    assert abs(back_rho - rho) <= _budget(rho, 8.0)
    assert abs(back_z - z) <= _budget(z, 8.0)
    assert abs(back_radial - 1.5) <= _budget(2.5, 8.0)
    assert abs(back_axial - (-2.5)) <= _budget(2.5, 8.0)


def test_polar_inverse_rejects_nonpositive_radius_and_nonfinite_input():
    """invalid_input channel: R must be strictly positive and finite."""
    with pytest.raises(ValueError):
        transform_to_rhoz(0.0, 0.0, 1.0, 1.0)
    with pytest.raises(ValueError):
        transform_to_rhoz(-1.0, 0.0, 1.0, 1.0)
    with pytest.raises(ValueError):
        transform_to_rhoz(1.0, np.nan, 1.0, 1.0)


def test_polar_inverse_returns_nothing_on_rejection():
    """partial_results channel."""
    result = None
    with pytest.raises(ValueError):
        result = transform_to_rhoz(-2.0, 0.0, 1.0, 1.0)
    assert result is None


# ---------------------------------------------------------------------------
# nonuniform first derivative
# ---------------------------------------------------------------------------

NONUNIFORM_GRIDS = (
    [0.0, 0.5, 2.0, 3.0],
    [0.0, 1.0, 3.0],
    [-1.0, 0.25, 1.5, 4.0],
    [0.0, 0.125, 0.5, 2.0, 8.0],
)


@pytest.mark.parametrize("grid", NONUNIFORM_GRIDS)
def test_first_derivative_is_exact_for_a_nonuniform_quadratic(grid):
    """The three-point operator returns 2*x at every interior node, exactly."""
    x = np.array(grid)
    expected = np.array([2.0 * value for value in grid[1:-1]])
    assert np.array_equal(diff_central(x, x * x), expected)


@pytest.mark.parametrize("grid", NONUNIFORM_GRIDS)
def test_first_derivative_returns_the_slope_of_a_nonuniform_linear_sample(grid):
    """Linear data has a constant derivative; the operator must return it exactly."""
    x = np.array(grid)
    assert np.array_equal(diff_central(x, 3.0 * x - 7.0), np.full(len(grid) - 2, 3.0))


def test_first_derivative_output_length_and_index_alignment():
    """N-2 outputs sit at the interior nodes x[1:-1]; the ends are not extrapolated."""
    x = np.array([0.0, 0.5, 2.0, 3.0])
    derivative = diff_central(x, x * x)
    assert derivative.shape == (len(x) - 2,)
    # Alignment: value k must be the derivative at x[k + 1], not x[k].
    assert np.array_equal(derivative, 2.0 * x[1:-1])
    assert derivative[0] != 2.0 * x[0]


def test_first_derivative_measured_second_order_on_uniform_refinement():
    """Measured order only on this configuration: err ~ h**2 for f = x**3.

    The ratio is compared with the squared mesh-refinement factor, so a
    first-order or third-order operator falls outside the band.  The measured
    values behind the band are recorded in the module docstring.
    """
    errors = []
    spacings = []
    for nodes in (20, 40, 80):
        x = np.linspace(-1.0, 1.0, nodes)
        derivative = diff_central(x, x**3)
        errors.append(float(np.max(np.abs(derivative - 3.0 * x[1:-1] ** 2))))
        spacings.append(float(x[1] - x[0]))
    for index in (1, 2):
        error_ratio = errors[index - 1] / errors[index]
        spacing_ratio = spacings[index - 1] / spacings[index]
        assert 0.95 <= error_ratio / spacing_ratio**2 <= 1.05, (
            errors,
            spacings,
        )
    # The refinement must actually reduce the error, not merely scale.
    assert errors[0] > errors[1] > errors[2] > 0.0


def test_first_derivative_rejects_nonfinite_unsorted_and_short_inputs():
    """invalid_input channel: each rejection reason has its own assertion."""
    with pytest.raises(ValueError):
        diff_central(np.array([0.0, 1.0, 2.0]), np.array([0.0, np.nan, 4.0]))
    with pytest.raises(ValueError):
        diff_central(np.array([0.0, 2.0, 1.0]), np.array([0.0, 1.0, 2.0]))
    with pytest.raises(ValueError):
        diff_central(np.array([0.0, 1.0]), np.array([0.0, 1.0]))
    with pytest.raises(ValueError):
        diff_central(np.array([0.0, 1.0, 2.0]), np.array([0.0, 1.0]))


def test_first_derivative_returns_nothing_on_rejection():
    """partial_results channel."""
    result = None
    with pytest.raises(ValueError):
        result = diff_central(np.array([0.0, 1.0]), np.array([0.0, 1.0]))
    assert result is None


# ---------------------------------------------------------------------------
# rectangular spline
# ---------------------------------------------------------------------------

R_AXIS = np.linspace(0.0, 1.0, 5)
Z_AXIS = np.linspace(-0.5, 0.5, 5)
RHO, ZED = np.meshgrid(R_AXIS, Z_AXIS)
QUERY = np.array([[0.2, -0.3], [0.55, 0.1], [0.9, 0.42], [0.35, -0.45]])


@pytest.mark.parametrize(
    "name, field, exact",
    [
        ("affine", RHO + 2.0 * ZED, lambda r, z: r + 2.0 * z),
        ("radial-quadratic", RHO**2, lambda r, z: r * r),
        ("radial-cubic", RHO**3, lambda r, z: r**3),
        ("separable-product", RHO * ZED, lambda r, z: r * z),
    ],
)
def test_rectangular_spline_reproduces_degree_three_polynomials(name, field, exact):
    """A cubic spline interpolant of a degree <= 3 polynomial is that polynomial."""
    values = interp(RHO, ZED, field, QUERY)
    expected = np.array([exact(point[0], point[1]) for point in QUERY])
    scale = max(1.0, float(np.max(np.abs(field))))
    assert np.all(np.abs(values - expected) <= 16.0 * EPS * scale), (name, values, expected)
    # The assertions must not be able to pass by all sides collapsing to zero.
    assert np.max(np.abs(expected)) > 0.1


def test_rectangular_spline_follows_the_query_order():
    """The result is ordered like `flpoints`, so transposing the queries transposes it."""
    field = RHO + 2.0 * ZED
    forward = interp(RHO, ZED, field, QUERY)
    reversed_queries = interp(RHO, ZED, field, QUERY[::-1])
    assert np.allclose(forward[::-1], reversed_queries, rtol=0.0, atol=16.0 * EPS)
    assert not np.array_equal(forward, reversed_queries)  # the fixture is discriminating


def test_rectangular_spline_rejects_queries_outside_the_grid_support():
    """invalid_input channel: no extrapolation, one assertion per reason."""
    field = RHO + 2.0 * ZED
    with pytest.raises(ValueError):
        interp(RHO, ZED, field, np.array([[1.2, 0.0]]))
    with pytest.raises(ValueError):
        interp(RHO, ZED, field, np.array([[0.5, -0.9]]))
    with pytest.raises(ValueError):
        interp(RHO, ZED, field, np.array([[np.nan, 0.0]]))
    with pytest.raises(ValueError):
        interp(RHO, ZED, field, np.array([0.5, 0.5]))  # not (n, 2)
    with pytest.raises(ValueError):
        interp(RHO, ZED, field[:-1], np.array([[0.5, 0.0]]))


def test_rectangular_spline_returns_nothing_on_rejection():
    """partial_results channel."""
    result = None
    with pytest.raises(ValueError):
        result = interp(RHO, ZED, RHO, np.array([[2.0, 0.0]]))
    assert result is None


def test_rectangular_spline_propagates_a_too_coarse_grid():
    """runtime_failure channel: fewer than four nodes per axis cannot form a cubic spline."""
    coarse_r = np.linspace(0.0, 1.0, 3)
    coarse_z = np.linspace(-1.0, 1.0, 3)
    coarse_rho, coarse_zed = np.meshgrid(coarse_r, coarse_z)
    with pytest.raises((ValueError, TypeError)):
        interp(coarse_rho, coarse_zed, coarse_rho + coarse_zed, np.array([[0.5, 0.0]]))


# ---------------------------------------------------------------------------
# regular grid
# ---------------------------------------------------------------------------

SCATTER_X = np.array([0.0, 1.0, 0.0, 1.0, 0.5, 0.25, 0.75, 0.5])
SCATTER_Y = np.array([0.0, 0.0, 1.0, 1.0, 0.5, 0.25, 0.25, 0.75])


def _scatter_field():
    return 2.0 * SCATTER_X - 3.0 * SCATTER_Y + 0.5


def test_regular_grid_generates_an_ij_indexed_axis_product():
    """The generated axes are linspace(min, max) in ij order, exactly."""
    xi, yi, _ = regular_grid(SCATTER_X, SCATTER_Y, _scatter_field(), nx=4, ny=5)
    assert xi.shape == (4, 5) == yi.shape
    # Each coordinate depends on exactly one index.
    assert np.array_equal(xi, np.broadcast_to(xi[:, :1], xi.shape))
    assert np.array_equal(yi, np.broadcast_to(yi[:1, :], yi.shape))
    # Endpoints are the data extremes, and the axis is the requested length.
    assert xi[0, 0] == SCATTER_X.min() == 0.0
    assert xi[-1, 0] == SCATTER_X.max() == 1.0
    assert yi[0, 0] == SCATTER_Y.min() == 0.0
    assert yi[0, -1] == SCATTER_Y.max() == 1.0
    assert np.array_equal(xi[:, 0], np.linspace(SCATTER_X.min(), SCATTER_X.max(), 4))
    assert np.array_equal(yi[0, :], np.linspace(SCATTER_Y.min(), SCATTER_Y.max(), 5))


def test_regular_grid_reproduces_an_affine_field_at_supplied_points():
    """Linear scattered interpolation is exact for affine data inside the hull."""
    query_x = np.array([0.2, 0.6, 0.75])
    query_y = np.array([0.2, 0.4, 0.3])
    _, _, values = regular_grid(SCATTER_X, SCATTER_Y, _scatter_field(), xi=query_x, yi=query_y)
    expected = 2.0 * query_x - 3.0 * query_y + 0.5
    assert np.all(np.abs(values - expected) <= 16.0 * EPS)
    assert np.max(np.abs(expected)) > 0.1  # not a zero-collapsing fixture


def test_regular_grid_keeps_the_field_order_and_returns_only_coordinates_without_fields():
    """Positional fields preserve order; no field returns the two axes alone."""
    first, second = _scatter_field(), 3.0 * _scatter_field()
    query_x = np.array([0.2, 0.6])
    query_y = np.array([0.2, 0.4])
    _, _, one, two = regular_grid(SCATTER_X, SCATTER_Y, first, second, xi=query_x, yi=query_y)
    assert np.allclose(two, 3.0 * one, rtol=0.0, atol=16.0 * EPS)
    only_axes = regular_grid(SCATTER_X, SCATTER_Y, nx=3, ny=2)
    assert len(only_axes) == 2
    assert only_axes[0].shape == (3, 2)


def test_regular_grid_does_not_synthesise_values_outside_the_hull():
    """Outside support the linear interpolant is NaN, never an invented value."""
    _, _, values = regular_grid(
        SCATTER_X, SCATTER_Y, _scatter_field(), xi=np.array([1.2]), yi=np.array([0.2])
    )
    assert np.isnan(values).all()


def test_regular_grid_nearest_returns_a_stored_sample():
    """`method='nearest'` selects stored values, so every output is in the data."""
    _, _, values = regular_grid(
        SCATTER_X,
        SCATTER_Y,
        _scatter_field(),
        xi=np.array([0.2, 0.75]),
        yi=np.array([0.2, 0.25]),
        method="nearest",
    )
    assert np.isin(values, _scatter_field()).all()


def test_regular_grid_rejects_unknown_methods_and_removed_keywords():
    """invalid_input channel: both documented rejection shapes are asserted."""
    with pytest.raises(ValueError):
        regular_grid(SCATTER_X, SCATTER_Y, _scatter_field(), method="spline")
    with pytest.raises(TypeError):
        regular_grid(SCATTER_X, SCATTER_Y, values=[_scatter_field()])


def test_regular_grid_returns_nothing_on_rejection():
    """partial_results channel."""
    result = None
    with pytest.raises(ValueError):
        result = regular_grid(SCATTER_X, SCATTER_Y, _scatter_field(), method="spline")
    assert result is None


def test_regular_grid_is_reproducible():
    """The Delaunay triangulation is deterministic for a fixed point order."""
    first = regular_grid(SCATTER_X, SCATTER_Y, _scatter_field(), nx=3, ny=3)
    second = regular_grid(SCATTER_X, SCATTER_Y, _scatter_field(), nx=3, ny=3)
    assert all(np.array_equal(left, right) for left, right in zip(first, second, strict=True))
