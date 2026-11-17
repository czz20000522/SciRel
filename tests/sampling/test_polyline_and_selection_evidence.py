"""Independent evidence for the polyline, orientation and reflection relations.

Assets:

* ``scirel.geometry.path-distance`` (``get_fieldline_distance``)
* ``scirel.geometry.parse-segment`` (``parse_segment``)
* ``scirel.geometry.select-fieldline`` (``get_fieldlines``)
* ``scirel.geometry.scalar-reflection`` (``reflect_and_hstack``)

These four relations are combinatorial: they choose, roll, reverse or mirror an
already-given sequence of vertices, and nothing in them is an approximation.
The evidence therefore uses **exact arithmetic only** — rational chord lengths
on Pythagorean legs, the shoelace double area recomputed with
:class:`fractions.Fraction`, exact nearest-vertex selection, and bitwise array
equality for mirrors.  No assertion below carries a tolerance, so a wrong
index convention, an off-by-one roll, a dropped closure marker or a mirror that
keeps the zero column twice cannot hide behind rounding.

Independent oracles, none of which is produced by the code under test:

1. **Chord lengths.**  ``get_fieldline_distance`` is the cumulative Euclidean
   chord length of the supplied vertex order.  For the legs ``(3,0)``, ``(0,4)``
   and ``(3,4)`` the length is exact in binary64 (``3``, ``4``, ``5``), so the
   expected cumulative vector is a closed-form constant, and refinement at a
   representable midpoint must leave the total unchanged.
2. **Double area.**  The orientation flag is the sign of the polygon double
   area.  The truth value is recomputed with exact rationals as
   ``D = sum(x_i y_{i+1} - x_{i+1} y_i)`` over the closed vertex cycle; a
   standard counter-clockwise polygon has ``D > 0``, so ``clockwise=True`` must
   return ``D < 0``.  This catches an inverted comparison in the operator.
3. **Cyclic rotation.**  Selecting a start vertex and orienting a contour may
   only rotate or reverse the given cycle.  The test asserts the output is a
   cyclic rotation of the input (or of its reverse), which is an exact set-level
   statement that forbids inventing, duplicating or dropping vertices.
4. **Brute-force nearest vertex.**  Every "nearest vertex" choice is compared
   with an exhaustive rational minimisation over the same vertices, with the
   documented first-vertex tie rule derived from that enumeration alone.
5. **Level membership.**  A contour level is selected by exact equality.  A
   level one representable step away from a stored level must be rejected,
   which distinguishes exact membership from a tolerant lookup.

Defect probes (would this assertion go red?):

* return ``0``/zeros instead of the relation -> cumulative-distance and mirror
  shape/parity assertions fail;
* return the input unchanged -> orientation and closure-marker assertions fail;
* return a wrong-magnitude constant -> the exact Pythagorean constants fail;
* use the wrong contour index or the wrong roll direction -> the disjoint-range
  level fixture and the rotation-invariance assertions fail.

Degenerate cases asserted here: a two-vertex path, a repeated vertex, a
zero-area (collinear) contour whose orientation is undefined, a single radial
column for the mirror, and a mirror input that is not centred on the axis.
"""

from __future__ import annotations

from fractions import Fraction
from types import SimpleNamespace

import numpy as np
import pytest

from scirel.geometry.sampling import (
    get_fieldline_distance,
    get_fieldlines,
    parse_segment,
    reflect_and_hstack,
)

# ---------------------------------------------------------------------------
# exact helpers
# ---------------------------------------------------------------------------


def _exact(value) -> Fraction:
    """Exact rational value of a binary64 number (no decimal detour)."""
    return Fraction(*float(value).as_integer_ratio())


def _doubled_area(points) -> Fraction:
    """Exact signed double area ``sum(x_i y_{i+1} - x_{i+1} y_i)`` of a cycle."""
    values = [(_exact(x), _exact(y)) for x, y in points]
    total = Fraction(0)
    for index, (x, y) in enumerate(values):
        next_x, next_y = values[(index + 1) % len(values)]
        total += x * next_y - next_x * y
    return total


def _rows(points) -> list[tuple[Fraction, Fraction]]:
    return [(_exact(x), _exact(y)) for x, y in np.asarray(points).reshape(-1, 2)]


def _is_cyclic_rotation(candidate, reference) -> bool:
    """True when ``candidate`` is an exact cyclic rotation of ``reference``."""
    left, right = _rows(candidate), _rows(reference)
    if len(left) != len(right):
        return False
    if not left:
        return True
    doubled = right + right
    start = left[0]
    return any(
        doubled[offset : offset + len(left)] == left
        for offset, row in enumerate(doubled)
        if row == start
    )


def _exact_nearest(vertices, target):
    """Exhaustive rational nearest vertex; ties keep the first listed vertex."""
    tx, ty = _exact(target[0]), _exact(target[1])
    best_index, best = None, None
    for index, (x, y) in enumerate(_rows(vertices)):
        distance = (x - tx) ** 2 + (y - ty) ** 2
        if best is None or distance < best:
            best_index, best = index, distance
    return best_index


SQUARE = np.array([[0.0, 0.0], [0.0, 1.0], [1.0, 1.0], [1.0, 0.0]])


# ---------------------------------------------------------------------------
# path-distance
# ---------------------------------------------------------------------------


def test_path_distance_equals_exact_pythagorean_chord_lengths():
    """Exact leg lengths 3, 4 and 5 accumulate to closed-form constants."""
    points = np.array([[0.0, 0.0], [3.0, 0.0], [3.0, 4.0], [6.0, 8.0]])
    assert np.array_equal(get_fieldline_distance(points), [0.0, 3.0, 7.0, 12.0])


def test_path_distance_is_additive_under_representable_refinement():
    """Splitting a leg at a representable midpoint leaves the total unchanged."""
    coarse = np.array([[0.0, 0.0], [3.0, 4.0]])
    refined = np.array([[0.0, 0.0], [1.5, 2.0], [3.0, 4.0]])
    assert get_fieldline_distance(coarse)[-1] == 5.0
    # 2.5 is exact, so the refinement is an identity, not an approximation.
    assert get_fieldline_distance(refined)[-1] == 5.0
    assert np.array_equal(get_fieldline_distance(refined), [0.0, 2.5, 5.0])


def test_path_distance_prefix_and_duplicate_vertex_are_exact():
    """A longer path keeps its prefix, and a repeated vertex adds exactly zero."""
    short = np.array([[0.0, 0.0], [0.0, 2.0], [0.0, 2.0]])
    long = np.array([[0.0, 0.0], [0.0, 2.0], [0.0, 2.0], [0.0, 5.0]])
    short_distance = get_fieldline_distance(short)
    long_distance = get_fieldline_distance(long)
    assert np.array_equal(short_distance, [0.0, 2.0, 2.0])
    assert np.array_equal(long_distance[: len(short)], short_distance)
    assert long_distance[-1] == 5.0
    # No implicit closing segment: the first-to-last gap is not accumulated.
    assert long_distance[-1] != np.hypot(0.0, 5.0) + 5.0


def test_path_distance_is_invariant_under_exact_quarter_turns():
    """A 90-degree rotation is exact, so every cumulative value is preserved."""
    points = np.array([[0.0, 0.0], [3.0, 0.0], [3.0, 4.0]])
    rotated = np.column_stack((-points[:, 1], points[:, 0]))
    assert np.array_equal(get_fieldline_distance(rotated), get_fieldline_distance(points))


def test_path_distance_single_vertex_returns_exact_zero():
    """n=1 is the documented boundary: zero distance at the only vertex."""
    register = get_fieldline_distance(np.array([[2.5, -1.5]]))
    assert register.shape == (1,)
    assert register[0] == 0.0


# ---------------------------------------------------------------------------
# parse-segment
# ---------------------------------------------------------------------------


def test_parse_segment_orientation_follows_the_exact_double_area_sign():
    """`clockwise=True` must return a cycle whose exact double area is negative."""
    # SQUARE is listed clockwise, so its exact double area is -2 (twice the area).
    assert _doubled_area(SQUARE) == -2
    assert _doubled_area(SQUARE[::-1]) == 2
    assert _doubled_area(parse_segment(SQUARE, clockwise=True)) < 0
    assert _doubled_area(parse_segment(SQUARE, clockwise=False)) > 0
    # The flag drives the sign, not the input order: the reversed cycle flips both.
    assert _doubled_area(parse_segment(SQUARE[::-1], clockwise=True)) < 0
    assert _doubled_area(parse_segment(SQUARE[::-1], clockwise=False)) > 0


def test_parse_segment_only_rotates_or_reverses_the_supplied_cycle():
    """No vertex is invented, duplicated or dropped by roll and orientation."""
    for clockwise in (True, False):
        oriented = parse_segment(SQUARE, clockwise=clockwise)
        assert len(oriented) == len(SQUARE)
        assert _is_cyclic_rotation(oriented, SQUARE) or _is_cyclic_rotation(oriented, SQUARE[::-1])


def test_parse_segment_rolls_to_the_exact_nearest_start_vertex():
    """The first vertex is the exhaustive rational nearest to `start_coord`."""
    target = np.array([0.9, 0.9])
    oriented = parse_segment(SQUARE, start_coord=target, clockwise=True)
    expected = _rows(SQUARE)[_exact_nearest(SQUARE, target)]
    assert _rows(oriented)[0] == expected == (Fraction(1), Fraction(1))


def test_parse_segment_start_is_stable_under_every_input_rotation():
    """Permutation scan: rolling the input cannot change a pinned output."""
    target = np.array([0.9, 0.9])
    reference = parse_segment(SQUARE, start_coord=target, clockwise=True)
    for shift in range(len(SQUARE)):
        rolled = np.roll(SQUARE, shift, axis=0)
        assert np.array_equal(parse_segment(rolled, start_coord=target, clockwise=True), reference)


def test_parse_segment_explicit_end_keeps_the_terminal_vertex_once():
    """`end_coord` truncates inclusively and suppresses automatic re-closing."""
    oriented = parse_segment(SQUARE, start_coord=[0.0, 0.0], end_coord=[1.0, 1.0], clockwise=True)
    assert np.array_equal(oriented, [[0.0, 0.0], [0.0, 1.0], [1.0, 1.0]])
    # An explicit end alone also suppresses the closure marker on a marked input.
    marked = np.vstack((SQUARE, SQUARE[:1]))
    truncated = parse_segment(marked, end_coord=[1.0, 1.0], clockwise=True)
    assert np.array_equal(truncated, [[0.0, 0.0], [0.0, 1.0], [1.0, 1.0]])


@pytest.mark.parametrize("clockwise", [True, False])
def test_parse_segment_closes_a_marked_polygon_exactly_once(clockwise):
    """An exact closure marker survives as exactly one terminal duplicate."""
    marked = np.vstack((SQUARE, SQUARE[:1]))
    oriented = parse_segment(marked, clockwise=clockwise)
    assert oriented.shape == (len(SQUARE) + 1, 2)
    assert np.array_equal(oriented[0], oriented[-1])
    first = _rows(oriented)[0]
    assert _rows(oriented).count(first) == 2


def test_parse_segment_zero_area_orientation_is_not_establishable():
    """Collinear vertices have zero double area; the flag then cannot discriminate.

    The contract's precondition is a *meaningful* polygon orientation, so this is
    documented behaviour rather than evidence of a correct orientation choice:
    the implementation's strict `> 0` test reports not-clockwise and returns the
    cycle reversed for ``clockwise=True``.
    """
    collinear = np.array([[0.0, 0.0], [1.0, 0.0], [2.0, 0.0]])
    assert _doubled_area(collinear) == 0
    assert np.array_equal(parse_segment(collinear, clockwise=False), collinear)
    reversed_cycle = parse_segment(collinear, clockwise=True)
    assert _is_cyclic_rotation(reversed_cycle, collinear[::-1])


def test_parse_segment_rejects_nonfinite_vertices_and_coordinates():
    """invalid_input channel: both vertex and endpoint non-finiteness raise."""
    bad = SQUARE.copy()
    bad[2, 1] = np.inf
    with pytest.raises(ValueError):
        parse_segment(bad)
    with pytest.raises(ValueError):
        parse_segment(SQUARE, start_coord=[np.nan, 0.0])
    with pytest.raises(ValueError):
        parse_segment(SQUARE, end_coord=[0.0, np.inf])


def test_parse_segment_returns_no_partial_result_on_rejection():
    """partial_results channel: a rejected request yields no array at all."""
    bad = SQUARE.copy()
    bad[0, 0] = np.nan
    result = None
    with pytest.raises(ValueError):
        result = parse_segment(bad)
    assert result is None


# ---------------------------------------------------------------------------
# select-fieldline
# ---------------------------------------------------------------------------

# Disjoint coordinate ranges identify which level group each segment belongs to.
LEVEL_PAYLOAD = {
    0.25: [
        np.array([[10.0, 10.0], [10.0, 11.0], [11.0, 11.0]]),
    ],
    0.5: [
        np.array([[20.0, 20.0], [20.0, 21.0]]),
        np.array([[30.0, 30.0], [30.0, 31.0], [31.0, 31.0], [31.0, 30.0]]),
    ],
}


def _contours(levels=None, payload=None):
    levels = list(LEVEL_PAYLOAD) if levels is None else levels
    payload = LEVEL_PAYLOAD if payload is None else payload
    return SimpleNamespace(
        levels=levels,
        allsegs=[
            [np.asarray(segment, dtype=float) for segment in payload[level]] for level in levels
        ],
    )


def test_select_fieldline_uses_the_level_index_not_the_first_group():
    """A wrong level index would return the level-0.25 range instead of 0.5."""
    selected = get_fieldlines(_contours(), 0.5, clockwise=True)
    assert np.all(selected >= 20.0), selected
    assert selected.shape == (4, 2)  # longest segment of the 0.5 group
    # And the other level still resolves to its own disjoint range.
    other = get_fieldlines(_contours(), 0.25, clockwise=True)
    assert np.all(other <= 11.0), other
    assert other.shape == (3, 2)


def test_select_fieldline_takes_the_largest_segment_by_vertex_count():
    """Delegation check against an independently chosen longest segment."""
    contours = _contours()
    level = 0.5
    segments = contours.allsegs[contours.levels.index(level)]
    longest = max(segments, key=lambda segment: np.shape(segment)[0])
    assert longest.shape[0] == 4
    expected = parse_segment(longest, clockwise=True)
    assert np.array_equal(get_fieldlines(contours, level, clockwise=True), expected)


def test_select_fieldline_requires_exact_level_membership():
    """A representable neighbour of a stored level is rejected, not tolerated."""
    contours = _contours()
    stored = contours.levels[1]
    neighbour = np.nextafter(stored, 2.0)
    assert neighbour != stored
    with pytest.raises(ValueError):
        get_fieldlines(contours, neighbour)
    assert get_fieldlines(contours, stored).shape[0] == 4


def test_select_fieldline_equal_length_segments_keep_the_first_listed():
    """Tie rule: `max` keeps the first listed segment of equal vertex count.

    This is an implementation convention recorded by the contract, not a
    physical claim; it is asserted so a silent change of the tie rule is visible.
    """
    first = np.array([[0.0, 0.0], [0.0, 1.0]])
    second = np.array([[9.0, 9.0], [9.0, 8.0]])
    contours = SimpleNamespace(levels=[0.5], allsegs=[[first, second]])
    assert np.array_equal(get_fieldlines(contours, 0.5, clockwise=True), first)


def test_select_fieldline_missing_level_raises_and_returns_nothing():
    """invalid_input channel (unknown level) — one assertion, no partial result."""
    result = None
    with pytest.raises(ValueError):
        result = get_fieldlines(_contours(), 0.75)
    assert result is None


# ---------------------------------------------------------------------------
# scalar-reflection
# ---------------------------------------------------------------------------


def _mirror_input():
    rho, z = np.meshgrid([0.0, 0.5, 1.0, 2.0], [-0.2, 0.0, 0.4])
    return rho, z


def test_scalar_reflection_keeps_the_symmetry_plane_once():
    """Radial columns become [-2, -1, -0.5, 0, 0.5, 1, 2]: the zero column once."""
    rho, z = _mirror_input()
    reflected_rho, reflected_z = reflect_and_hstack(rho, z)
    assert reflected_rho.shape == (3, 7) == reflected_z.shape
    assert np.array_equal(reflected_rho[0], [-2.0, -1.0, -0.5, 0.0, 0.5, 1.0, 2.0])
    assert int(np.count_nonzero(reflected_rho == 0.0)) == 3
    assert np.array_equal(reflected_z, np.hstack((z[:, -1:0:-1], z)))


def test_scalar_reflection_is_exactly_even_for_an_even_field():
    """An even field satisfies F(-rho) = F(rho) bitwise, not approximately."""
    rho, z = _mirror_input()
    _, _, reflected = reflect_and_hstack(rho, z, quantities=[rho * rho])
    mirror = reflected[:, ::-1]
    assert np.array_equal(reflected, mirror)


def test_scalar_reflection_matches_a_hand_built_exact_array():
    """Bitwise equality against an array assembled without the operator."""
    rho, z = _mirror_input()
    field = rho + 2.0 * z
    _, _, reflected = reflect_and_hstack(rho, z, quantities=[field])
    expected = np.hstack((field[:, -1:0:-1], field))
    assert np.array_equal(reflected, expected)
    assert reflected.dtype == np.float64


def test_scalar_reflection_is_not_idempotent():
    """Re-applying cannot work: the reflected grid is no longer centred."""
    rho, z = _mirror_input()
    reflected_rho, reflected_z, _ = reflect_and_hstack(rho, z, quantities=[rho])
    assert reflected_rho[0, 0] == -2.0
    with pytest.raises(ValueError):
        reflect_and_hstack(reflected_rho, reflected_z)


@pytest.mark.parametrize(
    "mutate, reason",
    [
        (lambda rho, z: (rho[:, :1], z[:, :1]), "one radial column"),
        (lambda rho, z: (rho + 0.25, z), "nonzero first radial column"),
        (lambda rho, z: (rho, z[:-1]), "mismatched shapes"),
        (lambda rho, z: (rho[0], z[0]), "one-dimensional arrays"),
    ],
)
def test_scalar_reflection_rejects_out_of_contract_grids(mutate, reason):
    """invalid_input channel, one executable assertion per rejection reason."""
    rho, z = _mirror_input()
    bad_rho, bad_z = mutate(rho, z)
    with pytest.raises(ValueError) as error:
        reflect_and_hstack(bad_rho, bad_z)
    assert str(error.value)


def test_scalar_reflection_rejects_nonfinite_fields_and_dual_input_paths():
    """Two more invalid_input reasons: non-finite field, both field channels."""
    rho, z = _mirror_input()
    bad_field = rho * rho
    bad_field[1, 1] = np.nan
    with pytest.raises(ValueError):
        reflect_and_hstack(rho, z, quantities=[bad_field])
    with pytest.raises(ValueError):
        reflect_and_hstack(rho, z, rho * rho, quantities=[rho * rho])


def test_scalar_reflection_is_bitwise_reproducible():
    """No randomness, no accumulation order: two identical calls agree bitwise."""
    rho, z = _mirror_input()
    first = reflect_and_hstack(rho, z, quantities=[rho * rho, rho + z])
    second = reflect_and_hstack(rho, z, quantities=[rho * rho, rho + z])
    assert all(np.array_equal(left, right) for left, right in zip(first, second, strict=True))
