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
    for target_index, source_index in [(1, 4), (2, 5), (4, 7), (5, 11), (7, 13), (8, 10)]:
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
    # Nonzero anchors: the unit-weight flux response is positive for every
    # off-axis pair (A_phi has a positive integrand), and the entries differ
    # across the grid, so a zero matrix or a constant matrix fails here even
    # though it would satisfy a purely relative comparison.
    assert matrix[4, 1] > 0.0
    assert matrix[13, 11] > 0.0
    assert matrix[4, 1] != matrix[13, 11]


def test_coincident_entries_are_exactly_zero_and_neighbours_are_not():
    """Evidence 2: the discrete zero-self convention of the flux matrix."""
    matrix = _matrix()
    np.testing.assert_array_equal(np.diag(matrix), 0.0)
    # The off-diagonal entries away from the axis are all nonzero; the axis
    # index set is the only other source of zeros and is checked separately.
    for row in range(len(AXIAL)):
        for column in (1, 2):
            for other in (1, 2):
                if row == 0 and column == other:
                    continue
                assert matrix[row * len(RADIAL) + column, (row - 1) * len(RADIAL) + other] != 0.0


def _reflected_indices():
    """Return the flat node index after reflecting Z about zero, R unchanged."""
    nodes = len(RADIAL) * len(AXIAL)
    return [
        (len(AXIAL) - 1 - index // len(RADIAL)) * len(RADIAL) + index % len(RADIAL)
        for index in range(nodes)
    ]


def test_reflected_blocks_match_bitwise():
    """Evidence 3: G[target, source] == G[mirror(target), mirror(source)]."""
    matrix = _matrix()
    mirror = _reflected_indices()
    assert mirror != list(range(len(mirror)))
    assert np.array_equal(matrix[np.ix_(mirror, mirror)], matrix)
    # A second, independent structural identity: with the target nodes also
    # serving as sources, the unit-weight mutual flux matrix must be exactly
    # symmetric.  A one-sided assembly error (for example a modulus built from
    # the target radius only) breaks this while leaving item 1 intact at a few
    # diagonal-adjacent entries.
    assert np.array_equal(matrix, matrix.T)
    assert np.any(matrix != 0.0)


def test_axis_nodes_carry_no_source_and_receive_no_response():
    """Evidence 4: the R = 0 half of the same convention."""
    matrix = _matrix()
    axis_rows = [row * len(RADIAL) for row in range(len(AXIAL))]
    for row in axis_rows:
        np.testing.assert_array_equal(matrix[row, :], 0.0)
        np.testing.assert_array_equal(matrix[:, row], 0.0)
    axis = set(axis_rows)
    for row in range(len(AXIAL)):
        for column in range(len(RADIAL)):
            index = row * len(RADIAL) + column
            if index in axis:
                continue
            # A non-axis node responds to a different non-axis node.
            assert matrix[index, index + 1 if column + 1 < len(RADIAL) else index - 1] != 0.0


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
    # Non-uniform but still symmetric axial grid: only the spacing test fires.
    with pytest.raises(ValueError, match="uniformly spaced Z"):
        build_mirror_plasma_flux_green(*np.meshgrid(RADIAL, np.array([-0.5, -0.1, 0.0, 0.1, 0.5])))
    # runtime_failure: see
    # ``test_no_finite_unit_weight_grid_can_make_an_entry_unrepresentable``.
    # This asset has no weight input, so the channel is bounded by the geometry
    # and is not exercisable; the assertion below records the boundary instead
    # of fabricating a raise.


def test_no_finite_unit_weight_grid_can_make_an_entry_unrepresentable():
    """The ``runtime_failure`` channel is unreachable, and here is why.

    With unit sources the entry is ``1e-7 * d * [(2-m)K - 2E]``.  The bracket is
    bounded by ``2 K``, and ``K`` grows only like ``log(4 d / gap)``; the
    smallest achievable ``gap`` for two distinct binary64 coordinates of size
    ``d`` is one ulp of ``d``, so the bracket stays below about 80 and the entry
    below ``1e-5 * a``.  A finite ``a`` therefore cannot push the entry past
    ``1.8e308``.  The largest finite coordinates confirm it: the flux stays
    finite, and only the *validation* rejects the unrepresentable geometry.
    """
    largest = np.finfo(float).max
    radius, height = np.meshgrid(
        np.array([0.0, 0.125, 0.25]) * largest, np.array([-0.5, -0.25, 0.0, 0.25, 0.5])
    )
    with np.errstate(all="ignore"):
        matrix = build_mirror_plasma_flux_green(radius, height)["g_psi"]
    assert np.all(np.isfinite(matrix))
    assert np.any(matrix != 0.0)
