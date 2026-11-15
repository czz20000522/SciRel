"""Independent numerical regressions for geometric nearest sampling (#250)."""

from decimal import Decimal, localcontext
from fractions import Fraction

import numpy as np
import pytest

from scirel.geometry import sampling
from scirel.geometry.sampling import locs_to_vals1D


@pytest.mark.parametrize("scale", [1.0, 1e155, 1e-170])
def test_geometric_nearest_is_invariant_under_uniform_coordinate_scale(scale):
    x, y = np.meshgrid(np.array([0.0, 2.0, 3.0]) * scale, np.array([0.0, 1.0]) * scale)
    q = np.array([[10.0, 20.0, 30.0], [40.0, 50.0, 60.0]])
    point = (2.75 * scale, 0.75 * scale)
    # Each axis is uniquely nearest at (3, 1); hypot is a separate stable reference.
    reference_index = np.hypot(x - point[0], y - point[1]).argmin()
    assert reference_index == 5
    with np.errstate(over="ignore", under="ignore", invalid="ignore"):
        actual = locs_to_vals1D(x, y, q, [point])
    assert actual == [60.0], (scale, actual)


@pytest.mark.parametrize(
    "x,y,query,expected",
    [
        # Both coordinate differences overflow; the other points enclose the query.
        ([1e308, 9e307, -1.7e308, -1.7e308], [0.0, 0.0, 1.79e308, -1.79e308], (-1e308, 0.0), 1),
        # hypot rounds unequal distances to the same number.
        ([1.0, 1.0], [2.0**-26, 0.0], (0.0, 0.0), 1),
        # Subtraction itself rounds unequal distances to the same number.
        ([0.0, 1.0], [0.0, 0.0], (1e16, 0.0), 1),
        # Subnormal distances also round together.
        ([5e-324, 5e-324], [5e-324, 0.0], (0.0, 0.0), 1),
        ([1.0, 0.0], [0.0, 1.0], (0.0, 0.0), 0),
        ([1e308, 0.0], [0.0, 1e308], (0.0, 0.0), 0),
    ],
    ids=[
        "subtraction-overflow",
        "rounded-hypot",
        "rounded-subtraction",
        "subnormal",
        "tie",
        "large-tie",
    ],
)
def test_extreme_and_rounded_distances_match_independent_decimal_reference(x, y, query, expected):
    # Exact binary64 -> decimal conversion; 2200 digits cover these finite fixtures,
    # including squaring subnormal coordinates. No SciRel result defines the oracle.
    with localcontext() as context:
        context.prec = 2200
        px, py = map(Decimal.from_float, query)
        squared = [
            (Decimal.from_float(sx) - px) ** 2 + (Decimal.from_float(sy) - py) ** 2
            for sx, sy in zip(x, y)
        ]
        assert min(range(len(squared)), key=squared.__getitem__) == expected
    with np.errstate(all="raise"):
        assert locs_to_vals1D(np.array(x), np.array(y), np.arange(len(x)), [query]) == [expected]


@pytest.mark.parametrize("shape", [(6,), (2, 3), (1, 2, 3)])
@pytest.mark.parametrize("dtype", [np.float32, np.float64, np.longdouble])
def test_matching_shapes_query_order_and_selected_types(shape, dtype):
    x = np.array([0, 2, 3, 0, 2, 3], dtype=dtype).reshape(shape)
    y = np.array([0, 0, 0, 1, 1, 1], dtype=dtype).reshape(shape)
    q = np.arange(6, dtype=np.complex128).reshape(shape) * (1 + 2j)
    queries = ((dtype(a), dtype(b)) for a, b in [(2.75, 0.75), (0, 0), (2.75, 0.75)])
    actual = locs_to_vals1D(x, y, q, queries)
    assert actual == [q.flat[5], q.flat[0], q.flat[5]]
    assert all(type(value) is np.complex128 for value in actual)


@pytest.mark.parametrize("dtype", [np.int64, np.uint64, object])
def test_integer_coordinates_keep_units_beyond_float_precision(dtype):
    base = 2**62
    x = np.array([base, base + 1, base + 2], dtype=dtype)
    y = np.zeros(3, dtype=dtype)
    assert locs_to_vals1D(x, y, np.array([10, 20, 30]), [(base + 1, 0)]) == [20]


@pytest.mark.parametrize("factory", [float, Decimal, Fraction])
@pytest.mark.parametrize("scale", ["1e155", "1e-170"])
def test_numeric_object_coordinates_are_not_coerced_to_float64(factory, scale):
    unit = factory(scale)
    x = np.array([factory(0), 2 * unit, 3 * unit], dtype=object)
    y = np.array([factory(0)] * 3, dtype=object)
    q = np.array([Decimal(10), Decimal(20), Decimal(30)], dtype=object)
    actual = locs_to_vals1D(x, y, q, [(3 * unit, factory(0))])
    assert actual == [Decimal(30)]
    assert type(actual[0]) is Decimal


def test_object_fraction_coordinates_keep_distinctions_lost_by_float64():
    delta = Fraction(1, 10**400)
    x = np.array([1 + delta, Fraction(1)], dtype=object)
    y = np.array([Fraction(0), Fraction(0)], dtype=object)
    assert locs_to_vals1D(x, y, np.array([10, 20]), [(Fraction(0), Fraction(0))]) == [20]


def test_decimal_coordinates_keep_distinctions_beyond_decimal_context_precision():
    x = np.array([Decimal("1." + "0" * 399 + "1"), Decimal(1)], dtype=object)
    y = np.array([Decimal(0), Decimal(0)], dtype=object)
    assert locs_to_vals1D(x, y, np.array([10, 20]), [(Decimal(0), Decimal(0))]) == [20]


def test_longdouble_coordinates_are_not_narrowed():
    unit = np.longdouble(1)
    x = np.array([np.nextafter(unit, np.longdouble(np.inf)), unit], dtype=np.longdouble)
    y = np.zeros(2, dtype=np.longdouble)
    assert locs_to_vals1D(x, y, np.array([10, 20]), [(unit, unit * 0)]) == [20]


@pytest.mark.parametrize("dtype", [float, object])
def test_existing_masked_coordinate_selection_is_preserved(dtype):
    x = np.ma.array(np.array([0, 1, 2], dtype=dtype), mask=[True, False, False])
    y = np.zeros(3, dtype=dtype)
    assert locs_to_vals1D(x, y, np.array([10, 20, 30]), [(0.0, 0.0)]) == [20]
    x.mask = True
    assert locs_to_vals1D(x, y, np.array([10, 20, 30]), [(0.0, 0.0)]) == [10]


@pytest.mark.parametrize("scale", [1e-300, 1e-170, 1.0, 1e155, 1e307])
def test_seeded_scattered_cloud_matches_independent_decimal_reference(scale):
    generator = np.random.default_rng(250)
    samples = generator.uniform(-1, 1, (32, 2)) * scale
    queries = generator.uniform(-0.5, 0.5, (8, 2)) * scale
    with localcontext() as context:
        context.prec = 2200
        points = [tuple(map(Decimal.from_float, point)) for point in samples]
        expected = []
        for query in queries:
            px, py = map(Decimal.from_float, query)
            squared = [(sx - px) ** 2 + (sy - py) ** 2 for sx, sy in points]
            expected.append(min(range(len(squared)), key=squared.__getitem__))
    with np.errstate(all="raise"):
        actual = locs_to_vals1D(samples[:, 0], samples[:, 1], np.arange(32), iter(queries))
    assert actual == expected


@pytest.mark.parametrize("position", ["X", "Y", "query_x", "query_y"])
@pytest.mark.parametrize("dtype", [np.complex128, object])
@pytest.mark.parametrize("imaginary", [0.0, 1.0])
def test_complex_coordinates_rejected_even_with_zero_imaginary_part(position, dtype, imaginary):
    arrays = {"X": np.array([0.0, 1.0]), "Y": np.array([0.0, 0.0])}
    queries = [[0.0, 0.0], [1.0, 0.0]]
    if position in arrays:
        arrays[position] = arrays[position].astype(dtype)
        arrays[position][0] = complex(0.0, imaginary)
    else:
        queries[0] = np.array(queries[0], dtype=dtype)
        queries[0][0 if position == "query_x" else 1] = complex(0.0, imaginary)
    with pytest.raises(ValueError, match="real"):
        locs_to_vals1D(arrays["X"], arrays["Y"], np.array([10, 20]), iter(queries))


@pytest.mark.parametrize("position", ["X", "Y"])
def test_complex_sample_coordinates_rejected_even_without_queries(position):
    arrays = {"X": np.array([0.0, 1.0]), "Y": np.array([0.0, 0.0])}
    arrays[position] = arrays[position].astype(complex)
    with pytest.raises(ValueError, match="real"):
        locs_to_vals1D(arrays["X"], arrays["Y"], np.array([10, 20]), [])


@pytest.mark.parametrize("dtype", [np.complex128, object])
def test_real_coordinates_still_preserve_complex_quantity_values(dtype):
    q = np.array([1 + 2j, 3 - 4j], dtype=dtype)
    actual = locs_to_vals1D(np.array([0.0, 1.0]), np.zeros(2), q, [(1.0, 0.0)])
    assert actual == [q[1]]
    assert type(actual[0]) is type(q[1])


def test_nearest_does_not_depend_on_hypot_rounding(monkeypatch):
    # A distorted library norm must not affect a selector using basic operations.
    monkeypatch.setattr(np, "hypot", lambda *args: np.array([0.0, 1.0]))
    actual = locs_to_vals1D(np.array([1.0, 0.0]), np.zeros(2), np.array([10, 20]), [(0.0, 0.0)])
    assert actual == [20]


@pytest.mark.parametrize(
    "samples,query",
    [
        (([0.0, 1.0, -1.0, 10.0], [0.0, 1.0, -1.0, 10.0]), (0.1, 0.2)),
        (([1.0, 1.0], [2.0**-26, 0.0]), (0.0, 0.0)),
        (([0.0, 1.0], [0.0, 0.0]), (1e16, 0.0)),
        (([1e308, 9e307, -1.7e308, -1.7e308], [0.0, 0.0, 1.79e308, -1.79e308]), (-1e308, 0.0)),
        (([1e155, 2e155, -3e155], [2e155, 0.0, 1e155]), (0.0, 0.0)),
        (([1e154, 1e154], [1e154, 0.0]), (0.0, 0.0)),
        (([5e-324, 5e-324, 1.0], [5e-324, 0.0, 1.0]), (0.0, 0.0)),
        (([1.0, 0.0, -1.0], [0.0, 1.0, 0.0]), (0.0, 0.0)),
    ],
    ids=[
        "normal",
        "rounded-norm",
        "rounded-subtraction",
        "subtraction-overflow",
        "square-overflow",
        "sum-overflow",
        "underflow",
        "ties",
    ],
)
def test_intervals_enclose_exact_distances_and_retain_every_true_minimizer(samples, query):
    x, y = map(np.array, samples)
    px, py = map(Fraction, query)
    squared = [(Fraction(sx) - px) ** 2 + (Fraction(sy) - py) ** 2 for sx, sy in zip(x, y)]
    with np.errstate(all="raise"):
        lower, upper = sampling._squared_distance_bounds(x, y, *query)
    assert lower.shape == upper.shape == x.shape
    for lo, distance, hi in zip(lower, squared, upper):
        assert np.isfinite(lo) and 0 <= Fraction(lo) <= distance
        assert hi == np.inf or distance <= Fraction(hi)
    retained = lower <= upper.min()
    for index, distance in enumerate(squared):
        if distance == min(squared):
            assert retained[index]


def test_normal_interval_filter_can_exclude_provably_far_samples():
    lower, upper = sampling._squared_distance_bounds(
        np.array([0.0, 10.0, 20.0]), np.zeros(3), 0.1, 0.0
    )
    np.testing.assert_array_equal(lower <= upper.min(), [True, False, False])


def test_overlapping_intervals_are_resolved_by_exact_distances(monkeypatch):
    monkeypatch.setattr(
        sampling, "_squared_distance_bounds", lambda *args: (np.zeros(3), np.full(3, np.inf))
    )
    actual = locs_to_vals1D(
        np.array([1.0, 0.0, 0.0]), np.zeros(3), np.array([10, 20, 30]), [(0.0, 0.0)]
    )
    assert actual == [20]


@pytest.mark.parametrize(
    "case",
    [
        "integer-samples",
        "object-samples",
        "fraction-query",
        "decimal-query",
        "inexact-integer-query",
    ],
)
def test_nonfloat_or_inexact_conversions_bypass_the_interval_filter(monkeypatch, case):
    def forbidden_filter(*args):
        raise AssertionError("an inexact or nonfloat conversion entered the interval filter")

    monkeypatch.setattr(sampling, "_squared_distance_bounds", forbidden_filter)
    expected = 20
    if case == "integer-samples":
        x, y, query = np.array([2**62, 2**62 + 1]), np.zeros(2, dtype=int), (2**62 + 1, 0)
    elif case == "object-samples":
        x = np.array([1 + Fraction(1, 10**400), Fraction(1)], dtype=object)
        y, query = np.zeros(2, dtype=object), (Fraction(0), Fraction(0))
    elif case in ("fraction-query", "decimal-query"):
        x, y = np.array([-1.0, 1.0]), np.zeros(2)
        query = (Fraction(1, 10**400) if case == "fraction-query" else Decimal("1e-400"), 0)
    else:
        x, y, query = np.array([2**53 + 2.0, 2**53], dtype=float), np.zeros(2), (2**53 + 1, 0)
        expected = 10  # Exact midpoint: retain the first sample, not a rounded query.
    assert locs_to_vals1D(x, y, np.array([10, 20]), [query]) == [expected]
