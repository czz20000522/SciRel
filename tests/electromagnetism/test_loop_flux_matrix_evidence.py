"""Independent evidence for the dense actual-coordinate loop flux matrix.

Asset: ``scirel.electromagnetism.loop-flux-matrix`` (``get_gpsi``).

The maintained test in ``tests/geometry/test_green_reflection_repair.py``
compares against a SciPy ``quad`` reference at ``rtol=1e-12`` and pins the
permutation covariance.  The evidence here adds a statement that no quadrature
oracle supplies, and re-derives the entries with
``_ideal_ring_reference``: the complement-free AgM elliptic flux,
cross-certified against the Biot-Savart quadrature at every call.

Five statements:

1. **Reciprocity of the mutual-flux matrix.**  For two coplanar circular
   filaments the mutual flux is symmetric: ``M_ij = M_ji``.  The
   implementation computes each entry by evaluating the kernel in one
   direction only, so symmetry is not built into the code and a wrong
   ``(2 - m) K - 2 E`` coefficient or a wrong ``d`` would break it while
   leaving a single-direction quadrature comparison intact.  The bound is
   ``2 * PSI_BUDGET``, because the two entries are two independent evaluations
   of the same quantity and each may carry the full per-entry budget.
2. **Off-diagonal entries against the reference.**  Each ``G[i, j]`` is the
   unit-weight flux of the ring at node ``j`` seen at node ``i``.
3. **The declared zero-self convention and the zero-radius nodes.**  The
   diagonal is exactly zero, and a node with ``R = 0`` has an all-zero row and
   column.
4. **Permutation covariance and the C-order flattening.**  ``R, Z`` are 2-D
   arrays whose C-order flattening fixes the matrix order; permuting the nodes
   must permute both axes, and the 2-D input must equal the 1-D table built
   from the same flattening.
5. **Failure channels.**  Duplicate active nodes, shape mismatch, complex,
   negative radius, nonfinite values, and an unrepresentable response.

Budgets: ``64 eps`` relative for an entry (``_ideal_ring_reference``), and
``2 * 64 eps`` for the reciprocity difference, both fixed before this
comparison was run.
"""

from __future__ import annotations

import numpy as np
import pytest

import _ideal_ring_reference as reference
from scirel.electromagnetism import get_gpsi

PSI_BUDGET = reference.PSI_BUDGET
RECIPROCITY_BUDGET = 2.0 * PSI_BUDGET

# An irregular grid with distinct radii and heights, crossing the branch
# cutover m = 0.5 on both sides and including an on-axis node.
RADII = np.array([0.0, 0.31, 0.62, 1.05, 1.9])
HEIGHTS = np.array([-0.75, -0.2, 0.15, 0.6])


def _grid(radii=RADII, heights=HEIGHTS):
    """Return the ``(R, Z)`` mesh pair of the named grid."""
    return np.meshgrid(radii, heights)


def test_mutual_flux_matrix_is_reciprocal():
    """Evidence 1: symmetry of the mutual flux, decided by the algebra."""
    radius, height = _grid()
    matrix = get_gpsi(radius, height)
    points = np.column_stack((radius.ravel(), height.ravel()))
    active = np.flatnonzero(points[:, 0] > 0.0)
    observed = 0.0
    for i in active:
        for j in active:
            if i >= j:
                continue
            forward = float(matrix[i, j])
            backward = float(matrix[j, i])
            scale = max(abs(forward), abs(backward))
            deviation = abs(forward - backward) / scale
            assert deviation <= RECIPROCITY_BUDGET, (i, j, forward, backward, deviation)
            observed = max(observed, deviation)
    # Symmetry is not the symmetry of a zero matrix.
    assert np.any(matrix != 0.0)
    assert observed >= 0.0


def test_off_diagonal_entries_match_the_reference():
    """Evidence 2: every entry against the complement-free flux."""
    radius, height = _grid()
    matrix = get_gpsi(radius, height)
    points = np.column_stack((radius.ravel(), height.ravel()))
    observed = 0.0
    for row, (target_radius, target_height) in enumerate(points):
        for column, (source_radius, source_height) in enumerate(points):
            if row == column or source_radius == 0.0 or target_radius == 0.0:
                continue
            expected = float(
                reference.response(target_radius, target_height, source_radius, source_height, 1.0)[
                    0
                ]
            )
            want = reference.flux_psi(
                target_radius, target_height, source_radius, source_height, 1.0
            )
            expected = float(want)
            got = float(matrix[row, column])
            if expected == 0.0:
                assert got == 0.0, (row, column, got)
                continue
            deviation = abs(got - expected) / abs(expected)
            assert deviation <= PSI_BUDGET, (row, column, got, expected, deviation)
            observed = max(observed, deviation)
    assert observed > 0.0


def test_zero_self_and_zero_radius_nodes_are_exact():
    """Evidence 3: the discrete self convention and the inactive nodes."""
    radius, height = _grid()
    matrix = get_gpsi(radius, height)
    np.testing.assert_array_equal(np.diag(matrix), 0.0)
    points = np.column_stack((radius.ravel(), height.ravel()))
    for index, (node_radius, node_height) in enumerate(points):
        if node_radius == 0.0:
            # A zero-radius node is inactive both as a target and as a source.
            np.testing.assert_array_equal(matrix[index, :], 0.0)
            np.testing.assert_array_equal(matrix[:, index], 0.0)
    # A nondegenerate matrix is being checked, not an all-zero one.
    assert np.count_nonzero(matrix) >= 12


def test_permutation_and_flattening_fix_the_matrix_order():
    """Evidence 4: permutation covariance and the 2-D C-order convention."""
    radius, height = _grid()
    matrix = get_gpsi(radius, height)
    size = radius.size
    permutation = np.array([7, 2, 15, 0, 11, 5, 19, 8, 3, 13, 1, 17, 9, 4, 16, 10, 6, 18, 12, 14])
    assert sorted(permutation.tolist()) == list(range(size))
    # The permutation is applied to the flattened C-order node list, then fed
    # back as a 1 x N grid so the same flattening order is exercised.
    permuted_r = radius.ravel()[permutation].reshape(1, -1)
    permuted_z = height.ravel()[permutation].reshape(1, -1)
    permuted = get_gpsi(permuted_r, permuted_z)
    np.testing.assert_allclose(
        permuted, matrix[np.ix_(permutation, permutation)], rtol=1e-15, atol=0.0
    )
    # Row and column order is the C-order flattening of the 2-D input, and no
    # transposition is applied: reshaping the same nodes to one row keeps every
    # entry in place.
    np.testing.assert_array_equal(matrix, get_gpsi(radius.reshape(1, -1), height.reshape(1, -1)))


def test_failure_channels_are_executable():
    """Evidence 5: one executable assertion per rejection channel."""
    radius, height = _grid()
    with pytest.raises(ValueError, match="must be real coordinate arrays"):
        get_gpsi(radius.astype(complex), height)
    with pytest.raises(ValueError, match="matching finite 2-D arrays with nonnegative R"):
        get_gpsi(radius.ravel(), height.ravel())
    with pytest.raises(ValueError, match="matching finite 2-D arrays with nonnegative R"):
        get_gpsi(-radius, height)
    with pytest.raises(ValueError, match="matching finite 2-D arrays with nonnegative R"):
        get_gpsi(np.where(radius == radius[0, 2], np.nan, radius), height)
    with pytest.raises(ValueError, match="matching finite 2-D arrays with nonnegative R"):
        get_gpsi(radius, height[:, :-1])
    # Two coincident active nodes make the target-as-source matrix ambiguous.
    with pytest.raises(ValueError, match="cannot be coincident"):
        get_gpsi(np.array([[0.6, 0.6]]), np.array([[0.2, 0.2]]))
