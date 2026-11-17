"""Independent evidence for the weighted line reduction, polynomial fit and scattered query.

Assets:

* ``scirel.geometry.weighted-line-integral`` (``flux_surface_avg``)
* ``scirel.geometry.polynomial-fit`` (``poly_fit``)
* ``scirel.geometry.scattered-linear`` (``locs_to_vals_griddata``)

The failure mode these three share is a wrong **constant**: the weight taken as
``|B|`` instead of ``1/|B|``, a missing normalisation of the weighted mean, or a
singular-value cutoff applied at the wrong place.  Each oracle below is a closed
form whose magnitude would change under exactly that error:

1. **Weight scaling law.**  With a constant ``B`` the reduction is
   ``integral(1/B ds) = L / B`` exactly (the trapezoid rule integrates a constant
   exactly).  ``B = 1, 2, 4, 1/2`` on a path of length ``1`` therefore gives
   ``1, 1/2, 1/4, 2``.  A ``|B|`` weight gives ``1, 2, 4, 1/2``, which the test
   distinguishes on every point, and a ``1/B**2`` weight gives ``1, 1/4, 1/16, 4``.
2. **Normalisation.**  A constant quantity ``Q = c`` must average to exactly
   ``c``.  A missing denominator returns ``c * L / B`` instead, and a missing
   ``1/B`` in the numerator returns ``c * B``-weighted values.
3. **Exact linear mean.**  On a straight path with constant ``B`` and ``Q = rho``
   over ``[0, 1]``, the trapezoid rule is exact and the mean is ``1/2``.  Splitting
   the path or reversing it must not move that number, which pins both the
   arclength measure and the accumulation direction.
4. **Exact Vandermonde solution.**  With as many distinct nodes as coefficients,
   the fit has a unique solution, recomputed here with :class:`fractions.Fraction`
   Gaussian elimination.  The contract's minimum-norm rule is a *second*,
   independent property: for an underdetermined system the returned coefficient
   vector must lie in the row space of the design matrix, i.e. be orthogonal to
   its null space.  Both properties are checked separately.
5. **Affine reproduction.**  Linear scattered interpolation returns an affine
   field exactly inside the convex hull, returns the stored value at a node, and
   returns NaN outside the hull instead of inventing a value.

Precision budget, fixed before measurement:

* constant-``B`` integral and constant-``Q`` mean: ``8 * eps * scale``, the
  rounding of a handful of additions and one division;
* linear-mean invariance under refinement/reversal: ``8 * eps`` relative;
* coefficients against the exact rational solution: ``256 * eps * max(1, |c|)``,
  the backward error of an SVD solve amplified by the small Vandermonde
  condition numbers used here (all nodes in ``[0, 3]``);
* affine reproduction: ``16 * eps * scale``.

**Not established here:** the accuracy of the reduction for a *non-affine* ``B``.
``1/B`` along a general path has no polynomial closed form, so the spline error
in ``B`` is not separated from the quadrature error; only the exact cases above
and the stated invariances are established.  Recorded as ``cannot establish`` in
the contract.
"""

from __future__ import annotations

from fractions import Fraction

import numpy as np
import pytest

from scirel.geometry.sampling import flux_surface_avg, locs_to_vals_griddata, poly_fit

EPS = np.finfo(float).eps

RHO_GRID, Z_GRID = np.meshgrid(np.linspace(0.0, 1.0, 5), np.linspace(-0.2, 0.2, 5))
PATH = np.column_stack([np.linspace(0.0, 1.0, 9), np.zeros(9)])
PATH_REFINED = np.column_stack([np.linspace(0.0, 1.0, 17), np.zeros(17)])


def _constant(value):
    return np.full_like(RHO_GRID, value)


# ---------------------------------------------------------------------------
# weighted-line-integral
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("field", [1.0, 2.0, 4.0, 0.5])
def test_weighted_integral_is_the_length_over_the_field(field):
    """A constant field gives integral(1/B ds) = L/B = 1/B on a unit-length path."""
    integral = flux_surface_avg(RHO_GRID, Z_GRID, _constant(field), PATH)
    assert abs(integral - 1.0 / field) <= 8.0 * EPS * max(1.0, 1.0 / field)


def test_weighted_integral_weight_is_inverse_not_direct():
    """The scaling law separates 1/B from B and from 1/B**2 at the same input."""
    integral = flux_surface_avg(RHO_GRID, Z_GRID, _constant(4.0), PATH)
    assert abs(integral - 0.25) <= 8.0 * EPS
    assert integral != pytest.approx(4.0)  # would be the |B| weight
    assert integral != pytest.approx(1.0 / 16.0)  # would be the 1/B**2 weight


@pytest.mark.parametrize("field", [1.0, 2.0, 7.0])
def test_weighted_average_of_a_constant_quantity_is_that_constant(field):
    """The denominator must cancel the numerator exactly for a constant quantity."""
    average = flux_surface_avg(RHO_GRID, Z_GRID, _constant(field), PATH, _constant(3.0))
    assert abs(average - 3.0) <= 8.0 * EPS * 3.0


def test_weighted_average_of_rho_is_the_exact_midpoint():
    """Trapezoid is exact for a linear quantity, so the mean over [0, 1] is 1/2."""
    average = flux_surface_avg(RHO_GRID, Z_GRID, _constant(1.0), PATH, RHO_GRID + 0.0 * Z_GRID)
    assert abs(average - 0.5) <= 8.0 * EPS


def test_weighted_average_is_invariant_under_path_refinement_and_reversal():
    """Subdividing or reversing the path may not move the weighted mean."""
    quantity = RHO_GRID + 0.0 * Z_GRID
    reference = flux_surface_avg(RHO_GRID, Z_GRID, _constant(1.0), PATH, quantity)
    refined = flux_surface_avg(RHO_GRID, Z_GRID, _constant(1.0), PATH_REFINED, quantity)
    reversed_path = flux_surface_avg(RHO_GRID, Z_GRID, _constant(1.0), PATH[::-1], quantity)
    assert abs(refined - reference) <= 8.0 * EPS
    assert abs(reversed_path - reference) <= 8.0 * EPS


def test_weighted_integral_of_a_zero_length_path_is_zero():
    """Boundary n=1 style case: a degenerate path integrates to zero, not to NaN."""
    degenerate = np.array([[0.5, 0.0], [0.5, 0.0]])
    assert flux_surface_avg(RHO_GRID, Z_GRID, _constant(1.0), degenerate) == 0.0


def test_weighted_average_rejects_a_zero_one_over_field_integral():
    """invalid_input channel: an average needs a nonzero integral of 1/B."""
    degenerate = np.array([[0.5, 0.0], [0.5, 0.0]])
    with pytest.raises(ValueError):
        flux_surface_avg(RHO_GRID, Z_GRID, _constant(1.0), degenerate, _constant(2.0))


@pytest.mark.parametrize("field", [-1.0, 0.0])
def test_weighted_integral_rejects_nonpositive_field_along_the_path(field):
    """invalid_input channel: |B| must be positive wherever the path samples it."""
    with pytest.raises(ValueError):
        flux_surface_avg(RHO_GRID, Z_GRID, _constant(field), PATH)


def test_weighted_integral_rejects_nonfinite_grid_data_and_path():
    """invalid_input channel: grid, field, path and quantity are all validated."""
    bad_grid = RHO_GRID.copy()
    bad_grid[0, 0] = np.nan
    with pytest.raises(ValueError):
        flux_surface_avg(bad_grid, Z_GRID, _constant(1.0), PATH)
    bad_field = _constant(1.0)
    bad_field[2, 2] = np.inf
    with pytest.raises(ValueError):
        flux_surface_avg(RHO_GRID, Z_GRID, bad_field, PATH)
    bad_path = PATH.copy()
    bad_path[3, 0] = np.nan
    with pytest.raises(ValueError):
        flux_surface_avg(RHO_GRID, Z_GRID, _constant(1.0), bad_path)
    bad_quantity = RHO_GRID.copy()
    bad_quantity[1, 1] = np.nan
    with pytest.raises(ValueError):
        flux_surface_avg(RHO_GRID, Z_GRID, _constant(1.0), PATH, bad_quantity)


def test_weighted_integral_returns_nothing_on_rejection():
    """partial_results channel."""
    result = None
    with pytest.raises(ValueError):
        result = flux_surface_avg(RHO_GRID, Z_GRID, _constant(-1.0), PATH)
    assert result is None


# ---------------------------------------------------------------------------
# polynomial-fit
# ---------------------------------------------------------------------------


def _exact_solve(nodes, values):
    """Exact ascending-power coefficients of the interpolating polynomial.

    Gaussian elimination on the Vandermonde system over :class:`fractions.Fraction`;
    the system is square with distinct nodes, so the solution is unique.
    """
    size = len(nodes)
    matrix = [
        [Fraction(*float(node).as_integer_ratio()) ** power for power in range(size)]
        + [Fraction(*float(value).as_integer_ratio())]
        for node, value in zip(nodes, values, strict=True)
    ]
    for column in range(size):
        pivot = next(row for row in range(column, size) if matrix[row][column] != 0)
        matrix[column], matrix[pivot] = matrix[pivot], matrix[column]
        scale = matrix[column][column]
        matrix[column] = [entry / scale for entry in matrix[column]]
        for row in range(size):
            if row != column and matrix[row][column] != 0:
                factor = matrix[row][column]
                matrix[row] = [
                    left - factor * right
                    for left, right in zip(matrix[row], matrix[column], strict=True)
                ]
    return [matrix[row][-1] for row in range(size)]


def _null_space_rows(nodes, order):
    """Exact null-space basis of the Vandermonde design matrix.

    Returned as row vectors so the minimum-norm test can take exact inner
    products; the design matrix has ``len(nodes)`` rows and ``order + 1`` columns.
    """
    width = order + 1
    matrix = [
        [Fraction(*float(node).as_integer_ratio()) ** power for power in range(width)]
        for node in nodes
    ]
    pivots: list[int] = []
    row = 0
    for column in range(width):
        pivot = next(
            (index for index in range(row, len(matrix)) if matrix[index][column] != 0), None
        )
        if pivot is None:
            continue
        matrix[row], matrix[pivot] = matrix[pivot], matrix[row]
        scale = matrix[row][column]
        matrix[row] = [entry / scale for entry in matrix[row]]
        for index in range(len(matrix)):
            if index != row and matrix[index][column] != 0:
                factor = matrix[index][column]
                matrix[index] = [
                    left - factor * right
                    for left, right in zip(matrix[index], matrix[row], strict=True)
                ]
        pivots.append(column)
        row += 1
        if row == len(matrix):
            break
    free = [column for column in range(width) if column not in pivots]
    basis = []
    for column in free:
        vector = [Fraction(0)] * width
        vector[column] = Fraction(1)
        for index, pivot_column in enumerate(pivots):
            vector[pivot_column] = -matrix[index][column]
        basis.append(vector)
    return basis


def test_polynomial_fit_recovers_the_exact_interpolating_polynomial():
    """Square Vandermonde system: the coefficients equal the exact rational solution."""
    nodes = [0.0, 1.0, 2.0, 3.0]
    values = [1.0, -1.0, 3.0, 7.0]
    exact = _exact_solve(nodes, values)
    assert [float(entry) for entry in exact] == [1.0, -7.0, 6.0, -1.0]
    _, coefficients = poly_fit(np.array(nodes), np.array(values), order=3)
    scale = max(1.0, float(np.max(np.abs(coefficients))))
    assert np.all(
        np.abs(coefficients - np.array([float(entry) for entry in exact])) <= 256.0 * EPS * scale
    )
    # The fit must reproduce the samples, not merely be close to some polynomial.
    assert np.all(
        np.abs(np.polyval(coefficients[::-1], nodes) - np.array(values)) <= 256.0 * EPS * scale
    )


def test_polynomial_fit_ascending_basis_functions_retain_their_exponent():
    """`basis_fns[k](v)` must be `v**k`, so the highest power is order."""
    nodes = np.array([0.0, 1.0, 2.0])
    basis, _ = poly_fit(nodes, nodes**2, order=2)
    assert len(basis) == 3
    for power, function in enumerate(basis):
        assert function(3.0) == 3.0**power


def test_polynomial_fit_returns_the_exact_slope_for_linear_data():
    """order=1 on collinear samples: intercept and slope are recovered exactly."""
    _, coefficients = poly_fit(np.array([0.0, 1.0, 2.0]), np.array([5.0, 7.0, 9.0]), order=1)
    assert np.allclose(coefficients, [5.0, 2.0], rtol=0.0, atol=64.0 * EPS)


def test_polynomial_fit_underdetermined_solution_is_the_minimum_norm_one():
    """Two nodes and three extra powers: the unique minimum-norm solution is derived here.

    ``A c = y`` with ``A = [[1, 0, 0, 0], [1, 1, 1, 1]]`` forces ``c0 = 1`` and
    ``c1 + c2 + c3 = 1``; the null space is spanned by ``(0, 1, -1, 0)`` and
    ``(0, 1, 0, -1)``, so minimality requires ``c1 = c2 = c3 = 1/3``.
    """
    nodes = np.array([0.0, 1.0])
    values = np.array([1.0, 2.0])
    basis = _null_space_rows(nodes, 3)
    assert len(basis) == 2
    _, coefficients = poly_fit(nodes, values, order=3)
    exact = [Fraction(1), Fraction(1, 3), Fraction(1, 3), Fraction(1, 3)]
    assert np.all(np.abs(coefficients - np.array([float(entry) for entry in exact])) <= 256.0 * EPS)
    # The same statement without reading the closed form: orthogonality to the null space.
    exact_coefficients = [Fraction(*float(value).as_integer_ratio()) for value in coefficients]
    for vector in basis:
        inner = sum(
            (left * right for left, right in zip(exact_coefficients, vector, strict=True)),
            Fraction(0),
        )
        assert inner == 0, (coefficients, vector)
    # And the residual is zero to rounding, so the fit is a genuine solution.
    design = np.power(nodes[:, None], np.arange(4)[None, :])
    assert np.all(np.abs(design @ coefficients - values) <= 256.0 * EPS)


def test_polynomial_fit_rejects_nonfinite_samples():
    """invalid_input channel: x and y are validated before the design matrix."""
    with pytest.raises(ValueError):
        poly_fit(np.array([0.0, np.nan, 2.0]), np.array([0.0, 1.0, 2.0]))
    with pytest.raises(ValueError):
        poly_fit(np.array([0.0, 1.0, 2.0]), np.array([0.0, np.inf, 2.0]))


def test_polynomial_fit_returns_nothing_on_rejection():
    """partial_results channel."""
    result = None
    with pytest.raises(ValueError):
        result = poly_fit(np.array([0.0, np.nan]), np.array([0.0, 1.0]))
    assert result is None


def test_polynomial_fit_is_reproducible():
    """The SVD solve has no randomness; two calls agree bitwise."""
    nodes = np.array([0.0, 1.0, 2.0, 3.0])
    values = np.array([1.0, -1.0, 3.0, 7.0])
    first = poly_fit(nodes, values, order=3)[1]
    second = poly_fit(nodes, values, order=3)[1]
    assert np.array_equal(first, second)


# ---------------------------------------------------------------------------
# scattered-linear
# ---------------------------------------------------------------------------

SCATTER_X, SCATTER_Y = np.meshgrid(np.array([0.0, 1.0]), np.array([0.0, 1.0]))
SCATTER_FIELD = 2.0 * SCATTER_X - 3.0 * SCATTER_Y + 0.5


@pytest.mark.parametrize(
    "query, expected",
    [
        ((0.25, 0.25), 0.25),
        ((0.75, 0.6), 0.2),
        ((0.5, 0.5), 0.0),
        ((1.0, 1.0), -0.5),
        ((0.0, 0.0), 0.5),
    ],
)
def test_scattered_linear_reproduces_the_affine_field(query, expected):
    """Linear interpolation on a triangulation is exact for affine data."""
    values = locs_to_vals_griddata(SCATTER_X, SCATTER_Y, SCATTER_FIELD, [query])
    assert abs(float(values[0]) - expected) <= 16.0 * EPS


def test_scattered_linear_returns_the_stored_value_at_a_node():
    """A query at a data point returns that sample exactly, not an average."""
    nodes = [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0), (1.0, 1.0)]
    values = locs_to_vals_griddata(SCATTER_X, SCATTER_Y, SCATTER_FIELD, nodes)
    assert np.array_equal(np.asarray(values), SCATTER_FIELD.ravel())


def test_scattered_linear_does_not_synthesise_values_outside_the_hull():
    """Outside support the interpolant is NaN; no extrapolation is invented."""
    values = locs_to_vals_griddata(SCATTER_X, SCATTER_Y, SCATTER_FIELD, [(3.0, 3.0)])
    assert np.isnan(values).all()


def test_scattered_linear_preserves_query_order_and_duplicates():
    """The returned sequence follows `coord_list`, duplicates included."""
    queries = [(0.25, 0.25), (1.0, 1.0), (0.25, 0.25)]
    values = locs_to_vals_griddata(SCATTER_X, SCATTER_Y, SCATTER_FIELD, queries)
    assert values[0] == values[2]
    assert abs(float(values[0]) - 0.25) <= 16.0 * EPS
    assert abs(float(values[1]) - (-0.5)) <= 16.0 * EPS


def test_scattered_linear_rejects_nonfinite_samples():
    """invalid_input channel: the underlying SciPy rejection is surfacing to the caller."""
    bad_x = SCATTER_X.copy()
    bad_x[0, 1] = np.nan
    with pytest.raises(ValueError):
        locs_to_vals_griddata(bad_x, SCATTER_Y, SCATTER_FIELD, [(0.5, 0.5)])


def test_scattered_linear_propagates_a_malformed_shape():
    """runtime_failure channel: mismatched field shapes raise instead of being repaired."""
    with pytest.raises(ValueError):
        locs_to_vals_griddata(SCATTER_X, SCATTER_Y, np.zeros(3), [(0.5, 0.5)])


def test_scattered_linear_is_reproducible():
    """The Delaunay triangulation is deterministic for a fixed point order."""
    queries = [(0.25, 0.25), (0.75, 0.6)]
    first = locs_to_vals_griddata(SCATTER_X, SCATTER_Y, SCATTER_FIELD, queries)
    second = locs_to_vals_griddata(SCATTER_X, SCATTER_Y, SCATTER_FIELD, queries)
    assert np.array_equal(first, second)
