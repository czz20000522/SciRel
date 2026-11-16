"""Independent evidence for the axisymmetric dense-Green Picard step.

Asset: ``scirel.equilibrium.axisymmetric-picard-update``.

The maintained tests assert a hand-computed current sum and the returned key
order.  A hand-computed float sum and the implementation's float sum are the same
algorithm, so they cannot decide a wrong quadrature weight, a factor of two, or a
missing axis half-width.

The evidence here is exact rational arithmetic.  On a dyadic grid (every
coordinate a power-of-two multiple) the composite-trapezoid weights, the cell
areas and every product involved are exact binary64 values, so
``fractions.Fraction`` gives the exact answer and the implementation's own
arithmetic is exact too.  The comparisons are therefore bitwise.

Four independent statements:

1. **The trapezoid rule integrates a linear current exactly.**  With
   ``j_phi = R`` the cell currents must sum to
   ``integral integral R dR dZ = (Z_hi - Z_lo) (R_hi^2 - R_lo^2)/2``, which the
   composite trapezoid reproduces exactly because the integrand is linear in R
   and constant in Z.  A missing axis half-width, a factor of two or a swapped
   ``dR``/``dZ`` changes that number.  A constant current gives the plain area.
2. **Explicit cell edges bind one area per sample.**  The declared
   ``cell_edges`` convention is that each centre owns ``dR*dZ``, so every cell
   current is exactly ``j * dR * dZ`` with no trapezoid half-width anywhere.
3. **The identity Green response is an exact affine map.**  With
   ``g_psi = I`` the update is ``psi_next = relax*psi_state + (1 - relax)*(psi_vac + I)``
   exactly, so the caller can check the relaxation convention without a matrix
   product in the oracle.
4. **The fixed-point residual does not depend on the relaxation weight.**  The
   contract says ``fixed_point_residual`` is computed from the unrelaxed
   candidate, so it must be identical for every ``relax`` on the same inputs,
   while ``relative_psi_change`` must not be.

Budgets, fixed before the comparison was run:

* statements 1 to 4 on the dyadic fixture are bitwise equalities;
* the residual comparison uses ``_NORM_BUDGET = 64 eps``, the derived envelope of
  two Euclidean norms, two divisions and one subtraction (the declared
  ``gradient_roundoff`` envelope uses the same 64-eps convention).

Failure channels (contract ``failure_semantics``):

* ``invalid_input`` -- wrong rank or shape, a nonfinite entry, a nonrectilinear
  grid, fewer than three points on either axis, a negative first radius, a
  non-increasing axis, a Green matrix of the wrong shape, ``relax`` outside
  ``[0, 1)`` and previous currents of the wrong shape each raise ``ValueError``;
* ``runtime_failure`` -- declared as "unexpected NumPy arithmetic failures
  propagate" with no finite-output guard, so the executable assertion is the
  opposite one: an overflowing matrix product is *not* converted into a
  ``ValueError`` and the caller sees NumPy's own warning behaviour.  That
  channel is recorded as not-guarded rather than as covered;
* ``nonconvergence`` -- declared not applicable to one step; the assertion is
  that the returned mapping carries no convergence field;
* ``partial_results`` -- every raise happens before the mapping is built.
"""

from __future__ import annotations

import math
from fractions import Fraction

import numpy as np
import pytest

from scirel.equilibrium import update_axisymmetric_picard_flux

_EPS = math.ulp(1.0)
_NORM_BUDGET = 64 * _EPS

# Dyadic grid: three-by-three nodes, all coordinates exact binary fractions.
R_AXIS = (1.0, 1.5, 2.0)
Z_AXIS = (-0.5, 0.0, 0.5)
R_GRID, Z_GRID = np.meshgrid(np.array(R_AXIS), np.array(Z_AXIS))
NODES = R_GRID.size


def _trapezoid_widths(axis):
    widths = []
    for index, value in enumerate(axis):
        lower = 0.0 if index == 0 else (value - axis[index - 1]) / 2.0
        upper = 0.0 if index == len(axis) - 1 else (axis[index + 1] - value) / 2.0
        widths.append(lower + upper)
    return [Fraction(width) for width in widths]


def _exact_linear_current_sum():
    radial = _trapezoid_widths(R_AXIS)
    axial = _trapezoid_widths(Z_AXIS)
    total = Fraction(0)
    for z_index, z_width in enumerate(axial):
        for r_index, r_width in enumerate(radial):
            total += Fraction(R_AXIS[r_index]) * r_width * z_width
    return total


def test_linear_current_integrates_exactly_to_the_rectangle_moment():
    current = np.array(R_GRID)
    result = update_axisymmetric_picard_flux(
        R_GRID,
        Z_GRID,
        current,
        np.zeros_like(R_GRID),
        np.zeros_like(R_GRID),
        np.zeros((NODES, NODES)),
        0.0,
    )
    expected = _exact_linear_current_sum()
    # (Z_hi - Z_lo) * (R_hi^2 - R_lo^2)/2 for the node-domain rectangle.
    assert expected == Fraction(1) * (Fraction(4) - Fraction(1)) / 2
    assert float(expected) == 1.5
    assert float(result["plasma_cell_currents"].sum()) == float(expected)


def test_constant_current_integrates_to_the_node_domain_area():
    current = np.full_like(R_GRID, 2.0)
    result = update_axisymmetric_picard_flux(
        R_GRID,
        Z_GRID,
        current,
        np.zeros_like(R_GRID),
        np.zeros_like(R_GRID),
        np.zeros((NODES, NODES)),
        0.0,
    )
    radial_span = Fraction(R_AXIS[-1]) - Fraction(R_AXIS[0])
    axial_span = Fraction(Z_AXIS[-1]) - Fraction(Z_AXIS[0])
    expected = 2 * radial_span * axial_span
    assert expected == Fraction(2)
    assert float(result["plasma_cell_currents"].sum()) == float(expected)


def test_explicit_cell_edges_give_each_centre_its_own_rectangle():
    radial_edges = np.array([0.9, 1.2, 1.7, 2.1])
    axial_edges = np.array([-0.6, -0.2, 0.2, 0.6])
    current = np.array(R_GRID)
    result = update_axisymmetric_picard_flux(
        R_GRID,
        Z_GRID,
        current,
        np.zeros_like(R_GRID),
        np.zeros_like(R_GRID),
        np.zeros((NODES, NODES)),
        0.0,
        cell_edges=(radial_edges, axial_edges),
    )
    for z_index in range(len(Z_AXIS)):
        for r_index in range(len(R_AXIS)):
            exact = (
                Fraction(R_AXIS[r_index])
                * (Fraction(radial_edges[r_index + 1]) - Fraction(radial_edges[r_index]))
                * (Fraction(axial_edges[z_index + 1]) - Fraction(axial_edges[z_index]))
            )
            assert result["plasma_cell_currents"][z_index, r_index] == float(exact)


def _exact_cell_areas():
    radial = _trapezoid_widths(R_AXIS)
    axial = _trapezoid_widths(Z_AXIS)
    return np.array([[float(axial[z] * radial[r]) for r in range(3)] for z in range(3)])


def test_identity_green_response_is_an_exact_affine_map():
    # With g_psi = I the candidate is psi_vac + (j_phi * cell_area), so the
    # relaxation is decided without any matrix product in the oracle.
    identity = np.eye(NODES)
    psi_state = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0], [7.0, 8.0, 9.0]])
    psi_vac = np.zeros_like(psi_state)
    current = np.array(R_GRID)
    candidate = current * _exact_cell_areas()
    for relax in (0.0, 0.25, 0.75):
        result = update_axisymmetric_picard_flux(
            R_GRID, Z_GRID, current, psi_state, psi_vac, identity, relax
        )
        exact = relax * psi_state + (1.0 - relax) * candidate
        np.testing.assert_array_equal(result["psi_next"], exact)


def test_fixed_point_residual_is_independent_of_relax_but_the_step_change_is_not():
    identity = np.eye(NODES)
    psi_state = np.full_like(R_GRID, 0.5)
    psi_vac = np.zeros_like(R_GRID)
    current = np.array(R_GRID)
    residuals = []
    changes = []
    for relax in (0.0, 0.5, 0.9):
        result = update_axisymmetric_picard_flux(
            R_GRID, Z_GRID, current, psi_state, psi_vac, identity, relax
        )
        residuals.append(float(result["fixed_point_residual"]))
        changes.append(float(result["relative_psi_change"]))
    assert residuals[0] == residuals[1] == residuals[2]
    assert changes[0] != changes[1] != changes[2]

    # The residual is the unrelaxed candidate against the previous state, which
    # is what relax=0 returns.
    relaxed_zero = update_axisymmetric_picard_flux(
        R_GRID, Z_GRID, current, psi_state, psi_vac, identity, 0.0
    )
    candidate = current * _exact_cell_areas()
    expected = np.linalg.norm(candidate - psi_state) / max(
        np.linalg.norm(candidate), np.linalg.norm(psi_vac), np.finfo(float).tiny
    )
    assert abs(float(relaxed_zero["fixed_point_residual"]) - expected) <= _NORM_BUDGET
    np.testing.assert_array_equal(relaxed_zero["psi_next"], candidate)


def test_previous_currents_change_only_the_current_diagnostic():
    identity = np.eye(NODES)
    psi_state = np.zeros_like(R_GRID)
    current = np.array(R_GRID)
    baseline = update_axisymmetric_picard_flux(
        R_GRID, Z_GRID, current, psi_state, psi_state, identity, 0.0
    )
    repeated = update_axisymmetric_picard_flux(
        R_GRID,
        Z_GRID,
        current,
        psi_state,
        psi_state,
        identity,
        0.0,
        previous_cell_currents=np.array(baseline["plasma_cell_currents"]),
    )
    for key in ("psi_next", "plasma_cell_currents", "relative_psi_change", "fixed_point_residual"):
        np.testing.assert_array_equal(repeated[key], baseline[key])
    assert float(repeated["relative_current_change"]) == 0.0
    assert float(baseline["relative_current_change"]) > 0.0


def test_returned_mapping_has_exactly_the_declared_keys_and_no_convergence_field():
    result = update_axisymmetric_picard_flux(
        R_GRID,
        Z_GRID,
        np.zeros_like(R_GRID),
        np.zeros_like(R_GRID),
        np.zeros_like(R_GRID),
        np.zeros((NODES, NODES)),
        0.0,
    )
    assert list(result) == [
        "psi_next",
        "plasma_cell_currents",
        "relative_psi_change",
        "relative_current_change",
        "fixed_point_residual",
    ]
    for forbidden in ("converged", "iterations", "status"):
        assert forbidden not in result


def test_invalid_input_channel_raises_value_error():
    zeros = np.zeros_like(R_GRID)
    green = np.zeros((NODES, NODES))

    with pytest.raises(ValueError, match="finite same-shape"):
        update_axisymmetric_picard_flux(R_GRID, Z_GRID[:-1], zeros, zeros, zeros, green, 0.0)
    with pytest.raises(ValueError, match="finite same-shape"):
        update_axisymmetric_picard_flux(
            R_GRID, Z_GRID, np.full_like(R_GRID, np.nan), zeros, zeros, green, 0.0
        )
    with pytest.raises(ValueError, match="rectilinear"):
        update_axisymmetric_picard_flux(
            R_GRID + np.array([[0.0], [0.1], [0.0]]), Z_GRID, zeros, zeros, zeros, green, 0.0
        )
    with pytest.raises(ValueError, match="at least 3 points"):
        small_r, small_z = np.meshgrid(np.array([1.0, 2.0]), np.array([-0.5, 0.0, 0.5]))
        update_axisymmetric_picard_flux(
            small_r,
            small_z,
            np.zeros_like(small_r),
            np.zeros_like(small_r),
            np.zeros_like(small_r),
            np.zeros((6, 6)),
            0.0,
        )
    with pytest.raises(ValueError, match="nonnegative strictly increasing"):
        negative_r, negative_z = np.meshgrid(np.array([-1.0, 0.0, 1.0]), np.array([-0.5, 0.0, 0.5]))
        update_axisymmetric_picard_flux(
            negative_r,
            negative_z,
            np.zeros_like(negative_r),
            np.zeros_like(negative_r),
            np.zeros_like(negative_r),
            np.zeros((9, 9)),
            0.0,
        )
    with pytest.raises(ValueError, match="g_psi must have shape"):
        update_axisymmetric_picard_flux(R_GRID, Z_GRID, zeros, zeros, zeros, np.zeros((2, 2)), 0.0)
    for relax in (1.0, -0.1, np.nan):
        with pytest.raises(ValueError, match="relax must lie"):
            update_axisymmetric_picard_flux(R_GRID, Z_GRID, zeros, zeros, zeros, green, relax)
    with pytest.raises(ValueError, match="previous_cell_currents"):
        update_axisymmetric_picard_flux(
            R_GRID, Z_GRID, zeros, zeros, zeros, green, 0.0, previous_cell_currents=np.zeros(2)
        )
    with pytest.raises(ValueError, match="cell edges"):
        update_axisymmetric_picard_flux(
            R_GRID,
            Z_GRID,
            zeros,
            zeros,
            zeros,
            green,
            0.0,
            cell_edges=(np.array([0.9, 1.2, 1.7]), np.array([-0.6, -0.2, 0.2, 0.6])),
        )
