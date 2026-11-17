"""Independent evidence for the two nearest-sample field queries.

Assets:

* ``scirel.geometry.rectangular-nearest`` (``locs_to_vals``)
* ``scirel.geometry.point-nearest`` (``locs_to_vals1D``)

Both relations answer the same question — *which stored sample is nearest?* —
by different rules: the rectangular scheme chooses a column and a row
independently, the geometric scheme minimises the Euclidean distance over the
flattened samples.  The evidence below separates the two rules and pins each
one against an oracle that enumerates every sample:

1. **Index encoding.**  ``Q[iy, ix] = 100 * iy + ix`` makes the returned value a
   lossless encoding of the selected index pair, so the assertion is on the
   *choice*, not on a floating value.  A rule that returned a neighbouring cell
   or the wrong axis order is visible immediately, and a constant response
   cannot pass because the expected codes differ per query.
2. **Exhaustive rational oracle (geometric).**  The nearest flattened sample is
   recomputed with :class:`fractions.Fraction` squared distances over all
   samples, with the documented first-sample tie rule derived from that
   enumeration alone.  Comparisons are exact; no tolerance is involved.
3. **Rules must differ on irregular input.**  The same irregular cloud is
   queried through both schemes: the axis-separable rule and the Euclidean rule
   are *required* to disagree there, which is what the contracts state as a
   limitation.  Agreement on a regular grid is asserted separately.
4. **Exact tie and near-tie behaviour.**  An exact midpoint on a grid axis and a
   pair of samples whose squared distances differ below binary64 resolution both
   have a determinate answer under the two rules; both are asserted exactly.

Defect probes: returning ``0`` fails the index encodings; returning the input
unchanged fails the type/selection assertions; a wrong-magnitude constant fails
the codes; picking the far axis fails the independent axis-argmin comparison.

Boundary cases asserted here: a single-sample cloud, a single-row grid, a query
outside the sampled range (clamped), a fully masked coordinate array, and an
exact tie.  Non-finite input, complex coordinates and malformed field shapes are
covered as one executable assertion per rejection channel.

**Not established here:** the universal soundness of the geometric scheme's
private interval pre-filter (that it can never discard a true minimiser).  The
tests below check it on constructed near-tie cases only; a proof, or a
proof-carrying implementation, is outside what a test can supply.  Recorded as
``cannot establish`` in the contract.
"""

from __future__ import annotations

from fractions import Fraction

import numpy as np
import pytest

from scirel.geometry.sampling import locs_to_vals, locs_to_vals1D

# ---------------------------------------------------------------------------
# exact helpers
# ---------------------------------------------------------------------------


def _exact(value) -> Fraction:
    return Fraction(*float(value).as_integer_ratio())


def _encoded_grid(xs, ys):
    """Grid with ``Q[iy, ix] = 100 * iy + ix``, so a value names its cell."""
    x, y = np.meshgrid(np.asarray(xs, dtype=float), np.asarray(ys, dtype=float))
    rows = np.arange(len(ys))[:, None]
    columns = np.arange(len(xs))[None, :]
    return x, y, 100.0 * rows + columns


def _nearest_axis(values, query) -> int:
    """Exact nearest index on one monotone axis; ties keep the lower index."""
    target = _exact(query)
    return min(range(len(values)), key=lambda index: (abs(_exact(values[index]) - target), index))


def _exact_nearest_flat(samples, query) -> int:
    """Exhaustive rational nearest flattened sample; ties keep the first."""
    qx, qy = _exact(query[0]), _exact(query[1])
    best_index, best = 0, None
    for index, (x, y) in enumerate(samples):
        distance = (_exact(x) - qx) ** 2 + (_exact(y) - qy) ** 2
        if best is None or distance < best:
            best_index, best = index, distance
    return best_index


# ---------------------------------------------------------------------------
# rectangular-nearest
# ---------------------------------------------------------------------------

XS = [0.0, 0.5, 1.0, 2.0]
YS = [-1.0, 0.0, 3.0]


@pytest.mark.parametrize(
    "query",
    [
        (0.0, -1.0),  # exact grid corner
        (2.0, 3.0),  # opposite corner
        (0.4, -0.2),  # column 1 and row 1, not the origin
        (1.9, 2.4),  # last column and last row
        (0.5, 0.0),  # exactly on a stored column
        (1.25, 1.4),
    ],
)
def test_rectangular_nearest_selects_the_independently_nearest_axes(query):
    """Selected cell equals the exact axis-wise argmin pair, encoded in the value."""
    x, y, q = _encoded_grid(XS, YS)
    ix, iy = _nearest_axis(XS, query[0]), _nearest_axis(YS, query[1])
    expected = 100.0 * iy + ix
    selected = locs_to_vals(x, y, q, [query])
    assert selected == [expected]
    # And the returned value really is that stored cell, not an interpolated number.
    assert selected[0] == q[iy, ix]


def test_rectangular_nearest_answer_battery_is_not_a_constant():
    """Guard the fixture: a response that always returned 0 (or one code) cannot pass."""
    x, y, q = _encoded_grid(XS, YS)
    queries = [(0.0, -1.0), (2.0, 3.0), (0.4, -0.2), (1.9, 2.4), (0.5, 0.0), (1.25, 1.4)]
    answers = locs_to_vals(x, y, q, queries)
    expected = [
        100.0 * _nearest_axis(YS, query[1]) + _nearest_axis(XS, query[0]) for query in queries
    ]
    assert answers == expected
    assert len(set(expected)) > 1
    assert 0.0 in expected and any(value != 0.0 for value in expected)


def test_rectangular_nearest_half_way_tie_keeps_the_lower_column():
    """A query exactly between two columns resolves to the lower index."""
    x, y, q = _encoded_grid([0.0, 1.0], [0.0])
    # |0.0 - 0.5| == |1.0 - 0.5| exactly; argmin keeps the first column.
    assert locs_to_vals(x, y, q, [(0.5, 0.0)]) == [0.0]
    # Just past the midpoint the choice flips, so the tie is not always 0.
    assert locs_to_vals(x, y, q, [(0.75, 0.0)]) == [1.0]


def test_rectangular_nearest_clamps_queries_outside_the_sampled_range():
    """Outside queries still answer: the scheme is a nearest lookup, not a hull test."""
    x, y, q = _encoded_grid(XS, YS)
    assert locs_to_vals(x, y, q, [(-100.0, 100.0)]) == [200.0]  # first column, last row
    assert locs_to_vals(x, y, q, [(100.0, -100.0)]) == [3.0]  # last column, first row


def test_rectangular_nearest_preserves_query_order_and_duplicates():
    """Result order follows the query list, duplicates included."""
    x, y, q = _encoded_grid(XS, YS)
    queries = [(0.0, -1.0), (2.0, 3.0), (0.0, -1.0)]
    assert locs_to_vals(x, y, q, queries) == [0.0, 203.0, 0.0]


def test_rectangular_nearest_keeps_the_selected_sample_type():
    """Integer fields stay integers: the scheme selects, it does not convert."""
    x, y = np.meshgrid(np.array([0.0, 1.0]), np.array([0.0, 1.0]))
    q = np.arange(4, dtype=np.int32).reshape(2, 2)
    selected = locs_to_vals(x, y, q, [(1.0, 1.0)])
    assert selected == [3]
    assert np.asarray(selected[0]).dtype == np.int32


def test_rectangular_nearest_agrees_with_the_geometric_scheme_on_a_regular_grid():
    """On a separable grid both schemes choose the same sample (their stated limit)."""
    x, y, q = _encoded_grid(XS, YS)
    queries = [(0.05, -0.95), (1.4, 1.1), (2.0, 3.0), (0.46, -0.04)]
    rectangular = locs_to_vals(x, y, q, queries)
    geometric = locs_to_vals1D(x, y, q, queries)
    assert rectangular == geometric


def test_rectangular_nearest_rejects_nonfinite_inputs():
    """invalid_input channel: samples, field and queries are validated first."""
    x, y, q = _encoded_grid(XS, YS)
    bad_x = x.copy()
    bad_x[0, 0] = np.inf
    with pytest.raises(ValueError):
        locs_to_vals(bad_x, y, q, [(0.0, 0.0)])
    bad_q = q.copy()
    bad_q[1, 1] = np.nan
    with pytest.raises(ValueError):
        locs_to_vals(x, y, bad_q, [(0.0, 0.0)])
    with pytest.raises(ValueError):
        locs_to_vals(x, y, q, [(np.nan, 0.0)])


def test_rectangular_nearest_propagates_a_malformed_field_shape():
    """runtime_failure channel: an unusable field raises instead of being repaired."""
    x, y, _ = _encoded_grid(XS, YS)
    with pytest.raises(IndexError):
        locs_to_vals(x, y, np.zeros(len(XS)), [(0.0, 0.0)])


def test_rectangular_nearest_returns_no_partial_result_on_rejection():
    """partial_results channel: a rejected batch yields nothing at all."""
    x, y, q = _encoded_grid(XS, YS)
    result = None
    with pytest.raises(ValueError):
        result = locs_to_vals(x, y, q, [(0.0, 0.0), (np.inf, 0.0)])
    assert result is None


# ---------------------------------------------------------------------------
# point-nearest
# ---------------------------------------------------------------------------

CLOUD_X = np.array([0.0, 2.0, 2.0, -1.0, 3.0, 0.5])
CLOUD_Y = np.array([0.0, 0.0, 1.0, 2.0, -1.0, 0.25])
CLOUD_Q = np.arange(CLOUD_X.size, dtype=float)


@pytest.mark.parametrize(
    "query",
    [
        (0.1, 0.1),
        (1.2, 0.6),
        (2.4, 0.4),
        (-0.9, 1.9),
        (10.0, -10.0),
        (0.5, 0.25),
        (1.0, 0.5),
    ],
)
def test_point_nearest_matches_the_exhaustive_rational_minimum(query):
    """Selected sample index equals the exact Fraction minimiser over all samples."""
    expected = _exact_nearest_flat(zip(CLOUD_X, CLOUD_Y), query)
    selected = locs_to_vals1D(CLOUD_X, CLOUD_Y, CLOUD_Q, [query])
    assert selected == [float(expected)]


def test_point_nearest_keeps_the_first_of_exactly_equidistant_samples():
    """Two duplicated coordinates are an exact tie; the first listed sample wins."""
    x = np.array([1.0, 1.0, 5.0])
    y = np.array([1.0, 1.0, 5.0])
    q = np.array([10.0, 20.0, 30.0])
    assert _exact_nearest_flat(zip(x, y), (0.0, 0.0)) == 0
    assert locs_to_vals1D(x, y, q, [(0.0, 0.0)]) == [10.0]


def test_point_nearest_resolves_a_tie_binary64_rounding_hides():
    """Subtraction rounds both differences to 1e16, so only exact arithmetic decides.

    The samples are ``(0, 0)`` and ``(1, 0)`` and the query is ``(1e16, 0)``.  The
    exact squared distances are ``1e32`` and ``(1e16 - 1)**2``, so the second
    sample is strictly nearer, while a float64 ``|x - qx|`` collapses both
    differences to ``1e16`` and would keep the first.
    """
    x = np.array([0.0, 1.0])
    y = np.array([0.0, 0.0])
    q = np.array([7.0, 9.0])
    query = (1e16, 0.0)
    # The float64 difference cannot separate the samples ...
    assert np.array_equal(np.abs(x - query[0]), [1e16, 1e16])
    assert np.argmin(np.abs(x - query[0]) ** 2 + np.abs(y - query[1]) ** 2) == 0
    # ... while the exact minimiser is the second sample, and that is returned.
    assert _exact_nearest_flat(zip(x, y), query) == 1
    assert locs_to_vals1D(x, y, q, [query]) == [9.0]


def test_point_nearest_on_a_single_sample_is_that_sample():
    """n=1 boundary: the only sample is returned for every query."""
    assert locs_to_vals1D(
        np.array([3.0]), np.array([4.0]), np.array([42.0]), [(0.0, 0.0), (9.0, 9.0)]
    ) == [
        42.0,
        42.0,
    ]


def test_point_nearest_skips_masked_samples():
    """A masked sample is not a candidate; the remaining ones are."""
    x = np.array([0.0, 1.0, 2.0])
    y = np.array([0.0, 0.0, 0.0])
    q = np.array([0.0, 1.0, 2.0])
    masked_x = np.ma.array(x, mask=[True, False, False])
    masked_y = np.ma.array(y, mask=[True, False, False])
    assert locs_to_vals1D(masked_x, masked_y, q, [(0.9, 0.0)]) == [1.0]
    # Every coordinate masked: the documented masked-argmin answer is index 0.
    fully = np.ma.array(x, mask=[True, True, True])
    assert locs_to_vals1D(fully, fully, q, [(0.0, 0.0)]) == [0.0]


def test_point_nearest_differs_from_the_rectangular_rule_on_irregular_input():
    """On a non-separable cloud the two documented rules select different samples.

    ``X`` and ``Y`` vary along both axes, so the axes are not a product grid and
    the contracts state only that the two schemes need not agree.  The expected
    values are computed here from the two rules' own definitions: column/row
    argmin for the rectangular scheme, and the exhaustive rational minimum for
    the geometric one.
    """
    x = np.array([[0.0, 1.0], [0.4, 1.0]])
    y = np.array([[0.0, 0.0], [1.0, 0.6]])
    q = np.array([[10.0, 20.0], [30.0, 40.0]])
    query = (0.6, 0.7)

    column = _nearest_axis(x[0, :], query[0])
    row = _nearest_axis(y[:, 0], query[1])
    rectangular_expected = q[row, column]
    flat = list(zip(x.ravel(), y.ravel()))
    geometric_expected = q.ravel()[_exact_nearest_flat(flat, query)]

    assert rectangular_expected != geometric_expected  # the fixture is discriminating
    assert locs_to_vals(x, y, q, [query]) == [rectangular_expected]
    assert locs_to_vals1D(x, y, q, [query]) == [geometric_expected]


def test_point_nearest_rejects_complex_coordinates_and_nonfinite_data():
    """invalid_input channel: complex coordinates are rejected even with zero part."""
    x = np.array([0.0, 1.0])
    y = np.array([0.0, 1.0])
    q = np.array([1.0, 2.0])
    with pytest.raises(ValueError):
        locs_to_vals1D(x.astype(complex), y, q, [(0.0, 0.0)])
    with pytest.raises(ValueError):
        locs_to_vals1D(x, y, q, [(np.inf, 0.0)])
    bad_q = np.array([1.0, np.nan])
    with pytest.raises(ValueError):
        locs_to_vals1D(x, y, bad_q, [(0.0, 0.0)])


def test_point_nearest_returns_no_partial_result_on_rejection():
    """partial_results channel: nothing is returned for a rejected batch."""
    x = np.array([0.0, 1.0])
    y = np.array([0.0, 1.0])
    q = np.array([1.0, 2.0])
    result = None
    with pytest.raises(ValueError):
        result = locs_to_vals1D(x, y, q, [(0.0, 0.0), (np.nan, 1.0)])
    assert result is None


def test_point_nearest_is_reproducible_and_order_preserving():
    """Two identical calls agree, and a permuted query list permutes the answers."""
    queries = [(0.1, 0.1), (2.4, 0.4), (-0.9, 1.9)]
    first = locs_to_vals1D(CLOUD_X, CLOUD_Y, CLOUD_Q, queries)
    second = locs_to_vals1D(CLOUD_X, CLOUD_Y, CLOUD_Q, queries)
    assert first == second
    permuted = [queries[index] for index in (2, 0, 1)]
    assert locs_to_vals1D(CLOUD_X, CLOUD_Y, CLOUD_Q, permuted) == [first[2], first[0], first[1]]
