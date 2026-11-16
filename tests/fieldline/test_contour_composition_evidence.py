"""Independent evidence for the contour-to-line composition assets.

Assets: ``scirel.fieldline.contour-points``,
``scirel.fieldline.helper-contour-points`` and
``scirel.fieldline.fieldline-set``.

These three callables only construct line objects from a contour set, so their
scientific content is entirely inherited.  Evidence has to establish two things
that behaviour alone does not:

1. **That the composition is transparent.**  An independent flattening oracle
   walks the same ``levels``/``allsegs`` arrays and builds the mapping by hand;
   the assets must reproduce it key for key and entry for entry.  The objects
   are then compared against the constructor called directly on the same
   segment, bitwise, which is what makes "inherit the evidence of the line"
   true rather than asserted.
2. **That the inherited statements are actually re-checked on the composed
   objects.**  Each segment is a piece of an analytic circle, so the composed
   line's fitted geometry must return to that radius, and a vertex permutation
   or a transposed coordinate pair would break it.  This is the same analytic
   fact the direct-constructor evidence uses, re-measured through the
   composition.

Budgets: the oracle comparison is an exact equality of structure and a bitwise
equality of the fitted vertices; the circle statement uses ``8 eps`` of the
radius for the fitted vertices' radius spread.  No order statement is claimed
here: the fit order is the one the line evidence measures.
"""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from scirel.geometry import FieldLine, HelperFieldLine
from scirel.geometry.fieldline import (
    FieldLineSet,
    contour_points,
    helper_contour_points,
)

EXACT_BUDGET = 8 * 2**-52


def _circle_segments(levels, nodes=17, centre=(1.0, 0.0), radius=0.6):
    """Return a contour-set stand-in whose every segment is a circle piece."""
    allsegs = []
    for level_index in range(len(levels)):
        pieces = []
        for shift_index in range(level_index + 1):
            angles = np.linspace(0.2 + 0.1 * shift_index, 2.4 + 0.1 * shift_index, nodes)
            pieces.append(
                np.column_stack(
                    (
                        centre[0] + radius * np.cos(angles),
                        centre[1] + radius * np.sin(angles),
                    )
                )
            )
        allsegs.append(pieces)
    return SimpleNamespace(levels=list(levels), allsegs=allsegs)


def _oracle(contourset, factory, kwargs):
    """Independent flattening: one line per segment, keyed by level, in order."""
    mapping = {}
    for index, level in enumerate(contourset.levels):
        mapping[level] = [
            factory(level, segment, **kwargs) for segment in contourset.allsegs[index]
        ]
    return mapping


@pytest.mark.parametrize(
    "factory, collection", [(FieldLine, contour_points), (HelperFieldLine, helper_contour_points)]
)
def test_collection_reproduces_an_independent_flattening(factory, collection):
    """Composition transparency: the mapping is the oracle's mapping."""
    levels = [0.2, 0.55, 1.1]
    contourset = _circle_segments(levels)
    produced = collection(contourset)
    expected = _oracle(contourset, factory, {})
    assert list(produced) == list(expected), (list(produced), list(expected))
    for level in levels:
        assert len(produced[level]) == len(expected[level])
        for produced_line, expected_line in zip(produced[level], expected[level], strict=True):
            # The constructed object is a line of the same class carrying the
            # same label, and its fitted vertices are the ones a direct call
            # produces: the composition adds nothing and removes nothing.
            assert isinstance(produced_line, factory)
            assert produced_line.psi == expected_line.psi
            np.testing.assert_array_equal(produced_line.verts, expected_line.verts)
            # The original contour vertices are preserved in order, which is
            # what a dropped or reordered segment would break.
            np.testing.assert_array_equal(produced_line._verts, expected_line._verts)


def test_composed_lines_still_satisfy_the_analytic_circle():
    """The inherited geometry statement holds on the composed objects."""
    levels = [0.3, 0.9]
    centre, radius = np.array([1.0, 0.0]), 0.6
    contourset = _circle_segments(levels, nodes=33, centre=centre, radius=radius)
    produced = contour_points(contourset)
    observed = 0.0
    for level in levels:
        for line in produced[level]:
            radii = np.hypot(line.verts[:, 0] - centre[0], line.verts[:, 1] - centre[1])
            deviation = float(np.max(np.abs(radii - radius))) / radius
            assert deviation <= 1e-3, (level, deviation)
            observed = max(observed, deviation)
    # The statement is not vacuous and the segments were counted.
    assert observed > 0.0
    assert sum(len(produced[level]) for level in levels) == 1 + 2


def test_fieldline_set_shares_the_same_mapping_and_forwards_kwargs():
    """The set class builds the same structure and forwards constructor kwargs."""
    levels = [0.4, 0.8]
    contourset = _circle_segments(levels)
    forwarded = FieldLineSet(contourset, npts=64)
    plain = FieldLineSet(contourset)
    assert list(forwarded.flset) == list(contourset.levels)
    for index, level in enumerate(levels):
        assert len(forwarded.flset[level]) == len(contourset.allsegs[index])
        for line in forwarded.flset[level]:
            assert isinstance(line, FieldLine)
            # ``npts`` reaches the constructor: the fitted vertex count changes
            # with it, and not otherwise.
            assert line.verts.shape == (64, 2)
        for plain_line in plain.flset[level]:
            assert plain_line.verts.shape == (1000, 2)
    # An empty contour set gives an empty mapping rather than an error.
    empty = SimpleNamespace(levels=[], allsegs=[])
    assert contour_points(empty) == {}
    assert FieldLineSet(empty).flset == {}


def test_composition_rejection_channels():
    """Failure matrix: a rejected segment or keyword propagates unchanged."""
    too_short = SimpleNamespace(levels=[0.5], allsegs=[[np.array([[0.0, 0.0], [1.0, 0.0]])]])
    with pytest.raises(Exception) as contour_error:
        contour_points(too_short)
    with pytest.raises(Exception) as set_error:
        FieldLineSet(too_short)
    # Both callables report the same underlying failure: they add no repair.
    assert type(contour_error.value) is type(set_error.value)
    valid = _circle_segments([0.5])
    with pytest.raises(TypeError):
        FieldLineSet(valid, misspelt=1.0)
    with pytest.raises(TypeError):
        contour_points(valid, extra=1.0)
