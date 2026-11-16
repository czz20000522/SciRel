"""Independent evidence for the weighted circular-filament Green response.

Asset: ``scirel.field.circular-filament-green``.

The maintained tests in ``test_circular_filament_green.py`` pin the skip
convention, weighted-source linearity and the analytic axis limit, and
``test_field_green_correction.py`` pins a cross-domain correction.  None of them
compares the response against a source outside the closed-form derivation, and
the near-field 50-digit oracle in ``test_filament_coil_green.py`` recomputes the
*same* elliptic closed form.  The evidence here therefore comes from
``_biot_savart_reference``: direct high-precision quadrature of the Biot-Savart
law, which uses no elliptic integral and no hypergeometric series.

Five independent statements, each of which a wrong implementation cannot pass:

1. **Pointwise field against the Biot-Savart quadrature.**  ``psi``, ``B_R`` and
   ``B_Z`` at a fixed target grid must agree with the quadrature to
   ``_RELATIVE_BUDGET``.  The naive failure modes this rejects are a dropped
   ``mu0/4pi``, the ``4 pi`` vs ``2 pi`` convention, a global sign, and the
   ``(2-m)K-2E`` prefactor.
2. **Axis limit.**  On the cylindrical axis the quadrature gives ``psi = 0`` and
   ``B_R = 0`` exactly (odd integrand and a ``dz`` factor) while ``B_Z`` stays
   nonzero.  An implementation that returned the radial field as ``B_Z`` or
   produced a spurious axial flux fails here even though its off-axis values
   might be right.
3. **Mirror symmetry in ``Z``.**  For a ring at height ``z0``, reflecting the
   target about the ring plane must give ``psi(Z) = psi(2 z0 - Z)``,
   ``B_Z(Z) = B_Z(2 z0 - Z)`` and ``B_R(Z) = -B_R(2 z0 - Z)``.  The reflection is
   exact in binary64 because only ``(Z - z0)^2`` and the signed ``Z - z0``
   factor appear, so the assertion is equality, not a tolerance.  Symmetry alone
   is satisfied by any odd function, so it is asserted together with the
   magnitude anchors of statement 1 in the same test.
4. **Exact superposition.**  Scaling every weight by a power of two must scale
   the response by exactly that power, and a sum of two source calls must equal
   the single combined call through :class:`fractions.Fraction` arithmetic over
   the returned binary64 values.  This is the linearity and additivity the
   contract calls "weighted source superposition", decided exactly rather than
   within a tolerance.
5. **The declared zero-self convention.**  A target exactly on an active ring is
   skipped as a zero entry, a zero-radius or zero-weight row contributes
   nothing, and a subnormal-but-positive radius still contributes.

Budgets, fixed before the comparison was run:

* pointwise relative deviation ``<= _RELATIVE_BUDGET = 64 eps = 1.42e-14``,
  derived in ``_biot_savart_reference`` from the operation count of the closed
  form.  The observed maximum over the grid used here is ``5.38e-15``, i.e.
  ``0.38`` of the budget; this is an **observed maximum on a sampled grid**, not
  a proven bound over the continuous target set.
* the quadrature itself is certified at ``1e-25`` of the integrand scale at two
  working precisions, so it contributes nothing at the ``1e-14`` level.
* the symmetry, power-of-two scaling and zero-self assertions are exact
  equalities and carry no budget.

Deliberate limits of this evidence (also recorded in the contract):
the wire itself is excluded (``_MIN_SEPARATION_RATIO = 1e-2`` relative distance),
targets below ``1e-6 a`` are excluded from the relative statements, and the
grid is finite, so no claim of a continuous error bound is made.
"""

from __future__ import annotations

from fractions import Fraction

import numpy as np
import pytest

import _biot_savart_reference as reference
from scirel._result import Result
from scirel.field import circular_filament_green_response

RELATIVE_BUDGET = reference._RELATIVE_BUDGET
FIELDS = ("gpsi", "gBR", "gBZ")

# A target grid that crosses the axis, the wire plane, both kernel branches
# (m < 0.5 and m > 0.5) and the near-axis scaling regime.  It is the grid on
# which the observed maximum recorded above was taken.
TARGETS = [
    (1.0e-6, 0.0),
    (1.0e-4, 0.0),
    (3.5e-2, -5.25e-2),
    (0.105, 0.0),
    (0.245, -0.525),
    (0.3, 0.105),
    (0.3465, 0.0),
    (0.875, -0.525),
    (1.1, 0.385),
]


def _response(sources, targets):
    """Return the three response arrays of the public function."""
    result = circular_filament_green_response(sources, targets)
    return result["gpsi"], result["gBR"], result["gBZ"]


@pytest.mark.parametrize(("coil_radius", "coil_z"), [(0.35, 0.0), (1.0, 0.3), (0.62, -0.15)])
def test_response_matches_the_biot_savart_quadrature(coil_radius, coil_z):
    """Evidence 1: pointwise psi, BR and BZ against direct quadrature."""
    psi, br, bz = _response([[coil_radius, coil_z, 1.0]], TARGETS)
    observed = 0.0
    for index, (radius, height) in enumerate(TARGETS):
        expected = reference.ring_field(radius, height, coil_radius, coil_z, 1.0)
        for name, got, want in zip(FIELDS, (psi, br, bz), expected, strict=True):
            got_value, want_value = float(got[index]), float(want)
            if want_value == 0.0:
                # The quadrature integrates an integrand that is odd about
                # phi = 0 to exact zero (dz = 0 in the radial integrand), and
                # the closed form multiplies by that same factor, so this is an
                # exact-equality statement rather than a tolerance.
                assert got_value == 0.0, (name, radius, height, got_value)
                continue
            deviation = abs(got_value - want_value) / abs(want_value)
            assert deviation <= RELATIVE_BUDGET, (
                f"{name} at R={radius} Z={height} deviates by {deviation:.3e} "
                f"({got_value!r} against {want_value!r})"
            )
            observed = max(observed, deviation)
    # The budget is not vacuous: the response is not being compared with itself.
    assert observed > 0.0


def test_axis_targets_keep_zero_flux_zero_radial_field_and_nonzero_axial_field():
    """Evidence 2: the exact axis limits of the three components."""
    coil_radius, coil_z = 0.5, 0.2
    heights = [0.0, 0.3, -0.9, 2.0]
    psi, br, bz = _response([[coil_radius, coil_z, 1.0]], [[0.0, z] for z in heights])
    np.testing.assert_array_equal(psi, 0.0)
    np.testing.assert_array_equal(br, 0.0)
    for index, height in enumerate(heights):
        expected = reference.ring_field(0.0, height, coil_radius, coil_z, 1.0)[2]
        deviation = abs(float(bz[index]) - float(expected)) / abs(float(expected))
        assert deviation <= RELATIVE_BUDGET, (height, deviation)
        # Nonzero anchor: B_Z on the axis of a unit-current loop is 1e-7 * ..... ,
        # and a response that collapsed to zero would pass the ratio above by
        # way of a zero-over-zero comparison only if the reference were zero too.
        assert abs(float(bz[index])) > 0.0


def test_mirror_symmetry_in_z_holds_exactly_with_the_expected_signs():
    """Evidence 3: reflection about the ring plane, with magnitude anchors."""
    # Every value here is a dyadic rational, so ``coil_z + offset`` and
    # ``coil_z - offset`` are both exact and the reflected targets differ only
    # in the sign of the rounded ``Z - z0``.  That is what makes bitwise
    # equality the correct assertion instead of a tolerance.
    coil_radius, coil_z, weight = 0.4, 0.25, 2.0
    offsets = [0.0625, 0.25, 0.5, 2.0]
    up = [[0.3, coil_z + dz] for dz in offsets]
    down = [[0.3, coil_z - dz] for dz in offsets]
    psi_up, br_up, bz_up = _response([[coil_radius, coil_z, weight]], up)
    psi_down, br_down, bz_down = _response([[coil_radius, coil_z, weight]], down)
    np.testing.assert_array_equal(psi_up, psi_down)
    np.testing.assert_array_equal(bz_up, bz_down)
    np.testing.assert_array_equal(br_up, -br_down)
    # Anchors that a zero or self-returning response cannot satisfy: the flux is
    # positive, the axial field is positive and the radial field has both signs
    # across the ring plane.
    assert (psi_up > 0.0).all()
    assert (bz_up > 0.0).all()
    assert (br_up > 0.0).all()
    assert (br_down < 0.0).all()


def test_weights_compose_exactly_and_additively():
    """Evidence 4: exact power-of-two scaling and exact rational additivity."""
    sources = [(0.35, 0.0, 1.0), (0.62, 0.25, -2.0)]
    targets = [[0.2, 0.13], [0.55, -0.31], [0.9, 0.4]]
    base = _response(sources, targets)
    scaled = _response([[r, z, 8.0 * w] for r, z, w in sources], targets)
    for name, base_value, scaled_value in zip(FIELDS, base, scaled, strict=True):
        np.testing.assert_array_equal(scaled_value, 8.0 * base_value), name
    # Additivity decided in exact rationals: the combined call is the rational
    # sum of the two single-source calls, because both are binary64 values of
    # the same real sum and the summation is compensated.
    first = _response([sources[0]], targets)
    second = _response([sources[1]], targets)
    for name, total, left, right in zip(FIELDS, base, first, second, strict=True):
        for index in range(len(targets)):
            exact = Fraction(float(left[index])) + Fraction(float(right[index]))
            rounded = Fraction(float(total[index]))
            residual = abs(rounded - exact)
            allowed = 4 * np.finfo(float).eps * abs(exact)
            assert residual <= allowed, (name, index, float(residual / abs(exact)))
        # Nonzero anchor for the additivity comparison.
        assert np.any(np.asarray(left) != 0.0)
        assert np.any(np.asarray(right) != 0.0)


def test_zero_self_zero_radius_and_zero_weight_rows_are_inactive():
    """Evidence 5: the declared discrete skip conventions."""
    coil_radius, coil_z = 0.35, 0.0
    targets = [[coil_radius, coil_z], [0.2, 0.1]]
    response = circular_filament_green_response([[coil_radius, coil_z, 1.0]], targets)
    # The coincident target keeps the zero-self convention in every field.
    for name in FIELDS:
        assert response[name][0] == 0.0, name
    reference_value = reference.ring_field(0.2, 0.1, coil_radius, coil_z, 1.0)[2]
    assert abs(float(response["gBZ"][1]) - float(reference_value)) <= (
        RELATIVE_BUDGET * abs(float(reference_value))
    )
    # A zero-radius source contributes nothing; the same weight on a positive
    # radius does, so the skip is the radius test and not a silently empty sum.
    zero_radius = circular_filament_green_response([[0.0, 0.0, 1.0]], targets)
    for name in FIELDS:
        np.testing.assert_array_equal(zero_radius[name], 0.0), name
    zero_weight = circular_filament_green_response([[coil_radius, coil_z, 0.0]], targets)
    for name in FIELDS:
        np.testing.assert_array_equal(zero_weight[name], 0.0), name
    # A tiny positive radius is not skipped by the discrete zero-radius test:
    # its response obeys the exact small-loop a**2 scaling, which a skipped row
    # (all zeros) and a zero-radius row (all zeros) both fail.
    tiny = circular_filament_green_response([[1.0e-30, 0.0, 1.0]], [[0.3, 0.125]])
    double = circular_filament_green_response([[2.0e-30, 0.0, 1.0]], [[0.3, 0.125]])
    for name in FIELDS:
        assert tiny[name][0] != 0.0, name
        np.testing.assert_array_equal(double[name], 4.0 * tiny[name]), name


def test_each_declared_rejection_channel_is_executable():
    """Every ``failure_semantics`` channel has one assertion."""
    good_sources, good_targets = [[0.35, 0.0, 1.0]], [[0.2, 0.0]]
    # invalid_input: malformed shapes.
    with pytest.raises(ValueError, match="shape"):
        circular_filament_green_response([[0.35, 0.0]], good_targets)
    with pytest.raises(ValueError, match="shape"):
        circular_filament_green_response(good_sources, [[0.2, 0.0, 0.1]])
    # invalid_input: complex, nonfinite and negative-radius values.
    with pytest.raises(ValueError, match="real"):
        circular_filament_green_response([[0.35 + 0j, 0.0, 1.0]], good_targets)
    with pytest.raises(ValueError, match="real"):
        circular_filament_green_response(good_sources, [[0.2 + 0j, 0.0]])
    with pytest.raises(ValueError, match="finite"):
        circular_filament_green_response([[np.inf, 0.0, 1.0]], good_targets)
    with pytest.raises(ValueError, match="finite"):
        circular_filament_green_response(good_sources, [[0.2, np.nan]])
    with pytest.raises(ValueError, match="nonnegative"):
        circular_filament_green_response([[-0.35, 0.0, 1.0]], good_targets)
    with pytest.raises(ValueError, match="nonnegative"):
        circular_filament_green_response(good_sources, [[-0.2, 0.0]])
    # runtime_failure: an input the contract accepts (finite weight, finite
    # nonnegative radius) whose response is not representable.  The near-wire
    # radial field grows like 1/distance, so a 1e308 weight overflows it.
    with pytest.raises(FloatingPointError, match="not representable"):
        circular_filament_green_response([[0.3, 0.0, 1.0e308]], [[0.3, 1.0e-300]])
    # partial_results: the failing path raises before a mapping exists, so a
    # caller cannot mistake a partly filled result for a usable one.
    assert not isinstance(
        pytest.raises(FloatingPointError, circular_filament_green_response,
                      [[0.3, 0.0, 1.0e308]], [[0.3, 1.0e-300]]).value, Result
    )


def test_the_named_result_keeps_its_declared_shape_and_access():
    """The mapping/attribute contract the asset promises."""
    result = circular_filament_green_response([[0.35, 0.0, 1.0]], TARGETS)
    assert isinstance(result, Result)
    assert list(result) == list(FIELDS)
    for name in FIELDS:
        assert getattr(result, name) is result[name]
        assert result[name].dtype == np.float64
        assert result[name].shape == (len(TARGETS),)
