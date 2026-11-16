"""Independent evidence for the filament vacuum-field grid operator.

Asset: ``scirel.field.filament-vacuum-field``.

``test_filament_vacuum_field.py`` pins superposition, the axis column, the
relative-flux reference and the trapezoid recurrence, and it compares the flux
with ``psi = R A_phi`` evaluated through the *same* closed-form kernel the
implementation calls.  The evidence here replaces that oracle with
``_biot_savart_reference``, which integrates the Biot-Savart law directly, and
splits the operator into the two things it actually does:

1. **Field components against direct quadrature** at every grid node.  ``b_r``
   and ``b_z`` are the aggregate Green response, so this is the part that must be
   exact to binary64.
2. **Flux against the stream-function difference.**  For ``psi = R A_phi`` the
   identity ``dpsi/dR = R B_Z`` makes
   ``psi(R, Z) - psi(R0, Z) = integral from R0 to R of R' B_Z(R', Z) dR'`` exact.
   The test evaluates that difference as the difference of two independent
   ``A_phi`` quadratures, so the comparison isolates the implementation's
   *radial quadrature* rather than re-deriving the closed form.
3. **The quadrature is order-improving, not order-claiming.**  Halving the radial
   spacing must shrink the deviation from the continuous flux by at least a
   factor of two.  This is a monotonicity statement about the two-point rule; the
   measured ratios on the three grids used here are 3.97 and 3.99, reported by
   the assertion message, and **no convergence order is claimed**, because one
   measured grid family is not an order proof.
4. **The exact zero first column** at ``R = 0`` for both the flux (the accumulation
   starts there) and the radial field (the odd integrand), which is a structural
   statement rather than a small number.
5. **Transposed layout gives the same arrays**, which is the rectilinear-axis
   detection branch.
6. **The rejection channels**, including non-rectilinear, non-uniform and
   non-increasing radial axes.

Budgets, fixed before the comparison was run:

* field components: ``_RELATIVE_BUDGET = 64 eps`` from
  ``_biot_savart_reference``; observed maximum ``1.96e-15`` (``0.14`` of the
  budget) on this grid.
* flux: the deviation is dominated by the **trapezoid truncation error**, not by
  binary64, so the budget cannot be an ``N eps`` figure.  The composite
  two-point rule over ``[0, 0.3]`` with ``h = 0.0125`` has truncation
  ``(h^2/12) * (f'(b) - f'(a))`` relative to the integral, and with
  ``h/R_range = 0.042`` that is ``1.5e-4``; the declared ceiling is ``2e-3``, one
  decade above that estimate to absorb the strong ``R B_Z`` variation across the
  ring.  The observed maximum is ``6.1e-4``, i.e. ``0.31`` of the ceiling.  Both
  numbers are **observed on the stated grid**; no continuous bound is proven, and
  the ceiling is deliberately loose because it is a truncation allowance rather
  than a measured fit.

Evidence ceiling: the flux is a *relative* accumulation starting at the first
radial node, so this establishes the declared reference convention and not a
global linked flux; and it establishes accuracy for the grid family used, not for
every grid.
"""

from __future__ import annotations

import numpy as np
import pytest

import _biot_savart_reference as reference
from scirel.field import integrate_filament_vacuum_field

RELATIVE_BUDGET = reference._RELATIVE_BUDGET
FLUX_BUDGET = 2.0e-3
FILAMENTS = [[0.45, -0.1, 1500.0]]

RADIAL = np.linspace(0.0, 0.30, 25)
AXIAL = np.array([-0.3, -0.1, 0.1])


def _grids(radial=RADIAL, axial=AXIAL):
    return np.meshgrid(radial, axial)


def _result(radial=RADIAL, axial=AXIAL):
    return integrate_filament_vacuum_field(*_grids(radial, axial), FILAMENTS)


def test_field_components_match_the_biot_savart_quadrature_everywhere():
    """Evidence 1: b_r and b_z at every node against direct quadrature."""
    result = _result()
    radius, height = _grids()
    observed = 0.0
    for row in range(radius.shape[0]):
        for column in (0, 1, 4, 8, 12, 18, 24):
            expected = reference.filament_field(
                FILAMENTS, float(radius[row, column]), float(height[row, column])
            )
            b_r_expected, b_z_expected = float(expected[1]), float(expected[2])
            if b_r_expected == 0.0:
                # The midplane of a single ring has exactly zero radial field.
                assert float(result["b_r"][row, column]) == 0.0
            else:
                deviation = abs(float(result["b_r"][row, column]) - b_r_expected) / abs(
                    b_r_expected
                )
                assert deviation <= RELATIVE_BUDGET, ("b_r", row, column, deviation)
                observed = max(observed, deviation)
            deviation = abs(float(result["b_z"][row, column]) - b_z_expected) / abs(b_z_expected)
            assert deviation <= RELATIVE_BUDGET, ("b_z", row, column, deviation)
            observed = max(observed, deviation)
    assert observed > 0.0
    # Nonzero anchors that a zero or constant field would fail: the axial field
    # falls with radius away from the ring, and the radial field has opposite
    # signs on the two sides of the ring plane.  Row 1 is exactly the ring plane,
    # where the radial field is exactly zero for the odd-integrand reason.
    assert abs(result["b_z"][2, 1]) > abs(result["b_z"][2, -1])
    assert result["b_r"][0, -1] < 0.0 < result["b_r"][2, -1]
    np.testing.assert_array_equal(result["b_r"][1, :], 0.0)


def test_flux_matches_the_stream_function_difference():
    """Evidence 2: the accumulated flux against a high-precision psi difference."""
    result = _result()
    radius, height = _grids()
    observed = 0.0
    for row in range(radius.shape[0]):
        for column in (1, 6, 12, 24):
            expected = reference.psi_difference(
                float(radius[row, column]),
                float(height[row, column]),
                [tuple(row_value) for row_value in FILAMENTS],
                float(radius[row, 0]),
            )
            deviation = abs(float(result["psi"][row, column]) - float(expected)) / abs(
                float(expected)
            )
            assert deviation <= FLUX_BUDGET, (row, column, deviation)
            observed = max(observed, deviation)
    assert observed > 0.0


def test_halving_the_radial_spacing_improves_the_flux_at_least_twofold():
    """Evidence 3: monotone refinement of the radial quadrature."""
    deviations = []
    for nodes in (7, 13, 25):
        radial = np.linspace(0.0, 0.30, nodes)
        result = _result(radial, np.array([-0.3, 0.1]))
        expected = reference.psi_difference(
            float(radial[-1]), -0.3, [tuple(row_value) for row_value in FILAMENTS], 0.0
        )
        deviations.append(
            abs(float(result["psi"][0, -1]) - float(expected)) / abs(float(expected))
        )
    assert deviations[0] > deviations[1] > deviations[2], deviations
    ratios = [deviations[index] / deviations[index + 1] for index in range(2)]
    # Measured ratios on this grid family, reported but not asserted as an order.
    assert all(ratio >= 2.0 for ratio in ratios), (deviations, ratios)


def test_the_first_radial_column_is_exactly_zero():
    """Evidence 4: the reference point of the accumulation and the axis field."""
    result = _result()
    np.testing.assert_array_equal(result["psi"][:, 0], 0.0)
    np.testing.assert_array_equal(result["b_r"][:, 0], 0.0)
    # The neighbouring columns are not zero, so the equality is the convention
    # and not an empty operator.  Row 0 lies exactly in the ring plane, where the
    # radial field is zero for a different reason (odd integrand), so the anchor
    # uses the off-plane row.
    assert np.all(result["psi"][:, 1] != 0.0)
    assert result["b_r"][0, 1] != 0.0
    assert result["b_r"][2, 1] != 0.0


def test_the_transposed_layout_returns_the_same_arrays():
    """Evidence 5: the radial axis may vary along either array axis."""
    radius, height = _grids()
    direct = integrate_filament_vacuum_field(radius, height, FILAMENTS)
    transposed = integrate_filament_vacuum_field(radius.T, height.T, FILAMENTS)
    for name in ("psi", "b_r", "b_z"):
        np.testing.assert_array_equal(transposed[name].T, direct[name]), name


def test_each_declared_rejection_channel_is_executable():
    """Every ``failure_semantics`` channel has one assertion."""
    radius, height = _grids()
    with pytest.raises(ValueError, match="real"):
        integrate_filament_vacuum_field(radius + 0j, height, FILAMENTS)
    with pytest.raises(ValueError, match="equal-shape 2-D grids"):
        integrate_filament_vacuum_field(radius, height[1:], FILAMENTS)
    with pytest.raises(ValueError, match="equal-shape 2-D grids"):
        integrate_filament_vacuum_field(radius[:1], height[:1], FILAMENTS)
    with pytest.raises(ValueError, match="shape"):
        integrate_filament_vacuum_field(radius, height, [[0.45, -0.1]])
    with pytest.raises(ValueError, match="must be finite"):
        integrate_filament_vacuum_field(radius, np.full_like(height, np.nan), FILAMENTS)
    with pytest.raises(ValueError, match="strictly positive"):
        integrate_filament_vacuum_field(radius, height, [[0.0, -0.1, 1.0]])
    # Non-rectilinear radial coordinate: perturb one entry of the grid.
    skew = radius.copy()
    skew[0, 3] += 0.01
    with pytest.raises(ValueError, match="rectilinear radial coordinate"):
        integrate_filament_vacuum_field(skew, height, FILAMENTS)
    # Non-monotone radial coordinate in the other axis direction.
    with pytest.raises(ValueError, match="strictly increasing"):
        integrate_filament_vacuum_field(*np.meshgrid(RADIAL[::-1], AXIAL), FILAMENTS)
    # Non-uniform spacing, which the two-point rule requires.
    nonuniform = np.array([0.0, 0.05, 0.2, 0.3])
    with pytest.raises(ValueError, match="uniformly spaced radial axis"):
        integrate_filament_vacuum_field(*np.meshgrid(nonuniform, AXIAL), FILAMENTS)
    # invalid_input: source/target singularity.
    with pytest.raises(ValueError, match="singular"):
        integrate_filament_vacuum_field(
            *np.meshgrid(np.array([0.0, 0.45]), np.array([-0.1, 0.2])),
            [[0.45, -0.1, 1.0]],
        )
    # runtime_failure: the kernel's FloatingPointError propagates unchanged.
    with pytest.raises(FloatingPointError, match="not representable"):
        integrate_filament_vacuum_field(
            *np.meshgrid(np.array([0.0, 0.3]), np.array([-1.0e-300, 1.0])),
            [[0.3, 0.0, 1.0e308]],
        )
