"""Independent evidence for the aggregate circular-filament Green response.

Asset: ``scirel.electromagnetism.circular-filament-green`` (``compute_greens``).

The maintained tests pin the axis/derivative regressions and bounded
comparisons; the near-field oracle in ``tests/cross_domain`` recomputes the
*same* elliptic closed form with ``mpmath`` at 50 digits, which can be wrong in
the same way as the implementation.  The evidence here comes from
``_ideal_ring_reference``, whose flows are described there: flux by
Biot-Savart quadrature, flux by a complement-free AgM elliptic evaluation, and
the two field components by differentiating the *flux* instead of evaluating
the implementation's analytic derivative combination.

Six statements, each of which a wrong implementation cannot pass:

1. **Pointwise response against the reference.**  ``psi``, ``B_R`` and ``B_Z``
   on grids that cross ``m = 0.5`` (the implementation's branch cutover), the
   axis, and both sides of the wire radius.  A dropped ``mu0/4 pi``, a
   ``2 pi``/``4 pi`` confusion, a global sign, a swapped ``B_R``/``B_Z`` pair, a
   wrong branch inside ``m >= 0.5`` or the ``(2 - m) K - 2 E`` prefactor all
   fail here.
2. **Axis limit from a closed form with no elliptic integral.**  On the axis
   ``psi`` and ``B_R`` are exactly zero (an explicit ``R`` factor and an odd
   integrand) and
   ``B_Z = 1e-7 w 2 pi a^2 / (a^2 + (Z - z0)^2)^{3/2}``,
   the elementary on-axis field of a loop.  This is a second source for the
   axis that shares no intermediate with either branch of the implementation.
3. **Exact mirror symmetry.**  For a ring at ``z0 = 0`` and the target grid
   reflected ``Z -> -Z``, ``psi`` and ``B_Z`` must be *bitwise* equal and
   ``B_R`` bitwise negated, because only ``(Z - z0)^2`` and the signed
   ``Z - z0`` enter.  Asserted as equality, not as a tolerance, and paired with
   the magnitude anchors of statement 1 so an identically zero response cannot
   pass.
4. **Vacuum Maxwell constraints, with a measured convergence ratio.**  Away
   from the filament, ``div B = (1/R) d(R B_R)/dR + dB_Z/dZ`` and
   ``(curl B)_phi = dB_R/dZ - dB_Z/dR`` must both vanish.  Neither is a
   restatement of the closed form: they are consistency conditions between the
   three *returned* arrays.  The residual is measured on three halvings of the
   difference step and must fall at the ratio the second-order stencil
   predicts; the measured ratios are printed into the assertion message.
5. **Flux-field relation with a measured convergence ratio.**
   ``B_R = -(1/R) dpsi/dZ`` and ``B_Z = (1/R) dpsi/dR`` between the returned
   arrays, again measured over three step halvings.
6. **Exact superposition and the declared skip rules.**  Power-of-two weight
   scaling is exact, an exactly opposed pair cancels to exactly zero, a list of
   source sets equals the per-set calls, zero-radius and zero-weight rows are
   skipped exactly, and a positive subnormal weight still contributes.

Budgets, fixed in ``_ideal_ring_reference`` before this comparison was run:
``PSI_BUDGET = 64 eps = 1.42e-14`` and ``FIELD_BUDGET = 128 eps = 2.84e-14``
relative, derived there from the operation count and the cancellation each
branch carries; the reference itself contributes at most ``1e-22`` relative.
The observed maxima are printed by the assertions; these are observed maxima on
sampled grids, not continuous error bounds.

Deliberate limits, also recorded in the contract: targets inside ``1e-2 a`` of
the wire are excluded (the ideal-filament response diverges there and the
fixed-breakpoint reference cannot certify them), relative statements about
``psi`` and ``B_R`` stop below ``1e-8 a``, and the convergence statements are
measured on the named grids only.
"""

from __future__ import annotations

from fractions import Fraction

import numpy as np
import pytest

import _ideal_ring_reference as reference
from scirel.electromagnetism import compute_greens

PSI_BUDGET = reference.PSI_BUDGET
FIELD_BUDGET = reference.FIELD_BUDGET
FIELDS = ("psi", "BR", "BZ")

# Target points as fractions of the ring radius: (R/a, (Z - z0)/a).  The grid
# crosses the branch cutover m = 0.5 at R/a = 3 - 2 sqrt(2) = 0.1716 and
# R/a = 3 + 2 sqrt(2) = 5.828, the axis, both sides of the wire radius, and
# three regimes in (Z - z0).
TARGET_FRACTIONS = (
    (1.0e-5, 0.0),
    (1.0e-4, -1.0e-2),
    (5.0e-2, 3.0e-2),
    (0.171, 0.0),
    (0.172, 0.0),
    (0.3, -4.5e-2),
    (0.5, 0.0),
    (0.7, 0.3),
    (0.98, 0.0),
    (1.02, 0.0),
    (2.0, -0.6),
    (5.8, 0.0),
    (5.9, 0.0),
)
RINGS = ((0.35, 0.0), (1.0, 0.3), (0.62, -0.15))


def _targets(ring_radius, ring_z, fractions=TARGET_FRACTIONS):
    """Return the target table of one ring in metres."""
    return np.array(
        [[ring_radius * radius, ring_z + ring_radius * height] for radius, height in fractions]
    )


@pytest.mark.parametrize(("ring_radius", "ring_z"), RINGS)
def test_response_matches_the_independent_reference(ring_radius, ring_z):
    """Evidence 1: pointwise psi, BR and BZ against the second source."""
    targets = _targets(ring_radius, ring_z)
    psi, br, bz = compute_greens(np.array([[ring_radius, ring_z, 1.0]]), targets)
    observed = dict.fromkeys(FIELDS, 0.0)
    for index, (radius, height) in enumerate(targets):
        expected = reference.response(float(radius), float(height), ring_radius, ring_z, 1.0)
        for name, got, want in zip(FIELDS, (psi, br, bz), expected, strict=True):
            want_value = float(want)
            got_value = float(got[index])
            if want_value == 0.0:
                # The reference forms this value from an odd integrand, so an
                # exact zero is the statement, not a tolerance.
                assert got_value == 0.0, (name, radius, height, got_value)
                continue
            deviation = abs(got_value - want_value) / abs(want_value)
            assert deviation <= (PSI_BUDGET if name == "psi" else FIELD_BUDGET), (
                f"{name} at R={radius!r} Z={height!r} deviates by {deviation:.3e} "
                f"({got_value!r} against {want_value!r})"
            )
            observed[name] = max(observed[name], deviation)
    # The comparison is not vacuous, and the branch cutover is exercised.
    assert all(value > 0.0 for value in observed.values()), observed
    assert any(0.0 < radius < 0.1716 or radius > 5.828 for radius, _ in targets)


@pytest.mark.parametrize("height_offset", [0.0, 0.3, -1.7])
def test_axis_limit_matches_the_elementary_loop_field(height_offset):
    """Evidence 2: the on-axis field against a source with no elliptic integral."""
    ring_radius = 0.8
    ring_z = 0.45
    psi, br, bz = compute_greens(
        np.array([[ring_radius, ring_z, -2.5]]), np.array([[0.0, ring_z + height_offset]])
    )
    # psi carries an explicit R factor and B_R an odd integrand: both are exactly
    # zero on the axis, in the implementation and in the definition alike.
    assert float(psi[0]) == 0.0
    assert float(br[0]) == 0.0
    expected = (
        -2.5 * 1e-7 * 2.0 * np.pi * ring_radius**2 / (ring_radius**2 + height_offset**2) ** 1.5
    )
    deviation = abs(float(bz[0]) - expected) / abs(expected)
    assert deviation <= FIELD_BUDGET, (float(bz[0]), expected, deviation)
    # The axis value must not be confused with the radial component, and must
    # not be the zero the other two components carry.
    assert abs(expected) > 0.0


def test_mirror_symmetry_is_exact():
    """Evidence 3: exact reflection about the ring plane at a zero ring height."""
    ring_radius, ring_z = 0.7, 0.0
    heights = np.array([0.15, 0.4, 1.1, 2.3])
    radii = np.array([0.2, 0.55, 0.95, 2.4])
    up = np.column_stack((radii, heights))
    down = np.column_stack((radii, -heights))
    psi_up, br_up, bz_up = compute_greens(np.array([[ring_radius, ring_z, 1.0]]), up)
    psi_down, br_down, bz_down = compute_greens(np.array([[ring_radius, ring_z, 1.0]]), down)
    # Only (Z - z0)^2 and the signed (Z - z0) enter, so the reflection is exact
    # in binary64 and the assertion is equality, not a tolerance.
    np.testing.assert_array_equal(psi_up, psi_down)
    np.testing.assert_array_equal(bz_up, bz_down)
    np.testing.assert_array_equal(br_up, -br_down)
    # Nondegeneracy: the anchors are not all zero, so the symmetry is not the
    # symmetry of a zero response.
    assert np.all(np.abs(psi_up) > 0.0)
    assert np.all(np.abs(br_up) > 0.0)


def _second_order_derivative(values, step, axis_length):
    """Return a second-order central difference of a sampled array."""
    return (np.roll(values, -1) - np.roll(values, 1)) / (2 * step)


def _divergence_and_curl(radius, height, ring_radius, ring_z, step):
    """Return ``(div B, curl_phi B)`` of the returned arrays at one target."""
    offsets = np.array([-2.0, -1.0, 0.0, 1.0, 2.0])
    radial = np.column_stack((radius + offsets * step, np.full(offsets.size, height)))
    axial = np.column_stack((np.full(offsets.size, radius), height + offsets * step))
    psi_r, br_r, bz_r = compute_greens(np.array([[ring_radius, ring_z, 1.0]]), radial)
    psi_z, br_z, bz_z = compute_greens(np.array([[ring_radius, ring_z, 1.0]]), axial)
    field_scale = max(np.max(np.abs(br_r)), np.max(np.abs(bz_r)), np.max(np.abs(bz_z)))
    divergence = ((radius + step) * float(br_r[3]) - (radius - step) * float(br_r[1])) / (
        2 * step
    ) / radius + (float(bz_z[3]) - float(bz_z[1])) / (2 * step)
    curl = (float(br_z[3]) - float(br_z[1])) / (2 * step) - (float(bz_r[3]) - float(bz_r[1])) / (
        2 * step
    )
    return abs(divergence), abs(curl), field_scale


def test_vacuum_divergence_and_curl_converge_at_second_order():
    """Evidence 4: div B = 0 and curl B = 0 with a measured refinement ratio."""
    radius, height, ring_radius, ring_z = 0.83, 0.21, 0.4, -0.25
    steps = [4.0e-3, 2.0e-3, 1.0e-3, 5.0e-4]
    samples = [_divergence_and_curl(radius, height, ring_radius, ring_z, step) for step in steps]
    for name, index in (("div B", 0), ("curl_phi B", 1)):
        # A second-order stencil on a smooth field falls by four per halving,
        # until the binary64 floor of the values involved is reached; the last
        # sampled step is the one closest to that floor.
        residuals = [sample[index] for sample in samples]
        ratios = [residuals[k] / residuals[k + 1] for k in range(len(steps) - 2)]
        assert all(ratio > 3.0 for ratio in ratios), (name, ratios, residuals)
        # The residual is not trivially zero at every step: it is a decreasing
        # sequence produced by actual truncation.
        assert residuals[0] > residuals[-1] >= 0.0
        # The residual is small against the field magnitude, not merely
        # decreasing: a stencil applied to the wrong component would converge
        # to a nonzero constant instead.
        scale = samples[-1][2]
        assert residuals[-1] <= 1e-3 * scale / max(abs(radius), 1e-12), (
            name,
            residuals[-1],
            scale,
        )


def test_flux_field_relation_converges_at_second_order():
    """Evidence 5: B_R = -(1/R) dpsi/dZ and B_Z = (1/R) dpsi/dR, measured."""
    radius, height, ring_radius, ring_z = 1.25, -0.4, 0.5, 0.05
    steps = [2.0e-3, 1.0e-3, 5.0e-4, 2.5e-4]
    axial_errors, radial_errors = [], []
    for step in steps:
        plus = np.array([[radius, height + step]])
        minus = np.array([[radius, height - step]])
        psi_plus, _, _ = compute_greens(np.array([[ring_radius, ring_z, 1.0]]), plus)
        psi_minus, _, _ = compute_greens(np.array([[ring_radius, ring_z, 1.0]]), minus)
        dpsi_dz = (float(psi_plus[0]) - float(psi_minus[0])) / (2 * step)
        inside = np.array([[radius + step, height]])
        outside = np.array([[radius - step, height]])
        psi_inside, br_inside, _ = compute_greens(np.array([[ring_radius, ring_z, 1.0]]), inside)
        psi_outside, _, _ = compute_greens(np.array([[ring_radius, ring_z, 1.0]]), outside)
        dpsi_dr = (float(psi_inside[0]) - float(psi_outside[0])) / (2 * step)
        _, br_centre, bz_centre = compute_greens(
            np.array([[ring_radius, ring_z, 1.0]]), np.array([[radius, height]])
        )
        axial_errors.append(abs(float(br_centre[0]) + dpsi_dz / radius))
        radial_errors.append(abs(float(bz_centre[0]) - dpsi_dr / radius))
    for name, errors in (("dpsi/dZ", axial_errors), ("dpsi/dR", radial_errors)):
        ratios = [errors[k] / errors[k + 1] for k in range(len(steps) - 2)]
        assert all(ratio > 3.0 for ratio in ratios), (name, ratios, errors)
        assert errors[0] > errors[-1] >= 0.0


def test_superposition_scaling_and_cancellation_are_exact():
    """Evidence 6: exact weight laws and the declared skip rules."""
    ring = [0.9, 0.2]
    targets = np.array([[0.35, -0.4], [0.6, 0.15], [1.4, 0.55]])
    base = compute_greens(np.array([[ring[0], ring[1], 1.0]]), targets)
    for power in (3, 10, -7):
        scaled = compute_greens(np.array([[ring[0], ring[1], float(2**power)]]), targets)
        for name, unscaled_values, scaled_values in zip(FIELDS, base, scaled, strict=True):
            # Multiplying by a power of two is exact in binary64, so the scaled
            # response must be bitwise equal to the doubled value.
            np.testing.assert_array_equal(
                scaled_values, np.ldexp(unscaled_values, power), err_msg=name
            )
    opposed = compute_greens(np.array([[ring[0], ring[1], 1.0], [ring[0], ring[1], -1.0]]), targets)
    for name, values in zip(FIELDS, opposed, strict=True):
        np.testing.assert_array_equal(values, 0.0, err_msg=name)
    # Inactive rows contribute exactly nothing.
    inactive = compute_greens(np.array([[0.0, 3.0, 1.0], [ring[0], ring[1], 0.0]]), targets)
    for name, values in zip(FIELDS, inactive, strict=True):
        np.testing.assert_array_equal(values, 0.0, err_msg=name)
    # A list of source sets is the ordered stack of the per-set calls: the list
    # argument is the documented second dimension, and its entries must be
    # bitwise equal to the independent single-set calls.
    second = [0.45, -0.8]
    sets = [np.array([[ring[0], ring[1], 1.0]]), np.array([[second[0], second[1], 1.0]])]
    stacked = compute_greens(sets, targets)
    singles = [compute_greens(source_set, targets) for source_set in sets]
    for index, (name, values) in enumerate(zip(FIELDS, stacked, strict=True)):
        assert values.shape == (2, len(targets)), (name, values.shape)
        for set_index in range(2):
            np.testing.assert_array_equal(values[set_index], singles[set_index][index])
    # Fraction arithmetic over the returned values: two independent single-ring
    # calls reproduce the one combined table within one rounding of the sum.
    combined = compute_greens(
        np.array([[ring[0], ring[1], 1.0], [second[0], second[1], 1.0]]), targets
    )
    for index, (name, values) in enumerate(zip(FIELDS, combined, strict=True)):
        for target_index in range(len(targets)):
            total = Fraction(float(singles[0][index][target_index])) + Fraction(
                float(singles[1][index][target_index])
            )
            difference = abs(Fraction(float(values[target_index])) - total)
            scale = abs(total) if total != 0 else Fraction(1)
            assert difference <= scale * Fraction(2, 2**52), (name, target_index, float(difference))
    # A subnormal weight still contributes where the product is representable:
    # 5e-324 times a response of order 1e3 lands inside the subnormal range
    # instead of underflowing to an indistinguishable zero.
    near_wire_target = np.array([[0.9, 0.2000001]])
    near_wire = compute_greens(np.array([[ring[0], ring[1], 1.0]]), near_wire_target)
    subnormal = compute_greens(np.array([[ring[0], ring[1], 5e-324]]), near_wire_target)
    assert abs(float(near_wire[1][0])) > 1.0
    assert float(subnormal[1][0]) != 0.0
    assert 0.0 < abs(float(subnormal[1][0])) < np.finfo(float).tiny


def test_failure_channels_are_executable():
    """Evidence 5 of the failure matrix: one assertion per rejection channel."""
    targets = np.array([[0.4, 0.1]])
    # Coincident active target: the discrete contract rejects the exact self
    # field instead of inventing a finite-wire value.
    with pytest.raises(ValueError, match="coincident with singular circular filament"):
        compute_greens(np.array([[0.4, 0.1, 1.0]]), targets)
    # Malformed source width.
    with pytest.raises(ValueError, match=r"rzw must have shape \(N, 3\)"):
        compute_greens(np.array([[0.4, 0.1]]), targets)
    # Malformed target width.
    with pytest.raises(ValueError, match=r"rz_pts must have shape \(N, 2\)"):
        compute_greens(np.array([[0.4, 0.1, 1.0]]), np.array([[0.4, 0.1, 2.0]]))
    # Complex input.
    with pytest.raises(ValueError, match="must contain real values"):
        compute_greens(np.array([[0.4 + 1j, 0.1, 1.0]]), targets)
    # Nonfinite input.
    with pytest.raises(ValueError, match="must be finite"):
        compute_greens(np.array([[0.4, np.nan, 1.0]]), targets)
    # Negative source radius.
    with pytest.raises(ValueError, match="non-negative cylindrical radius"):
        compute_greens(np.array([[-0.4, 0.1, 1.0]]), targets)
    # Negative target radius.
    with pytest.raises(ValueError, match="non-negative cylindrical radius"):
        compute_greens(np.array([[0.4, 0.1, 1.0]]), np.array([[-0.4, 0.1]]))
    # Unrepresentable finite response: a representable geometry with a weight
    # that overflows the product.
    # A representable geometry whose product with the weight is not
    # representable: the kernel reports it instead of returning ``inf``.
    with pytest.raises(FloatingPointError, match="not representable"):
        compute_greens(np.array([[0.4, 0.1, 1e308]]), np.array([[0.4, 0.1 + 1e-9]]))
