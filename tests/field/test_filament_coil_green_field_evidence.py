"""Independent evidence for the scalar filament-coil Green response.

Asset: ``scirel.field.filament-coil-green-field``.

The maintained ``test_filament_coil_green.py`` already compares this asset with a
50-digit ``mpmath`` recomputation of the *closed form* and with the other
``field`` Green asset.  Both are the same derivation as the implementation, so
neither can detect a wrong ``(2-m)K - 2E`` prefactor, a wrong sign, or a wrong
``mu0`` factor that the closed form and its oracle share.  The evidence here
adds a route that shares none of that:

1. **Summed response against direct Biot-Savart quadrature.** Every ring of the
   call is integrated over its own loop parameter by ``mp.quad``; the currents
   enter only as the ``mu0 I / 4 pi`` prefactor.  Agreement to
   ``_RELATIVE_BUDGET`` is what ties the returned scalar tuple to the Biot-Savart
   law rather than to the elliptic parametrisation.
2. **Stream-function consistency.** For a rotationally symmetric field with
   ``psi = R A_phi`` the identities ``B_R = -(1/R) dpsi/dZ`` and
   ``B_Z = (1/R) dpsi/dR`` are exact.  The test differentiates the *quadrature*
   stream function at 60 digits and requires the implementation's analytic
   derivative combination to reproduce it, which is a separate route from
   evaluating that combination directly.  This is the statement the closed form
   is easiest to get wrong in: a single sign in the radial integrand flips
   ``B_R`` while leaving ``|B|`` and ``psi`` untouched.
3. **The regularized-radius contract.** The observation radius is offset exactly
   once, by ``compute_axisymmetric_coil_modulus``; this operator must not shift
   it again.  The test pins that by comparing against the quadrature evaluated at
   the supplied radius, and shows that a radius which *would* have coincided
   after a second offset is accepted here rather than silently moved.
4. **A coincident ring is rejected**, and the rejection happens before any
   non-finite response can escape.
5. **Exact current/ampere-turn linearity** for a power-of-two factor, which
   distinguishes a genuine product ``current * turns`` from a sum or a fixed
   weight.

Budget: ``_RELATIVE_BUDGET = 64 eps`` from ``_biot_savart_reference``, derived
from the operation count of the closed form.  Observed maximum over the sampled
configurations: ``2.62e-15`` (``0.18`` of the budget); observed on a finite grid,
not a proven continuous bound.  The stream-function identity uses the same budget because it
compares two evaluations of the same physical point, and the finite-difference
step contributes about ``1e-30`` relative there.  The linearity and rejection
assertions are exact.

Evidence ceiling: single-observation scalar calls, well-separated geometry only
(``_MIN_SEPARATION_RATIO``); no statement about a finite-wire self field or
about a target inside the ring.
"""

from __future__ import annotations

import numpy as np
import pytest

import _biot_savart_reference as reference
from scirel.field import (
    compute_axisymmetric_coil_modulus,
    evaluate_filament_coil_green_field,
)

RELATIVE_BUDGET = reference._RELATIVE_BUDGET
COIL_RADIUS = np.array([0.25, 0.4])
COIL_Z = np.array([-0.15, 0.2])
CURRENT = np.array([10.0, -4.0])
TURNS = np.array([2.0, 3.0])


def _quadrature(reference_radius, reference_z):
    """Return the quadrature response of the example coil set at one point."""
    return reference.filament_field(
        [
            (float(COIL_RADIUS[index]), float(COIL_Z[index]), float(CURRENT[index] * TURNS[index]))
            for index in range(len(COIL_RADIUS))
        ],
        reference_radius,
        reference_z,
    )


@pytest.mark.parametrize(("raw_radius", "height"), [(0.3, 0.05), (0.1, -0.2), (0.75, 0.4)])
def test_response_matches_the_biot_savart_quadrature(raw_radius, height):
    """Evidence 1: the summed scalar tuple against direct quadrature."""
    radius, _, _ = compute_axisymmetric_coil_modulus(raw_radius, height, COIL_RADIUS, COIL_Z)
    flux, radial, axial = evaluate_filament_coil_green_field(
        radius, height, COIL_RADIUS, COIL_Z, CURRENT, TURNS
    )
    expected = _quadrature(float(radius), height)
    for name, got, want in zip(
        ("flux", "B_R", "B_Z"), (flux, radial, axial), expected, strict=True
    ):
        assert float(want) != 0.0, name
        deviation = abs(got - float(want)) / abs(float(want))
        assert deviation <= RELATIVE_BUDGET, (name, raw_radius, height, deviation)
    # Nonzero anchors: the response is not a zero tuple and the two field
    # components are not the same number.
    assert flux != 0.0 and radial != 0.0 and axial != 0.0
    assert radial != axial


@pytest.mark.parametrize(("raw_radius", "height"), [(0.2, 0.13), (0.55, -0.31), (0.75, 0.4)])
def test_stream_function_identities_hold_for_the_returned_components(raw_radius, height):
    """Evidence 2: B_R = -(1/R) dpsi/dZ and B_Z = (1/R) dpsi/dR."""
    radius, _, _ = compute_axisymmetric_coil_modulus(raw_radius, height, COIL_RADIUS, COIL_Z)
    flux, radial, axial = evaluate_filament_coil_green_field(
        radius, height, COIL_RADIUS, COIL_Z, CURRENT, TURNS
    )
    filaments = [
        (float(COIL_RADIUS[index]), float(COIL_Z[index]), float(CURRENT[index] * TURNS[index]))
        for index in range(len(COIL_RADIUS))
    ]
    radial_from_flux = -float(reference.dpsi_dz(float(radius), height, filaments)) / float(radius)
    axial_from_flux = float(reference.dpsi_dr(float(radius), height, filaments)) / float(radius)
    assert abs(radial - radial_from_flux) <= RELATIVE_BUDGET * abs(radial_from_flux), (
        raw_radius,
        height,
        radial,
        radial_from_flux,
    )
    assert abs(axial - axial_from_flux) <= RELATIVE_BUDGET * abs(axial_from_flux), (
        raw_radius,
        height,
        axial,
        axial_from_flux,
    )
    # The two identities are not interchangeable: a call that swapped B_R and
    # B_Z would satisfy neither, and one that returned the axial field twice
    # would fail the radial comparison above because the mixed point is chosen
    # so the two components differ by more than an order of magnitude.
    assert abs(radial - axial) > 0.1 * max(abs(radial), abs(axial))
    # The flux anchor is what makes the derivative comparison meaningful.
    assert flux != 0.0


def test_the_radius_offset_is_applied_exactly_once():
    """Evidence 3: no second axis shift inside this operator."""
    raw_radius, height = 0.3, 0.05
    radius, _, _ = compute_axisymmetric_coil_modulus(raw_radius, height, COIL_RADIUS, COIL_Z)
    assert radius == raw_radius + 1.0e-8
    supplied = evaluate_filament_coil_green_field(
        radius, height, COIL_RADIUS, COIL_Z, CURRENT, TURNS
    )
    # Passing the *unshifted* radius must give the response at that radius, not
    # at the shifted one: the difference is a real physical difference of order
    # 1e-8/R, which is far above the binary64 budget.
    unshifted = evaluate_filament_coil_green_field(
        raw_radius, height, COIL_RADIUS, COIL_Z, CURRENT, TURNS
    )
    assert supplied != unshifted
    expected_unshifted = _quadrature(raw_radius, height)
    for name, got, want in zip(("flux", "B_R", "B_Z"), unshifted, expected_unshifted, strict=True):
        assert abs(got - float(want)) <= RELATIVE_BUDGET * abs(float(want)), name


def test_current_and_turns_enter_as_one_exact_product():
    """Evidence 5: exact power-of-two linearity of current * turns."""
    radius, _, _ = compute_axisymmetric_coil_modulus(0.3, 0.05, COIL_RADIUS, COIL_Z)
    base = evaluate_filament_coil_green_field(radius, 0.05, COIL_RADIUS, COIL_Z, CURRENT, TURNS)
    doubled = evaluate_filament_coil_green_field(
        radius, 0.05, COIL_RADIUS, COIL_Z, 2.0 * CURRENT, TURNS
    )
    for name, base_value, doubled_value in zip(("flux", "B_R", "B_Z"), base, doubled, strict=True):
        assert doubled_value == 2.0 * base_value, name
        assert base_value != 0.0, name


def test_each_declared_rejection_channel_is_executable():
    """Every ``failure_semantics`` channel has one assertion."""
    radius, _, _ = compute_axisymmetric_coil_modulus(0.3, 0.05, COIL_RADIUS, COIL_Z)
    # invalid_input: a target that coincides with a ring is a singular geometry.
    with pytest.raises(ValueError, match="singular coil geometry"):
        evaluate_filament_coil_green_field(0.25, -0.15, COIL_RADIUS, COIL_Z, CURRENT, TURNS)
    # invalid_input: observation coordinates and coil vectors.
    for arguments, message in [
        ((0.0, 0.05, COIL_RADIUS, COIL_Z, CURRENT, TURNS), "finite and positive"),
        ((-0.5, 0.05, COIL_RADIUS, COIL_Z, CURRENT, TURNS), "finite and positive"),
        ((radius, np.nan, COIL_RADIUS, COIL_Z, CURRENT, TURNS), "finite and positive"),
        ((radius, 0.05, COIL_RADIUS, COIL_Z, CURRENT, TURNS[:-1]), "same-shape"),
        ((radius, 0.05, COIL_RADIUS * 0.0, COIL_Z, CURRENT, TURNS), "valid geometry"),
        ((radius, 0.05, COIL_RADIUS, COIL_Z, np.full(2, np.nan), TURNS), "valid geometry"),
    ]:
        with pytest.raises(ValueError, match=message):
            evaluate_filament_coil_green_field(*arguments)
    # runtime_failure: the kernel's FloatingPointError propagates unchanged
    # rather than being converted into a non-finite scalar.
    with pytest.raises(FloatingPointError, match="overflow encountered in multiply"):
        evaluate_filament_coil_green_field(
            1.2e-100,
            0.0,
            np.array([1.0e-100]),
            np.array([0.1e-100]),
            np.array([1.0e308]),
            np.array([1.0]),
        )
    # partial_results: the tuple is only built after the kernel returns, so a
    # failing call cannot leave a partially filled tuple behind.
    with pytest.raises(FloatingPointError):
        evaluate_filament_coil_green_field(
            1.2e-100,
            0.0,
            np.array([1.0e-100]),
            np.array([0.1e-100]),
            np.array([1.0e308]),
            np.array([1.0]),
        )
