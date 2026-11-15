"""Independent numerical regressions for geometric nearest sampling (#250)."""

from decimal import Decimal, localcontext
from fractions import Fraction

import numpy as np
import pytest

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
