"""Independent evidence for the dense axisymmetric Green response matrices.

Asset: ``scirel.field.dense-axisymmetric-green``.

The maintained file ``test_dense_axisymmetric_green.py`` pins shapes, the
weight-scaling column rule, agreement between a column and the aggregate
response of the same filament, and the axis ``B_Z`` limit.  The second of those
compares one SciRel entry point against another SciRel entry point, so it cannot
detect a kernel that is wrong in both.  The evidence here compares every matrix
entry against ``_biot_savart_reference``, which integrates the Biot-Savart law
directly and never touches an elliptic integral or the hypergeometric branch the
implementation switches on at ``m = 0.5``.

What the tests establish
------------------------

1. Every ``[target, source]`` entry of all three matrices equals the quadrature
   field of that single filament at that target, to ``_RELATIVE_BUDGET``.
2. The exact coincidence entries are zero, and a zero-radius source column is
   zero while the neighbouring column of a positive-radius source is not.
3. Weight scaling is exact for a power of two: column ``j`` of the doubled-weight
   call is exactly twice column ``j`` of the base call, for every target row.
4. An empty source table keeps the two-dimensional ``(N_target, 0)`` shape the
   contract promises, so a caller can still align it with its source records.

Budget: ``_RELATIVE_BUDGET = 64 eps`` from ``_biot_savart_reference``, derived
there from the operation count of the closed form.  The observed maximum over
the grid used here is ``7.81e-15`` (``0.55`` of the budget); it is an observed
maximum on a sampled grid, not a proven bound between grid points.  The
power-of-two and coincidence assertions are exact equalities and carry no
budget.

Evidence ceiling: finite grids only; the near-wire regime is bounded by
``_MIN_SEPARATION_RATIO`` and no continuous accuracy statement is made.  The
matrix is a discrete self-response convention, so nothing here says anything
about a finite-wire self field.
"""

from __future__ import annotations

import numpy as np
import pytest

import _biot_savart_reference as reference
from scirel.field import dense_axisymmetric_green_response

RELATIVE_BUDGET = reference._RELATIVE_BUDGET
FIELDS = ("gpsi", "gBR", "gBZ")

TARGETS = [(0.2, 0.13), (0.55, -0.31), (0.9, 0.4), (1.4, 0.1), (0.32, 0.0)]
SOURCES = [(0.35, 0.0, 1.0), (0.62, 0.25, -2.0), (0.8, -0.1, 0.5)]


def _matrices(targets, sources):
    result = dense_axisymmetric_green_response(targets, sources)
    return result["gpsi"], result["gBR"], result["gBZ"]


def test_every_matrix_entry_matches_the_biot_savart_quadrature():
    """Evidence 1: the dense response against direct quadrature, entry by entry."""
    psi, br, bz = _matrices(TARGETS, SOURCES)
    observed = 0.0
    for row, (target_r, target_z) in enumerate(TARGETS):
        for column, (coil_r, coil_z, weight) in enumerate(SOURCES):
            expected = reference.ring_field(target_r, target_z, coil_r, coil_z, weight)
            for name, matrix, want in zip(FIELDS, (psi, br, bz), expected, strict=True):
                got = float(matrix[row, column])
                if float(want) == 0.0:
                    assert got == 0.0, (name, row, column, got)
                    continue
                deviation = abs(got - float(want)) / abs(float(want))
                assert deviation <= RELATIVE_BUDGET, (name, row, column, deviation)
                observed = max(observed, deviation)
    assert observed > 0.0
    # Nonzero anchors: a matrix that returned zeros would satisfy the ratio
    # test only through the exact-zero branch above, so the three entries below
    # must be nonzero and must have the expected signs.
    assert psi[0, 0] > 0.0
    assert bz[0, 0] > 0.0
    assert br[2, 1] != 0.0


def test_explicit_coincidence_is_a_zero_entry_and_zero_radius_a_zero_column():
    """Evidence 2: the discrete zero-self and zero-radius conventions."""
    target = (0.35, 0.0)
    psi, br, bz = _matrices([target, (0.2, 0.1)], [[0.35, 0.0, 1.0]])
    for name, matrix in zip(FIELDS, (psi, br, bz), strict=True):
        assert matrix[0, 0] == 0.0, name
        assert matrix[1, 0] != 0.0, name
    # A zero-radius source has a zero column; the positive-radius neighbour in
    # the same call does not, so the zero is the convention and not an empty
    # assembly.
    psi, br, bz = _matrices([(0.2, 0.1)], [[0.0, 0.0, 1.0], [0.35, 0.0, 1.0]])
    for name, matrix in zip(FIELDS, (psi, br, bz), strict=True):
        assert matrix[0, 0] == 0.0, name
        assert matrix[0, 1] != 0.0, name


def test_weight_scales_each_column_exactly():
    """Evidence 3: exact power-of-two scaling down the source axis."""
    base = _matrices(TARGETS, SOURCES)
    doubled = _matrices(TARGETS, [(r, z, 4.0 * w) for r, z, w in SOURCES])
    for name, base_matrix, doubled_matrix in zip(FIELDS, base, doubled, strict=True):
        np.testing.assert_array_equal(doubled_matrix, 4.0 * base_matrix), name
        # Nonzero anchor: exact equality with zero would be satisfied by an
        # all-zero matrix.
        assert np.any(base_matrix != 0.0), name


def test_empty_sources_keep_the_declared_two_dimensional_shape():
    """Evidence 4: the empty-source shorthand preserves the source axis."""
    targets = [[0.2, 0.1], [0.4, -0.2], [0.6, 0.3]]
    for shorthand in ([], np.empty((0, 3))):
        result = dense_axisymmetric_green_response(targets, shorthand)
        assert list(result) == list(FIELDS)
        for name in FIELDS:
            assert result[name].shape == (3, 0)
            assert result[name].dtype == np.float64


def test_each_declared_rejection_channel_is_executable():
    """Every ``failure_semantics`` channel has one assertion."""
    good_targets, good_sources = [[0.2, 0.1]], [[0.35, 0.0, 1.0]]
    for bad_targets, bad_sources, message in [
        ([[0.2, 0.1, 0.3]], good_sources, "shape"),
        (good_targets, [[0.35, 0.0]], "shape"),
        ([[0.2 + 0j, 0.1]], good_sources, "real"),
        (good_targets, [[0.35 + 0j, 0.0, 1.0]], "real"),
        ([[np.inf, 0.1]], good_sources, "finite"),
        (good_targets, [[0.35, np.nan, 1.0]], "finite"),
        ([[-0.2, 0.1]], good_sources, "nonnegative"),
        (good_targets, [[-0.35, 0.0, 1.0]], "nonnegative"),
    ]:
        with pytest.raises(ValueError, match=message):
            dense_axisymmetric_green_response(bad_targets, bad_sources)
    # runtime_failure: the kernel's FloatingPointError propagates rather than
    # being converted into a non-finite matrix entry.
    with pytest.raises(FloatingPointError, match="not representable"):
        dense_axisymmetric_green_response([[0.3, 1.0e-300]], [[0.3, 0.0, 1.0e308]])
    # The empty shorthand does not swallow a malformed shape.
    with pytest.raises(ValueError, match="shape"):
        dense_axisymmetric_green_response(good_targets, np.empty((0, 2)))
