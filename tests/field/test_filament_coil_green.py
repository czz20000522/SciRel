"""Direct contract tests for the ``field`` circular-coil Green operators.

``compute_axisymmetric_coil_modulus`` builds the observation geometry and
``evaluate_complete_elliptic_integrals`` remains a standalone polynomial-log
approximation.  ``evaluate_filament_coil_green_field`` no longer consumes those
elliptic values: it evaluates each ring through the canonical circular-filament
kernel, which switches to a small-modulus hypergeometric branch below ``m=0.5``
and therefore stays accurate near the cylindrical axis, where the
``(2-m)K-2E`` combination cancels (issue #10 item 4).

Oracles here are independent: a 50-digit mpmath recomputation of the closed
forms, cross-asset agreement with the other ``field`` Green asset, and explicit
failure contracts.
"""

from __future__ import annotations

import mpmath as mp
import numpy as np
import pytest

from scirel.field import (
    circular_filament_green_response,
    compute_axisymmetric_coil_modulus,
    evaluate_complete_elliptic_integrals,
    evaluate_filament_coil_green_field,
)

_MU0_OVER_2PI = 2.0e-7
_AXIS_OFFSET_M = 1.0e-8
_MP_DPS = 50


def _example_coils():
    rng = np.random.default_rng(69)
    ncoil = 4
    coil_radius = rng.uniform(0.1, 0.6, ncoil)
    coil_z = rng.uniform(-0.5, 0.5, ncoil)
    current = rng.uniform(5.0, 20.0, ncoil)
    turns = rng.uniform(1.0, 8.0, ncoil)
    return coil_radius, coil_z, current, turns


def _gseq_geometry(r0, z0, coil_radius, coil_z):
    radius = r0 + _AXIS_OFFSET_M
    denominator = (radius + coil_radius) ** 2 + (z0 - coil_z) ** 2
    return radius, 4.0 * radius * coil_radius / denominator, np.sqrt(denominator)


def _polynomial_log_k_e(m):
    p = 1.0 - m
    a_k = (
        ((0.01451196212 * p + 0.03742563713) * p + 0.03590092383) * p + 0.09666344259
    ) * p + 1.38629436112
    b_k = (((0.00441787012 * p + 0.03328355346) * p + 0.06880248576) * p + 0.12498593597) * p + 0.5
    a_e = (((0.01736506451 * p + 0.04757383546) * p + 0.0626060122) * p + 0.44325141463) * p + 1.0
    b_e = (((0.00526449639 * p + 0.04069697526) * p + 0.09200180037) * p + 0.2499836831) * p
    return a_k - b_k * np.log(p), a_e - b_e * np.log(p)


def _mp_closed_form(radius, z0, coil_radius, coil_z, current, turns):
    """50-digit independent recomputation of the summed filament-coil response."""
    mp.mp.dps = _MP_DPS
    radius_mp = mp.mpf(str(radius))
    z0_mp = mp.mpf(str(z0))
    flux = mp.mpf(0)
    br = mp.mpf(0)
    bz = mp.mpf(0)
    for rc, zc, cur, turn in zip(coil_radius, coil_z, current, turns):
        rc_mp, zc_mp = mp.mpf(str(rc)), mp.mpf(str(zc))
        factor = mp.mpf(str(_MU0_OVER_2PI)) * mp.mpf(str(turn)) * mp.mpf(str(cur))
        dz = z0_mp - zc_mp
        distance = mp.sqrt((radius_mp + rc_mp) ** 2 + dz**2)
        modulus = 4 * radius_mp * rc_mp / distance**2
        k_value = mp.ellipk(modulus)
        e_value = mp.ellipe(modulus)
        separation2 = (radius_mp - rc_mp) ** 2 + dz**2
        flux += (
            factor
            / mp.sqrt(modulus)
            * mp.sqrt(radius_mp * rc_mp)
            * ((2 - modulus) * k_value - 2 * e_value)
        )
        br += (
            factor
            * dz
            / radius_mp
            / distance
            * ((radius_mp**2 + rc_mp**2 + dz**2) / separation2 * e_value - k_value)
        )
        bz += (
            factor
            / distance
            * ((rc_mp**2 - radius_mp**2 - dz**2) / separation2 * e_value + k_value)
        )
    return float(flux), float(br), float(bz)


def test_geometry_returns_source_regularized_radius_modulus_and_distance():
    coil_radius, coil_z, _, _ = _example_coils()
    radius, modulus, distance = compute_axisymmetric_coil_modulus(0.3, 0.1, coil_radius, coil_z)
    assert radius == 0.3 + _AXIS_OFFSET_M
    expected_denom = (radius + coil_radius) ** 2 + (0.1 - coil_z) ** 2
    np.testing.assert_allclose(
        modulus, 4.0 * radius * coil_radius / expected_denom, rtol=1e-15, atol=0.0
    )
    np.testing.assert_allclose(distance, np.sqrt(expected_denom), rtol=1e-15, atol=0.0)
    assert np.all((modulus > 0.0) & (modulus <= 1.0))
    # the axis point is admissible: the source offset makes r0 positive
    radius_axis, _, _ = compute_axisymmetric_coil_modulus(0.0, 0.0, coil_radius, coil_z)
    assert radius_axis == _AXIS_OFFSET_M


def test_geometry_rejects_invalid_inputs():
    with pytest.raises(ValueError, match="finite after source axis offset"):
        compute_axisymmetric_coil_modulus(-0.1, 0.0, np.array([0.2]), np.array([0.0]))
    with pytest.raises(ValueError, match="finite"):
        compute_axisymmetric_coil_modulus(np.nan, 0.0, np.array([0.2]), np.array([0.0]))
    with pytest.raises(ValueError, match="positive radii"):
        compute_axisymmetric_coil_modulus(0.1, 0.0, np.array([0.0]), np.array([0.0]))
    with pytest.raises(ValueError, match="same-shape"):
        compute_axisymmetric_coil_modulus(0.1, 0.0, np.array([0.2, 0.3]), np.array([0.0]))


def test_negative_raw_radius_within_offset_width_is_rejected():
    # 负的原始半径（即使在 +1e-8 偏移宽度内）被显式拒绝，不会被偏移"救活"。
    # 偏移后仍为负时走"偏移后非有限/非正"分支，否则走"原始半径非负"分支。
    with pytest.raises(ValueError, match="nonnegative"):
        compute_axisymmetric_coil_modulus(-1.0e-9, 0.0, np.array([0.2]), np.array([0.0]))
    with pytest.raises(ValueError, match="finite after source axis offset"):
        compute_axisymmetric_coil_modulus(-_AXIS_OFFSET_M, 0.0, np.array([0.2]), np.array([0.0]))


def test_geometry_rejects_underflowed_modulus_before_green_response():
    with pytest.raises(ValueError, match="underflowed"):
        compute_axisymmetric_coil_modulus(1.0e150, 0.0, np.array([1.0e-300]), np.array([0.0]))


def test_elliptic_approximation_matches_the_source_polynomial_log_form():
    modulus = np.array([0.0, 0.25, 0.5, 0.75, 0.9, 0.999])
    k, e = evaluate_complete_elliptic_integrals(modulus)
    k_expected, e_expected = _polynomial_log_k_e(modulus)
    np.testing.assert_allclose(k, k_expected, rtol=1e-15, atol=0.0)
    np.testing.assert_allclose(e, e_expected, rtol=1e-15, atol=0.0)


def test_elliptic_approximation_mathematical_endpoint_in_whole_and_mixed_arrays():
    k, e = evaluate_complete_elliptic_integrals(np.array([1.0, 1.0]))
    assert np.all(np.isinf(k)) and np.all(e == 1.0)
    k_mixed, e_mixed = evaluate_complete_elliptic_integrals(np.array([0.5, 1.0]))
    assert np.isfinite(k_mixed[0]) and np.isinf(k_mixed[1]) and e_mixed[1] == 1.0
    for bad in (np.array([-0.1, 0.5]), np.array([1.1]), np.array([np.nan])):
        with pytest.raises(ValueError, match="modulus_squared"):
            evaluate_complete_elliptic_integrals(bad)


def test_green_response_matches_a_50_digit_independent_recomputation():
    coil_radius, coil_z, current, turns = _example_coils()
    radius, _, _ = _gseq_geometry(0.31, -0.07, coil_radius, coil_z)
    flux, br, bz = evaluate_filament_coil_green_field(
        radius, -0.07, coil_radius, coil_z, current, turns
    )
    expected = _mp_closed_form(radius, -0.07, coil_radius, coil_z, current, turns)
    for got, want in zip((flux, br, bz), expected):
        assert abs(got - want) <= 1e-13 * abs(want)


def test_green_response_is_linear_in_current_and_symmetric_pair_gives_zero_br():
    coil_radius, coil_z, current, turns = _example_coils()
    radius, _, _ = _gseq_geometry(0.3, 0.0, coil_radius, coil_z)
    flux, br, bz = evaluate_filament_coil_green_field(
        radius, 0.0, coil_radius, coil_z, current, turns
    )
    scaled = evaluate_filament_coil_green_field(
        radius, 0.0, coil_radius, coil_z, 2.0 * current, turns
    )
    assert scaled[0] == 2.0 * flux and scaled[1] == 2.0 * br and scaled[2] == 2.0 * bz
    pair_r = np.array([0.2, 0.2])
    pair_z = np.array([-0.1, 0.1])
    _, br_pair, _ = evaluate_filament_coil_green_field(
        radius, 0.0, pair_r, pair_z, np.array([10.0, 10.0]), np.array([2.0, 2.0])
    )
    assert abs(br_pair) < 1.0e-18


def test_green_response_agrees_with_the_other_field_green_asset():
    coil_radius, coil_z, current, turns = _example_coils()
    radius, _, _ = _gseq_geometry(0.3, 0.0, coil_radius, coil_z)
    flux, br, bz = evaluate_filament_coil_green_field(
        radius, 0.0, coil_radius, coil_z, current, turns
    )
    sources = np.column_stack((coil_radius, coil_z, turns * current))
    other = circular_filament_green_response(sources, [[radius, 0.0]])
    np.testing.assert_allclose(
        [flux, br, bz],
        [other["gpsi"][0], other["gBR"][0], other["gBZ"][0]],
        rtol=1e-15,
        atol=0.0,
    )


@pytest.mark.parametrize("r0", [1e-8, 1e-6, 1e-4, 1e-3, 1e-2])
def test_green_response_is_accurate_near_the_axis(r0):
    """Issue #10 item 4: psi and B_R must not lose accuracy as the axis is approached."""
    coil_radius = np.array([0.5])
    coil_z = np.array([0.1])
    current = np.array([1.0])
    turns = np.array([1.0])
    radius, _, _ = _gseq_geometry(r0, 0.0, coil_radius, coil_z)
    flux, br, bz = evaluate_filament_coil_green_field(
        radius, 0.0, coil_radius, coil_z, current, turns
    )
    expected = _mp_closed_form(radius, 0.0, coil_radius, coil_z, current, turns)
    for got, want in zip((flux, br, bz), expected):
        assert abs(got - want) <= 1e-12 * abs(want)
    # near-axis sign and finiteness: psi keeps the reference sign, B_Z stays finite
    assert np.sign(flux) == np.sign(expected[0])
    assert np.isfinite(bz)


def test_green_response_is_continuous_across_the_kernel_branch_switch():
    """Both sides of the m = 0.5 kernel switch must match the 50-digit reference.

    Comparing two neighbouring radii would only measure the field gradient; the
    branch-jump question is answered by checking each side against the
    independent recomputation, which has no branch switch of its own.
    """
    coil_radius = np.array([0.5])
    coil_z = np.array([0.0])
    current = np.array([1.0])
    turns = np.array([1.0])
    r_values = np.linspace(0.02, 0.45, 20001)
    moduli = 4.0 * (r_values + _AXIS_OFFSET_M) * 0.5 / (r_values + _AXIS_OFFSET_M + 0.5) ** 2
    crossing = int(np.argmin(np.abs(moduli - 0.5)))
    assert abs(moduli[crossing] - 0.5) < 1e-4
    for index in (crossing - 1, crossing + 1):
        radius = r_values[index] + _AXIS_OFFSET_M
        got = evaluate_filament_coil_green_field(radius, 0.0, coil_radius, coil_z, current, turns)
        want = _mp_closed_form(radius, 0.0, coil_radius, coil_z, current, turns)
        for a, b in zip(got, want):
            assert abs(a - b) <= 1e-12 * abs(b)


def test_green_response_keeps_the_near_axis_scaling_invariants():
    """Issue #10 item 4: the near-axis cancellation shows up in the scaled limits.

    A plain value comparison can be fooled when both sides carry the same
    relative error at small magnitude; the scaled quantities cannot.  With the
    regularized radius r, the closed forms scale as psi ~ r^2, B_R ~ r and
    B_Z ~ const, so psi/r^2 and B_R/r must approach the oracle's finite limits
    while B_Z approaches a constant.  The B_R scaling is linear, not quadratic:
    a quadratic ratio diverges here (checked against the same oracle).  The
    linear scaling follows from this asset's geometry -- the geometric axis with
    the observation plane offset from the coil plane is an off-plane dipole
    expansion, not the equilibrium magnetic-axis expansion, where B_R would
    scale as r^2.  Do not change the scaling back to r^2 without re-deriving it
    for this geometry.
    """
    coil_radius = np.array([0.5])
    coil_z = np.array([0.1])
    current = np.array([1.0])
    turns = np.array([1.0])
    limits = []
    for r0 in (1e-6, 1e-8, 1e-10):
        radius = r0 + _AXIS_OFFSET_M
        flux, br, bz = evaluate_filament_coil_green_field(
            radius, 0.0, coil_radius, coil_z, current, turns
        )
        want = _mp_closed_form(radius, 0.0, coil_radius, coil_z, current, turns)
        scaled = (flux / radius**2, br / radius, bz)
        expected = (want[0] / radius**2, want[1] / radius, want[2])
        for got, ref in zip(scaled, expected):
            assert np.isfinite(got) and got != 0.0
            assert abs(got - ref) <= 1e-9 * abs(ref)
        limits.append(scaled)
    # the scaled limits are stable across six decades of approach to the axis
    for index in range(3):
        values = [item[index] for item in limits]
        spread = max(values) - min(values)
        assert spread <= 1e-9 * abs(values[0])


def test_singular_coincident_chain_is_rejected_not_returned_as_nan():
    coil_radius = np.array([0.3])
    coil_z = np.array([0.2])
    with pytest.raises(ValueError, match="singular"):
        evaluate_filament_coil_green_field(
            0.3, 0.2, coil_radius, coil_z, np.array([1.0]), np.array([1.0])
        )


def test_nonfinite_output_overflow_fails_closed():
    with pytest.raises((ValueError, FloatingPointError)):
        evaluate_filament_coil_green_field(
            1.0e-300,
            0.0,
            np.array([1.0e-300]),
            np.array([0.0]),
            np.array([1.0e308]),
            np.array([1.0e308]),
        )


def test_green_response_rejects_singular_and_misaligned_inputs():
    coil_radius, coil_z, current, turns = _example_coils()
    radius, _, _ = _gseq_geometry(0.3, 0.0, coil_radius, coil_z)
    cases = [
        (np.nan, 0.0, coil_radius, coil_z, current, turns),
        (-0.5, 0.0, coil_radius, coil_z, current, turns),
        (radius, np.nan, coil_radius, coil_z, current, turns),
        (radius, 0.0, coil_radius, coil_z, current, turns[:-1]),
        (radius, 0.0, coil_radius * 0.0, coil_z, current, turns),
    ]
    for case in cases:
        with pytest.raises(ValueError):
            evaluate_filament_coil_green_field(*case)
