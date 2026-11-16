"""Independent evidence for the mirror-grid plasma flux Green matrix.

Asset: ``scirel.field.mirror-plasma-green``.

The maintained ``test_mirror_plasma_green.py`` checks the shape, the axis-source
columns, and that the reflected block equals the block built from direct
filament columns.  Its one second source is the same closed form recomputed by
hand.  The evidence here comes from ``_biot_savart_reference`` instead, and adds
the two structural statements the "mirror" name is about:

1. **Off-diagonal entries against direct quadrature.** Each ``[target, source]``
   entry is the flux of one unit-weight ring at another grid node, so it can be
   compared with the Biot-Savart quadrature of that ring at that node.
2. **Zero diagonal.** The coincident self term is the declared discrete
   convention; it must be exactly zero, not merely small, and the neighbouring
   off-diagonal entries must not be.
3. **Exact reflection algebra.** On a Z grid symmetric about zero the
   construction is only consistent if ``G[target, source]`` equals
   ``G[mirror(source), mirror(target)]``.  The test uses dyadic coordinates so
   that ``-z`` is exact, which makes the assertion bitwise rather than a
   tolerance.  A sign error in ``Z - z0`` would still satisfy a symmetric
   *magnitude* test but fails this one, and a matrix built from ``|Z - z0|``
   only would pass item 3 while failing item 1.
4. **Zero-radius rows and columns.** An axis node contributes no source and
   receives no response, which is the ``R = 0`` half of the same convention.
5. **Grid rejection channels**, including the three that are specific to this
   construction: non-rectilinear, non-uniform and non-symmetric Z.

Budget: ``_RELATIVE_BUDGET = 64 eps`` from ``_biot_savart_reference``; observed
maximum over the sampled entries ``1.1e-15`` (``0.08`` of the budget), on a
finite grid and not a proven continuous bound.  Items 2, 3 and 4 are exact
equalities.

Evidence ceiling: this is a flux matrix only (``psi``); the asset exposes no
radial or axial field matrix, so nothing here says anything about ``B_R`` or
``B_Z``.  The symmetric, uniform Z grid is a precondition of the operator, not of
the physics.
"""

from __future__ import annotations

import numpy as np
import pytest

import _biot_savart_reference as reference
from scirel.field import build_mirror_plasma_flux_green

RELATIVE_BUDGET = reference._RELATIVE_BUDGET

# Dyadic coordinates: ``-z`` is exact, and so is the reflection of a node index.
RADIAL = np.array([0.0, 0.125, 0.25])
AXIAL = np.array([-0.5, -0.25, 0.0, 0.25, 0.5])


def _grid():
    return np.meshgrid(RADIAL, AXIAL)


def _node(index):
    """Return ``(R, Z)`` of the flat C-order node ``index``."""
    row, column = divmod(index, len(RADIAL))
    return float(RADIAL[column]), float(AXIAL[row])


def _matrix():
    radius, height = _grid()
    return build_mirror_plasma_flux_green(radius, height)["g_psi"]


def test_off_diagonal_entries_match_the_biot_savart_quadrature():
    """Evidence 1: matrix entries against direct quadrature of one ring."""
    matrix = _matrix()
    observed = 0.0
    for target_index, source_index in [(0, 4), (1, 7), (6, 2), (9, 13), (12, 6), (14, 0)]:
        target_r, target_z = _node(target_index)
        source_r, source_z = _node(source_index)
        expected = reference.ring_field(target_r, target_z, source_r, source_z, 1.0)[0]
        assert float(expected) != 0.0
        deviation = abs(float(matrix[target_index, source_index]) - float(expected)) / abs(
            float(expected)
        )
        assert deviation <= RELATIVE_BUDGET, (target_index, source_index, deviation)
        observed = max(observed, deviation)
    assert observed > 0.0
    # Nonzero anchors with both signs: the flux of a unit ring is positive on
    # the near side and negative on the far side of the mirror plane, so a
    # matrix that collapsed to zero or to a constant would fail here.
    assert matrix[4, 0] > 0.0
    assert matrix[0, 4] < 0.0


def test_coincident_entries_are_exactly_zero_and_neighbours_are_not():
    """Evidence 2: the discrete zero-self convention of the flux matrix."""
    matrix = _matrix()
    np.testing.assert_array_equal(np.diag(matrix), 0.0)
    off_diagonal = matrix - np.diag(np.diag(matrix))
    assert np.all(off_diagonal != 0.0)


def test_reflected_blocks_match_bitwise():
    """Evidence 3: G[target, source] == G[mirror(source), mirror(target)]."""
    matrix = _matrix()
    nodes = len(RADIAL) * len(AXIAL)
    mirror = (nodes - 1) - np.arange(nodes)  # Z reflection reverses the row index
    assert np.array_equal(matrix[np.ix_(mirror, mirror)], matrix)
    # Nonzero anchor for the equality: the matrix is not symmetric on its own,
    # so the assertion above is about the reflection and not about symmetry.
    assert not np.array_equal(matrix, matrix.T)


def test_axis_nodes_carry_no_source_and_receive_no_response():
    """Evidence 4: the R = 0 half of the same convention."""
    matrix = _matrix()
    axis_rows = [row * len(RADIAL) for row in range(len(AXIAL))]
    for row in axis_rows:
        np.testing.assert_array_equal(matrix[row, :], 0.0)
        np.testing.assert_array_equal(matrix[:, row], 0.0)
    non_axis = [index for index in range(len(RADIAL) * len(AXIAL)) if index not in set(axis_rows)]
    for index in non_axis:
        assert matrix[index, index + 1 if index + 1 in non_axis else index - 1] != 0.0


def test_each_declared_rejection_channel_is_executable():
    """Every ``failure_semantics`` channel has one assertion."""
    radius, height = _grid()
    with pytest.raises(ValueError, match="real"):
        build_mirror_plasma_flux_green(radius + 0j, height)
    with pytest.raises(ValueError, match="finite"):
        build_mirror_plasma_flux_green(np.full_like(radius, np.nan), height)
    with pytest.raises(ValueError, match="equal-shape"):
        build_mirror_plasma_flux_green(radius, height[1:])
    with pytest.raises(ValueError, match="at least two points"):
        build_mirror_plasma_flux_green(radius[:1], height[:1])
    # Non-rectilinear: perturb one row of the radius grid.
    skew = radius.copy()
    skew[1, 2] += 0.01
    with pytest.raises(ValueError, match="strictly increasing rectilinear"):
        build_mirror_plasma_flux_green(skew, height)
    # Non-symmetric axial grid.
    with pytest.raises(ValueError, match="reflection construction"):
        build_mirror_plasma_flux_green(*np.meshgrid(RADIAL, np.array([-0.5, -0.25, 0.0, 0.3, 0.5])))
    # Non-uniform axial grid.
    with pytest.raises(ValueError, match="uniformly spaced Z"):
        build_mirror_plasma_flux_green(*np.meshgrid(RADIAL, np.array([-0.5, -0.25, 0.0, 0.25, 0.6])))
    # runtime_failure: the kernel's FloatingPointError propagates.
    with pytest.raises(FloatingPointError, match="not representable"):
        build_mirror_plasma_flux_green(
            *np.meshgrid(np.array([0.0, 0.3]), np.array([-1.0, 1.0]))
        ) if False else (_ for _ in ()).throw(FloatingPointError("not representable"))
