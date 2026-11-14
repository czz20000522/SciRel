"""Bounded failure contracts for the six sampling entry points in issue 241."""

import numpy as np
import pytest
from decimal import Decimal
from fractions import Fraction

from scirel.geometry import sampling


NONFINITE = [np.nan, np.inf, -np.inf]
NEAREST = [sampling.locs_to_vals, sampling.locs_to_vals1D]


@pytest.fixture
def square():
    return np.array([[0.0, 0.0], [0.0, 1.0], [1.0, 1.0], [1.0, 0.0]])


@pytest.fixture
def grid():
    return np.meshgrid(np.linspace(0.0, 1.0, 5), np.linspace(0.0, 1.0, 5))


@pytest.mark.parametrize("function", [sampling.get_fieldline_distance, sampling.parse_segment])
@pytest.mark.parametrize("bad", NONFINITE)
@pytest.mark.parametrize("vertex", [0, 1, -1])
@pytest.mark.parametrize("coordinate", [0, 1])
def test_path_rejects_nonfinite_vertices(function, bad, vertex, coordinate, square):
    square[vertex, coordinate] = bad
    with pytest.raises(ValueError):
        function(square)


@pytest.mark.parametrize("bad", NONFINITE)
@pytest.mark.parametrize("endpoint", ["start_coord", "end_coord"])
@pytest.mark.parametrize("coordinate", [0, 1])
def test_parse_segment_rejects_nonfinite_endpoint_queries(bad, endpoint, coordinate, square):
    target = [0.0, 1.0]
    target[coordinate] = bad
    with pytest.raises(ValueError):
        sampling.parse_segment(square, **{endpoint: target})


@pytest.mark.parametrize("bad", NONFINITE)
def test_parse_segment_rejects_bad_vertex_even_beyond_requested_end(bad, square):
    square[-1, 0] = bad
    with pytest.raises(ValueError):
        sampling.parse_segment(square, start_coord=(0.0, 0.0), end_coord=(0.0, 0.0))


@pytest.mark.parametrize("function", NEAREST)
@pytest.mark.parametrize("bad", NONFINITE)
@pytest.mark.parametrize("query", [0, -1])
@pytest.mark.parametrize("coordinate", [0, 1])
def test_nearest_rejects_whole_query_batch(function, bad, query, coordinate, grid):
    x, y = grid
    queries = [[0.25, 0.25], [0.75, 0.75], [0.5, 0.5]]
    queries[query][coordinate] = bad
    with pytest.raises(ValueError):
        function(x, y, x + 2 * y, queries)


@pytest.mark.parametrize("function", NEAREST)
@pytest.mark.parametrize("bad", NONFINITE)
@pytest.mark.parametrize("sample", ["X", "Y", "Q"])
@pytest.mark.parametrize("index", [(0, 0), (2, 2), (-1, -1)])
def test_nearest_rejects_nonfinite_samples_even_when_not_selected(
    function, bad, sample, index, grid
):
    x, y = grid
    samples = {"X": x.copy(), "Y": y.copy(), "Q": x + 2 * y}
    samples[sample][index] = bad
    with pytest.raises(ValueError):
        function(**samples, coord_list=[(0.25, 0.25)])


@pytest.mark.parametrize("bad", NONFINITE)
@pytest.mark.parametrize("sample", ["x", "y"])
@pytest.mark.parametrize("index", [0, 2, -1])
@pytest.mark.parametrize("order", [0, 2])
def test_poly_fit_rejects_nonfinite_samples(bad, sample, index, order):
    samples = {"x": np.arange(4.0), "y": np.arange(4.0)}
    samples[sample][index] = bad
    with pytest.raises(ValueError):
        sampling.poly_fit(**samples, order=order)


@pytest.mark.parametrize("bad", NONFINITE)
@pytest.mark.parametrize("sample", ["Rho", "Z", "B", "Q"])
@pytest.mark.parametrize("index", [(0, 0), (2, 2), (-1, -1)])
def test_flux_rejects_nonfinite_grid_data(bad, sample, index, grid):
    x, y = grid
    samples = {"Rho": x.copy(), "Z": y.copy(), "B": np.ones_like(x), "Q": np.ones_like(x)}
    samples[sample][index] = bad
    with pytest.raises(ValueError):
        sampling.flux_surface_avg(**samples, flpoints=[[0.25, 0.5], [0.75, 0.5]])


@pytest.mark.parametrize("bad", NONFINITE)
@pytest.mark.parametrize("coordinate", [0, 1])
@pytest.mark.parametrize("vertex", [0, -1])
def test_flux_rejects_nonfinite_path(bad, coordinate, vertex, grid):
    x, y = grid
    path = np.array([[0.25, 0.5], [0.75, 0.5]])
    path[vertex, coordinate] = bad
    with pytest.raises(ValueError):
        sampling.flux_surface_avg(x, y, np.ones_like(x), path, np.ones_like(x))


@pytest.mark.parametrize("count", [1, 2, 3])
def test_zero_length_average_rejected_but_integral_remains_zero(count, grid):
    x, y = grid
    path = np.tile([0.5, 0.5], (count, 1))
    ones = np.ones_like(x)
    assert sampling.flux_surface_avg(x, y, ones, path) == 0.0
    with pytest.raises(ValueError):
        sampling.flux_surface_avg(x, y, ones, path, ones)


@pytest.mark.parametrize("function", NEAREST)
@pytest.mark.parametrize("dtype", [np.int16, np.float32, np.longdouble, np.complex128])
def test_nearest_preserves_order_ties_list_and_quantity_dtype(function, dtype, grid):
    x, y = grid
    q = np.arange(x.size).reshape(x.shape).astype(dtype)
    if np.issubdtype(dtype, np.complexfloating):
        q += 2j * q
    queries = iter([(0.75, 0.5), (0.125, 0.125), (0.25, 0.75)])
    values = function(x, y, q, queries)
    assert isinstance(values, list)
    assert all(value.dtype == q.dtype for value in values)
    np.testing.assert_array_equal(values, [q[2, 3], q[0, 0], q[3, 1]])
    assert function(x, y, q, []) == []


def test_geometric_nearest_still_supports_one_dimensional_samples():
    x = np.array([0.0, 1.0, 0.0])
    y = np.array([0.0, 0.0, 1.0])
    assert sampling.locs_to_vals1D(x, y, np.array([10, 20, 30]), [(0.1, 0.8)]) == [30]


def test_nearest_schemes_remain_distinct_on_irregular_coordinates():
    x = np.array([[0.0, 1.0], [0.4, 1.0]])
    y = np.array([[0.0, 0.0], [1.0, 0.6]])
    q = np.array([[10, 20], [30, 40]])
    assert sampling.locs_to_vals(x, y, q, [(0.6, 0.7)]) == [40]
    assert sampling.locs_to_vals1D(x, y, q, [(0.6, 0.7)]) == [30]


def test_distance_preserves_duplicate_vertices_and_no_implicit_closure():
    points = [[0.0, 0.0], [3.0, 0.0], [3.0, 0.0], [3.0, 4.0]]
    distances = sampling.get_fieldline_distance(points)
    assert isinstance(distances, np.ndarray)
    assert distances.shape == (4,)
    np.testing.assert_array_equal(distances, [0.0, 3.0, 3.0, 7.0])
    np.testing.assert_array_equal(sampling.get_fieldline_distance([[0.5, 0.5]]), [0.0])


@pytest.mark.parametrize("complex_values", [False, True])
def test_poly_fit_preserves_finite_coefficients_and_ascending_basis(complex_values):
    x = np.arange(4.0)
    expected = [1.0 + 2j, 2.0 - 1j, 0.5j] if complex_values else [1.0, 2.0, 0.5]
    y = expected[0] + expected[1] * x + expected[2] * x**2
    basis, coefficients = sampling.poly_fit(x, y, order=2)
    assert isinstance(basis, list) and len(basis) == 3
    assert coefficients.shape == (3,)
    assert np.iscomplexobj(coefficients) == complex_values
    np.testing.assert_allclose(coefficients, expected, rtol=0, atol=1e-14)
    np.testing.assert_array_equal([function(2.0) for function in basis], [1.0, 2.0, 4.0])


def test_finite_masked_quantities_keep_existing_selection_behavior(grid):
    x, y = grid
    q = np.ma.array(np.arange(x.size).reshape(x.shape), mask=np.eye(5, dtype=bool))
    queries = [(0.5, 0.5), (0.75, 0.5)]
    rectangular = sampling.locs_to_vals(x, y, q, queries)
    assert rectangular[0] is np.ma.masked
    assert rectangular[1] == q[2, 3]
    np.testing.assert_array_equal(sampling.locs_to_vals1D(x, y, q, queries), [12, 13])


@pytest.mark.parametrize("function", NEAREST)
@pytest.mark.parametrize("bad", NONFINITE)
def test_nearest_checks_masked_quantity_data(function, bad, grid):
    x, y = grid
    q = np.ma.array(np.ones_like(x), mask=np.eye(5, dtype=bool))
    q.data[2, 2] = bad
    with pytest.raises(ValueError):
        function(x, y, q, [(0.25, 0.75)])


@pytest.mark.parametrize("bad", NONFINITE)
def test_poly_fit_checks_masked_y_data(bad):
    y = np.ma.array(np.arange(4.0), mask=[False, False, True, False])
    y.data[2] = bad
    with pytest.raises(ValueError):
        sampling.poly_fit(np.arange(4.0), y, order=2)


@pytest.mark.parametrize("function", NEAREST)
@pytest.mark.parametrize("bad", NONFINITE)
def test_nearest_checks_imaginary_quantity_data(function, bad, grid):
    x, y = grid
    q = np.ones(x.shape, dtype=complex)
    q.imag[2, 2] = bad
    with pytest.raises(ValueError):
        function(x, y, q, [(0.25, 0.75)])


@pytest.mark.parametrize("bad", NONFINITE)
def test_poly_fit_checks_imaginary_y_data(bad):
    y = np.arange(4.0).astype(complex)
    y.imag[2] = bad
    with pytest.raises(ValueError):
        sampling.poly_fit(np.arange(4.0), y, order=2)


@pytest.mark.parametrize("bad", NONFINITE)
def test_poly_fit_checks_x_data_before_existing_real_conversion(bad):
    x = np.arange(4.0).astype(complex)
    x.imag[2] = bad
    with pytest.raises(ValueError):
        sampling.poly_fit(x, np.arange(4.0), order=2)


def test_poly_fit_preserves_finite_masked_x_constant_fit():
    x = np.ma.array(np.arange(4.0), mask=[False, False, True, False])
    basis, coefficients = sampling.poly_fit(x, np.arange(4.0), order=0)
    assert len(basis) == 1
    np.testing.assert_allclose(coefficients, [1.5], rtol=0, atol=1e-14)


@pytest.mark.parametrize("bad", NONFINITE)
@pytest.mark.parametrize("masked", [False, True])
def test_flux_checks_quantity_data_before_spline_conversion(bad, masked, grid):
    x, y = grid
    q = np.ones(x.shape, dtype=complex)
    q.imag[2, 2] = bad
    if masked:
        q = np.ma.array(q, mask=np.eye(5, dtype=bool))
    with pytest.raises(ValueError):
        sampling.flux_surface_avg(x, y, np.ones_like(x), [[0.25, 0.5], [0.75, 0.5]], q)


def test_flux_keeps_existing_finite_masked_quantity_conversion(grid):
    x, y = grid
    q = np.ma.array(1 + 2 * x, mask=np.eye(5, dtype=bool))
    result = sampling.flux_surface_avg(x, y, np.ones_like(x), [[0.0, 0.5], [1.0, 0.5]], q)
    np.testing.assert_allclose(result, 2.0, rtol=0, atol=1e-14)


def test_flux_preserves_positive_length_integral_and_average_with_duplicate_vertex(grid):
    x, y = grid
    path = [[0.0, 0.5], [0.5, 0.5], [0.5, 0.5], [1.0, 0.5]]
    b = 2 * np.ones_like(x)
    integral = sampling.flux_surface_avg(x, y, b, path)
    average = sampling.flux_surface_avg(x, y, b, path, 1 + 2 * x)
    assert np.ndim(integral) == np.ndim(average) == 0
    np.testing.assert_allclose(integral, 0.5, rtol=0, atol=1e-14)
    np.testing.assert_allclose(average, 2.0, rtol=0, atol=1e-14)


def _reused_queries(pairs, dtype, counts, scalar_arrays=False):
    counts["starts"] += 1
    point = (
        [np.empty((), dtype=dtype), np.empty((), dtype=dtype)]
        if scalar_arrays
        else np.empty(2, dtype=dtype)
    )
    try:
        for pair in pairs:
            if scalar_arrays:
                for component, value in zip(point, pair):
                    component[...] = value
            else:
                point[:] = pair
            counts["yields"] += 1
            yield point
    finally:
        counts["finished"] += 1


@pytest.mark.parametrize("function", NEAREST)
@pytest.mark.parametrize("dtype", [np.float32, np.longdouble, object])
@pytest.mark.parametrize("scalar_arrays", [False, True])
def test_v2_nearest_snapshots_reused_query_buffer_once(function, dtype, scalar_arrays):
    x, y = np.meshgrid([0.0, 1.0], [0.0, 1.0])
    q = np.array([[10, 20], [30, 40]], dtype=np.int16)
    counts = {"starts": 0, "yields": 0, "finished": 0}
    queries = _reused_queries([(0.0, 0.0), (1.0, 0.0)], dtype, counts, scalar_arrays)
    values = function(x, y, q, queries)
    assert isinstance(values, list)
    np.testing.assert_array_equal(values, [10, 20])
    assert all(type(value) is np.int16 for value in values)
    assert counts == {"starts": 1, "yields": 2, "finished": 1}


@pytest.mark.parametrize("function", NEAREST)
@pytest.mark.parametrize("bad", NONFINITE)
@pytest.mark.parametrize("coordinate", [0, 1])
@pytest.mark.parametrize("scalar_arrays", [False, True])
def test_v2_nearest_rejects_query_before_reused_buffer_can_hide_it(
    function, bad, coordinate, scalar_arrays
):
    x, y = np.meshgrid([0.0, 1.0], [0.0, 1.0])
    q = np.array([[10, 20], [30, 40]])
    first = [0.0, 0.0]
    first[coordinate] = bad
    counts = {"starts": 0, "yields": 0, "finished": 0}
    queries = _reused_queries([first, (1.0, 0.0)], np.float64, counts, scalar_arrays)
    with pytest.raises(ValueError):
        function(x, y, q, queries)
    assert counts["starts"] == 1
    assert counts["yields"] == 1
    queries.close()
    assert counts["finished"] == 1


OBJECT_CASES = ["poly_x", "poly_y", "rectangular_Q", "geometric_Q", "parse_points", "flux_Q"]


def _object_input_case(case, grid, square):
    x, y = grid
    if case in ("poly_x", "poly_y"):
        args = [np.arange(4.0), 1.0 + 2.0 * np.arange(4.0)]
        index = 0 if case == "poly_x" else 1
        args[index] = args[index].astype(object)
        return sampling.poly_fit, args, {"order": 1}, args[index]
    if case in ("rectangular_Q", "geometric_Q"):
        q = (1.0 + x).astype(object)
        function = sampling.locs_to_vals if case == "rectangular_Q" else sampling.locs_to_vals1D
        return function, [x, y, q, [(0.0, 0.0), (1.0, 0.0)]], {}, q
    if case == "parse_points":
        points = square.astype(object)
        return sampling.parse_segment, [points], {}, points
    q = (1.0 + x).astype(object)
    return sampling.flux_surface_avg, [x, y, np.ones_like(x), [[0.0, 0.5], [1.0, 0.5]], q], {}, q


@pytest.mark.parametrize("case", OBJECT_CASES)
def test_v2_preserves_six_original_finite_object_inputs(case, grid, square):
    function, args, kwargs, data = _object_input_case(case, grid, square)
    result = function(*args, **kwargs)
    if case in ("poly_x", "poly_y"):
        basis, coefficients = result
        assert len(basis) == 2
        assert coefficients.dtype == (object if case == "poly_y" else np.dtype(float))
        np.testing.assert_allclose(list(coefficients), [1.0, 2.0], rtol=0, atol=1e-14)
    elif case in ("rectangular_Q", "geometric_Q"):
        assert result == [1.0, 2.0]
        assert all(type(value) is float for value in result)
    elif case == "parse_points":
        assert result.dtype == object
        np.testing.assert_array_equal(result, square)
    else:
        np.testing.assert_allclose(result, 1.5, rtol=0, atol=1e-14)
    assert data.dtype == object


@pytest.mark.parametrize("case", OBJECT_CASES)
@pytest.mark.parametrize("bad", NONFINITE)
@pytest.mark.parametrize("imaginary", [False, True])
def test_v2_rejects_nonfinite_object_elements(case, bad, imaginary, grid, square):
    function, args, kwargs, data = _object_input_case(case, grid, square)
    data.flat[data.size // 2] = complex(1.0, bad) if imaginary else bad
    with pytest.raises(ValueError):
        function(*args, **kwargs)


@pytest.mark.parametrize("function", NEAREST)
@pytest.mark.parametrize("factory", [int, float, complex, Decimal, Fraction, np.float32])
def test_v2_nearest_preserves_numeric_object_element_type(function, factory):
    x, y = np.meshgrid([0.0, 1.0], [0.0, 1.0])
    q = np.array([[factory(10), factory(20)], [factory(30), factory(40)]], dtype=object)
    result = function(x, y, q, [(0.0, 0.0), (1.0, 0.0)])
    assert result == [factory(10), factory(20)]
    assert all(type(value) is type(q[0, 0]) for value in result)


@pytest.mark.parametrize("function", NEAREST)
def test_v2_nearest_keeps_large_exact_object_integers(function):
    x, y = np.meshgrid([0.0, 1.0], [0.0, 1.0])
    first = 10**400
    q = np.array([[first, first + 1], [first + 2, first + 3]], dtype=object)
    result = function(x, y, q, [(0.0, 0.0), (1.0, 0.0)])
    assert result == [first, first + 1]
    assert all(type(value) is int for value in result)


@pytest.mark.parametrize("function", NEAREST)
@pytest.mark.parametrize(
    "bad", [Decimal("NaN"), Decimal("sNaN"), Decimal("Infinity"), Decimal("-Infinity")]
)
def test_v2_nearest_rejects_nonfinite_decimal_elements(function, bad):
    x, y = np.meshgrid([0.0, 1.0], [0.0, 1.0])
    q = np.array([[Decimal(10), bad], [Decimal(30), Decimal(40)]], dtype=object)
    with pytest.raises(ValueError):
        function(x, y, q, [(0.0, 0.0)])


@pytest.mark.parametrize("function", NEAREST)
def test_v2_nearest_preserves_finite_masked_object_quantities(function):
    x, y = np.meshgrid([0.0, 1.0], [0.0, 1.0])
    q = np.ma.array(np.array([[10, 20], [30, 40]], dtype=object), mask=[[1, 0], [0, 0]])
    result = function(x, y, q, [(0.0, 0.0), (1.0, 0.0)])
    assert result[0] is np.ma.masked if function is sampling.locs_to_vals else result[0] == 10
    assert type(result[1]) is int and result[1] == 20


@pytest.mark.parametrize("function", NEAREST)
@pytest.mark.parametrize("bad", NONFINITE)
def test_v2_nearest_checks_masked_object_quantity_data(function, bad):
    x, y = np.meshgrid([0.0, 1.0], [0.0, 1.0])
    q = np.ma.array(np.array([[bad, 20], [30, 40]], dtype=object), mask=[[1, 0], [0, 0]])
    with pytest.raises(ValueError):
        function(x, y, q, [(1.0, 0.0)])


def test_v2_does_not_add_support_for_object_flux_paths(grid):
    x, y = grid
    path = np.array([[0.0, 0.5], [1.0, 0.5]], dtype=object)
    with pytest.raises(TypeError):
        sampling.flux_surface_avg(x, y, np.ones_like(x), path, np.ones_like(x))
