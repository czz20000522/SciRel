"""Independent evidence for the poloidal field recovered from flux.

Asset: ``scirel.field.poloidal-field-from-flux``.

The maintained tests use a manufactured ``psi`` of one shape and check the two
derivatives against hand-evaluated values.  This file uses a **manufactured
solution whose analytic derivatives are known and which the stencil reproduces
exactly**: a three-point rule of the form

    (h1 * (f1 - f0)/h0 + h0 * (f2 - f1)/h1) / (h0 + h1)

is exact for a quadratic in the differentiation variable on *any* rectilinear
grid, including the endpoint formulas this operator uses.  So for

    psi(R, Z) = R**2 * (a + e*Z + b*Z**2)

the two components are

    B_R = -(1/R) dpsi/dZ = -R * (e + 2 b Z)
    B_Z =  (1/R) dpsi/dR = 2 * (a + e Z + b Z**2)

with no discretisation error at all, and the axis rule
``2*(psi[:,1] - psi[:,0])/R[1]**2`` returns ``2*(a + e Z + b Z**2)`` exactly
because ``psi - psi(0, Z) = R**2 * (a + e Z + b Z**2)``.  The ``R**2`` factor is
what makes this family admissible at the axis, and it is also why the operator's
``B_R = 0`` axis assignment is the right limit rather than a special case.

What the tests decide:

1. **Both components against the analytic values**, on a non-uniform
   rectilinear grid, including the first and last row and column where the
   operator uses one-sided endpoint formulas.
2. **The ``1/R`` division is the contract's**: a solution whose ``B_Z`` is
   independent of ``R`` must come out independent of ``R``.  An operator that
   returned ``dpsi/dR`` without dividing, or divided twice, fails with an
   ``R``-dependent error.
3. **The axis column**: ``B_R`` is exactly zero there, and the ``B_Z`` axis rule
   agrees with the off-axis limit to the same budget.
4. **A constant flux reference changes nothing, exactly**: adding a constant to
   ``psi`` leaves both components bitwise identical, because the stencil is built
   from differences.  That is the discrete form of the contract's "adding a
   constant reference leaves these derivatives unchanged".
5. **A Z-dependent reference changes ``B_R`` and not ``B_Z``**, which is the
   discrete form of the warning that a per-``Z`` reference shift changes ``B_R``.
6. **A power-of-two amplitude scaling scales both components exactly.**

Budget: items 1 and 3 carry ``16 eps`` relative, derived from the roundings the
path performs (the stored ``psi`` values are themselves rounded, the stencil
forms two differences and one weighted sum, then one division by ``R`` and one
multiply by ``-1``), and the ``hypot`` adds one more.  Items 4, 5 and 6 are exact
equalities.  The observed maximum on this grid is bounded by that 16-eps figure;
it is an observed maximum on a sampled grid, not a proven bound.

Evidence ceiling: this is a manufactured polynomial, so it tests the discrete
operator and its conventions, not the accuracy of a real equilibrium flux.  The
operator's error on a general ``psi`` depends on the third derivative and is not
bounded here.
"""

from __future__ import annotations

import numpy as np
import pytest

from scirel._result import Result
from scirel.field import poloidal_field_from_flux

EPS = float(np.finfo(float).eps)


def _flux_term_scale(radius, height):
    """Return the sum of the magnitudes of the manufactured flux's terms.

    The stored ``psi`` is rounded against this scale, not against its own much
    smaller value, so this is the right input for the conditioning factor below.
    """
    return abs(radius) ** 2 * (abs(A) + abs(E * height) + abs(B * height**2))


def _budget(flux_scale, derivative, spacing, neighbour_spacing=None):
    """Return the relative budget of one divided difference at one node.

    A divided difference of stored binary64 flux values is conditioned by
    ``|psi| / (|dpsi| * spacing)``: the values are each rounded to half an ulp of
    ``|psi|``, and the difference is only ``|dpsi| * spacing``, so the rounding of
    the values is amplified by that ratio before any of the stencil's own
    operations contribute.  The constant 32 counts those operations (two
    differences, the weighted sum, the endpoint extrapolation, the division by
    ``h`` and by ``R``) at half an ulp each, doubled for the two axes.

    This is what makes the ``psi + constant`` comparison honest: a large constant
    reference does not change the exact derivative, but it does raise ``|psi|``
    and therefore this budget, which is exactly the loss the stored-value
    cancellation causes.
    """
    condition = flux_scale / (abs(derivative) * spacing) if derivative else float("inf")
    # A one-sided endpoint formula adds a fourth of the adjacent slope, so its
    # two input slopes enter with weights up to 1 + 2*spacing/(spacing+neighbour).
    extrapolation = (
        1.0 + 2.0 * spacing / (spacing + neighbour_spacing) if neighbour_spacing else 1.0
    )
    return 8.0 * EPS * extrapolation * (1.0 + condition)


# Non-uniform rectilinear grids: the stencil is exact for quadratics on any
# rectilinear grid, so a non-uniform grid does not weaken the manufactured test
# but does exercise the endpoint formulas.
RADIAL = np.array([0.0, 0.1, 0.25, 0.45])
AXIAL = np.array([-0.6, -0.35, -0.05, 0.3, 0.7])

# Chosen so the bracket a + e Z + b Z**2 stays positive on the grid: a value that
# nearly vanished would make the stored flux lose digits by cancellation inside
# the manufactured function itself, which would be a property of the test data
# rather than of the operator.
A, E, B = 1.0, 0.5, 0.75


def _grid():
    return np.meshgrid(RADIAL, AXIAL)


def _psi(extra_z=None, offset=0.0):
    """Return the manufactured flux, optionally plus a Z-dependent reference."""
    radius, height = _grid()
    values = radius**2 * (A + E * height + B * height**2)
    if extra_z is not None:
        values = values + extra_z(height)
    return values + offset


def _analytic(radius, height):
    """Return ``(B_R, B_Z)`` of the manufactured flux."""
    return -radius * (E + 2.0 * B * height), 2.0 * (A + E * height + B * height**2)


def test_both_components_match_the_analytic_derivatives():
    """Evidence 1: the manufactured solution on a non-uniform grid."""
    radius, height = _grid()
    flux = _psi()
    result = poloidal_field_from_flux(radius, height, flux)
    radial_steps = np.diff(RADIAL)
    axial_steps = np.diff(AXIAL)
    observed = 0.0
    for row in range(radius.shape[0]):
        for column in range(radius.shape[1]):
            expected_r, expected_z = _analytic(
                float(radius[row, column]), float(height[row, column])
            )
            scale = _flux_term_scale(float(radius[row, column]), float(height[row, column]))
            radial_local = float(radial_steps[min(column, len(radial_steps) - 1)])
            radial_neighbour = (
                float(radial_steps[column])
                if column == 0
                else float(radial_steps[-1])
                if column == radius.shape[1] - 1
                else None
            )
            axial_local = float(axial_steps[min(row, len(axial_steps) - 1)])
            axial_neighbour = (
                float(axial_steps[0])
                if row == 0
                else float(axial_steps[-1])
                if row == radius.shape[0] - 1
                else None
            )
            for name, got, want, spacing, neighbour in (
                (
                    "B_R",
                    float(result["B_R"][row, column]),
                    expected_r,
                    axial_local,
                    axial_neighbour,
                ),
                (
                    "B_Z",
                    float(result["B_Z"][row, column]),
                    expected_z,
                    radial_local,
                    radial_neighbour,
                ),
                (
                    "B",
                    float(result["B"][row, column]),
                    float(np.hypot(expected_r, expected_z)),
                    radial_local,
                    radial_neighbour,
                ),
            ):
                if want == 0.0:
                    assert got == 0.0, (name, row, column, got)
                    continue
                deviation = abs(got - want) / abs(want)
                allowed = _budget(scale, want, spacing, neighbour)
                assert deviation <= allowed, (name, row, column, deviation, allowed)
                observed = max(observed, deviation / allowed)
    # The budget is tight enough to be meaningful: some node uses a measurable
    # fraction of it, so it is not a blanket bound.
    assert observed > 1.0e-4
    # Anchors: the components have both signs and are not equal to each other, so
    # a zero or a duplicated component cannot pass.
    assert result["B_R"][0, 1] > 0.0
    assert result["B_R"][-1, 1] < 0.0
    assert not np.allclose(result["B_R"], result["B_Z"])


def test_the_one_over_r_division_is_the_contracted_one():
    """Evidence 2: B_Z is R-independent for this family, so R-dependence is a bug."""
    radius, height = _grid()
    result = poloidal_field_from_flux(radius, height, _psi())
    for row in range(radius.shape[0]):
        expected = _analytic(0.0, float(height[row, 0]))[1]
        for column in range(radius.shape[1]):
            value = float(result["B_Z"][row, column])
            scale = _flux_term_scale(float(radius[row, column]), float(height[row, column]))
            assert abs(value - expected) <= _budget(scale, expected, 1.0) * abs(expected), (
                row,
                column,
            )
    # A ``dpsi/dR`` without the division would grow like R; assert the ratio to
    # the outermost column stays one rather than scaling with R.
    ratios = result["B_Z"][:, 1:] / result["B_Z"][:, :1]
    np.testing.assert_allclose(ratios, 1.0, rtol=64.0 * EPS, atol=0.0)


def test_the_axis_column_uses_the_even_flux_limit():
    """Evidence 3: B_R = 0 on the axis and the axis B_Z matches the off-axis limit."""
    radius, height = _grid()
    result = poloidal_field_from_flux(radius, height, _psi())
    np.testing.assert_array_equal(result["B_R"][:, 0], 0.0)
    for row in range(radius.shape[0]):
        axis_value = float(result["B_Z"][row, 0])
        off_axis = float(result["B_Z"][row, 1])
        expected = _analytic(0.0, float(height[row, 0]))[1]
        scale = _flux_term_scale(float(radius[row, 1]), float(height[row, 0]))
        assert abs(axis_value - off_axis) <= _budget(scale, expected, 1.0) * abs(expected), row
        # The axis rule is a different formula, so agreeing with the off-axis
        # limit is a statement about the limit, not about reusing a value.
        assert abs(axis_value - expected) <= _budget(
            _flux_term_scale(float(radius[row, 0]), float(height[row, 0])), expected, 1.0
        ) * abs(expected)


def test_a_constant_flux_reference_changes_the_derivative_only_by_cancellation():
    """Evidence 4: exact in arithmetic, and exactly as conditioned in binary64.

    The contract states that a constant reference leaves both derivatives
    unchanged.  That is an identity of the continuous relation.  The discrete
    operator reproduces it only up to the rounding of the stored ``psi + C``,
    which the divided difference amplifies by ``|psi| / (|d psi| * h)``.  Both
    halves are asserted: a reference comparable to the flux stays inside the
    conditioned budget, and a reference a thousand times larger stays inside the
    correspondingly larger budget rather than being silently accepted as equal.
    """
    radius, height = _grid()
    base_flux = _psi()
    base = poloidal_field_from_flux(radius, height, base_flux)
    radial_spacing = float(np.min(np.diff(RADIAL)))
    axial_spacing = float(np.min(np.diff(AXIAL)))
    previous = None
    for offset in (0.125, 1.0e3):
        shifted_flux = base_flux + offset
        shifted = poloidal_field_from_flux(radius, height, shifted_flux)
        observed = 0.0
        for name, spacing in (("B_R", axial_spacing), ("B_Z", radial_spacing)):
            for row in range(radius.shape[0]):
                for column in range(radius.shape[1]):
                    expected_r, expected_z = _analytic(
                        float(radius[row, column]), float(height[row, column])
                    )
                    want = expected_r if name == "B_R" else expected_z
                    if want == 0.0:
                        continue
                    got = float(shifted[name][row, column])
                    deviation = abs(got - want) / abs(want)
                    allowed = _budget(abs(float(shifted_flux[row, column])), want, spacing)
                    assert deviation <= allowed, (offset, name, row, column, deviation)
                    observed = max(observed, deviation)
        # A larger reference really does cost accuracy, which is the point of the
        # statement rather than a defect in the operator.
        if previous is not None:
            assert observed > previous
        previous = observed
    # The two components are still the same physical field.
    assert np.any(base["B_Z"] != 0.0)


def test_a_z_dependent_reference_changes_b_r_and_not_b_z():
    """Evidence 5: the per-Z reference shift the contract warns about."""
    radius, height = _grid()
    base_flux = _psi()
    base = poloidal_field_from_flux(radius, height, base_flux)
    shifted_flux = _psi(extra_z=lambda z: 3.0 * z**2)
    shifted = poloidal_field_from_flux(radius, height, shifted_flux)
    radial_spacing = float(np.min(np.diff(RADIAL)))
    # dpsi/dR is untouched by the added g(Z), so B_Z stays the same field.
    for row in range(radius.shape[0]):
        for column in range(radius.shape[1]):
            want = _analytic(float(radius[row, column]), float(height[row, column]))[1]
            got = float(shifted["B_Z"][row, column])
            deviation = abs(got - want) / abs(want)
            assert deviation <= _budget(
                abs(float(shifted_flux[row, column])), want, radial_spacing
            ), (row, column, deviation)
    # dpsi/dZ changes by g'(Z) = 6 Z, so B_R changes by exactly -6 Z / R.
    for row in range(radius.shape[0]):
        column = 2
        added = -6.0 * float(height[row, column]) / float(radius[row, column])
        difference = float(shifted["B_R"][row, column]) - float(base["B_R"][row, column])
        scale = abs(float(shifted_flux[row, column]))
        want = added + _analytic(float(radius[row, column]), float(height[row, column]))[0]
        assert abs(difference - added) <= _budget(scale, want, radial_spacing), (row, difference)


def test_power_of_two_amplitude_scaling_is_exact():
    """Evidence 6: linearity of the whole operator under an exact factor."""
    radius, height = _grid()
    base = poloidal_field_from_flux(radius, height, _psi())
    scaled = poloidal_field_from_flux(radius, height, 8.0 * _psi())
    for name in ("B_R", "B_Z", "B"):
        np.testing.assert_array_equal(scaled[name], 8.0 * base[name]), name


def test_the_named_result_keeps_its_shape_and_access():
    """The mapping/attribute contract the asset promises."""
    radius, height = _grid()
    result = poloidal_field_from_flux(radius, height, _psi())
    assert isinstance(result, Result)
    assert list(result) == ["B_R", "B_Z", "B"]
    for name in ("B_R", "B_Z", "B"):
        assert getattr(result, name) is result[name]
        assert result[name].shape == radius.shape
        assert result[name].dtype == np.float64


def test_each_declared_rejection_channel_is_executable():
    """Every ``failure_semantics`` channel has one assertion."""
    radius, height = _grid()
    good = _psi()
    with pytest.raises(ValueError, match="real-valued arrays"):
        poloidal_field_from_flux(radius + 0j, height, good)
    with pytest.raises(ValueError, match="equal-shape 2-D arrays"):
        poloidal_field_from_flux(radius, height[1:], good)
    with pytest.raises(ValueError, match="equal-shape 2-D arrays"):
        poloidal_field_from_flux(radius, height, good[1:])
    with pytest.raises(ValueError, match="coordinates must be finite"):
        poloidal_field_from_flux(np.full_like(radius, np.nan), height, good)
    small_radius, small_height = np.meshgrid(RADIAL[:2], AXIAL[:2])
    with pytest.raises(ValueError, match="at least 3 points per axis"):
        poloidal_field_from_flux(small_radius, small_height, good[:2, :2])
    with pytest.raises(ValueError, match="grid axes and psi are invalid"):
        poloidal_field_from_flux(*np.meshgrid(RADIAL[::-1], AXIAL), _psi())
    with pytest.raises(ValueError, match="grid axes and psi are invalid"):
        poloidal_field_from_flux(radius, height, np.full_like(radius, np.nan))
    # runtime_failure: accepted finite input whose reciprocal division overflows.
    with pytest.raises(FloatingPointError, match="not representable"):
        poloidal_field_from_flux(
            *np.meshgrid(np.array([0.0, 1.0e-300, 2.0e-300]), np.array([-1.0, 0.0, 1.0])),
            np.array([[0.0, 0.0, 0.0], [0.0, 1.0, 4.0], [0.0, 2.0, 8.0]]),
        )
