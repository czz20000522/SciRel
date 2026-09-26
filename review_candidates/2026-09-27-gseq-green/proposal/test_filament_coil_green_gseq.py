"""Direct contract tests for the r69 GSEQ filament-coil Green family:
``compute_axisymmetric_coil_modulus``,
``evaluate_complete_elliptic_integrals`` and
``evaluate_filament_coil_green_field``.

The three operators form the GSEQ Green chain (geometry -> elliptic values ->
responses).  The oracle tests re-derive the closed forms independently; the
cross-implementation tests quantify the source polynomial-log K/E
approximation against the baseline scipy-elliptic filament response on the
same filament geometry (sampled evidence over probed grids, not bounds over
the continuous domain).  Fixture random sources are freshly seeded per call
so single affected-test runs see byte-identical carriers to the whole-file
run.
"""
from __future__ import annotations

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
    a_k = ((((0.01451196212 * p + 0.03742563713) * p + 0.03590092383) * p + 0.09666344259) * p + 1.38629436112)
    b_k = ((((0.00441787012 * p + 0.03328355346) * p + 0.06880248576) * p + 0.12498593597) * p + 0.5)
    a_e = ((((0.01736506451 * p + 0.04757383546) * p + 0.0626060122) * p + 0.44325141463) * p + 1.0)
    b_e = ((((0.00526449639 * p + 0.04069697526) * p + 0.09200180037) * p + 0.2499836831) * p)
    return a_k - b_k * np.log(p), a_e - b_e * np.log(p)


def test_geometry_returns_source_regularized_radius_modulus_and_distance():
    coil_radius, coil_z, _, _ = _example_coils()
    radius, modulus, distance = compute_axisymmetric_coil_modulus(0.3, 0.1, coil_radius, coil_z)
    assert radius == 0.3 + _AXIS_OFFSET_M
    expected_denom = (radius + coil_radius) ** 2 + (0.1 - coil_z) ** 2
    np.testing.assert_allclose(modulus, 4.0 * radius * coil_radius / expected_denom, rtol=1e-15, atol=0.0)
    np.testing.assert_allclose(distance, np.sqrt(expected_denom), rtol=1e-15, atol=0.0)
    assert np.all((modulus > 0.0) & (modulus <= 1.0))
    # the axis point is admissible: the source offset makes r0 positive
    radius_axis, _, _ = compute_axisymmetric_coil_modulus(0.0, 0.0, coil_radius, coil_z)
    assert radius_axis == _AXIS_OFFSET_M


def test_geometry_rejects_invalid_inputs():
    coil_radius, coil_z, _, _ = _example_coils()
    bad = [
        (np.nan, 0.0, coil_radius, coil_z),
        (np.inf, 0.0, coil_radius, coil_z),
        (0.3, np.nan, coil_radius, coil_z),
        (0.3, 0.0, np.array([0.2, -0.1]), np.array([0.0, 0.1])),
        (0.3, 0.0, np.array([0.2, 0.1]), np.array([0.0])),
        (0.3, 0.0, np.array([[0.2], [0.1]]), np.array([[0.0], [0.1]])),
    ]
    for args in bad:
        with pytest.raises(ValueError):
            compute_axisymmetric_coil_modulus(*args)


def test_negative_raw_radius_within_offset_width_is_rejected():
    """Registered hardening: a raw radius in (-1e-8, 0) would turn positive
    through the axis offset alone; the saved implementation accepts it, this
    port rejects the silently re-labelled point."""
    for raw in (-5e-9, -1e-12):
        with pytest.raises(ValueError, match="nonnegative"):
            compute_axisymmetric_coil_modulus(raw, 0.0, np.array([0.2]), np.array([0.0]))
    # the axis point itself stays admissible
    radius, _, _ = compute_axisymmetric_coil_modulus(0.0, 0.0, np.array([0.2]), np.array([0.0]))
    assert radius == _AXIS_OFFSET_M


def test_elliptic_approximation_matches_the_source_polynomial_log_form():
    rng = np.random.default_rng(70)
    m = rng.uniform(0.0, 0.999, size=(7,))
    k, e = evaluate_complete_elliptic_integrals(m)
    k_expected, e_expected = _polynomial_log_k_e(m)
    assert np.array_equal(k, k_expected)
    assert np.array_equal(e, e_expected)
    # scipy reference: sampled agreement to the documented approximation error
    from scipy.special import ellipe, ellipk
    m_probe = np.linspace(1e-6, 0.999999, 200001)
    k_ref, e_ref = ellipk(m_probe), ellipe(m_probe)
    k_apx, e_apx = _polynomial_log_k_e(m_probe)
    assert np.max(np.abs(k_apx - k_ref) / k_ref) < 1e-8
    assert np.max(np.abs(e_apx - e_ref) / e_ref) < 2e-8


def test_elliptic_approximation_whole_array_sentinel_and_mixed_singular_path():
    # every element == 1: finite sentinel branch
    k, e = evaluate_complete_elliptic_integrals(np.array([1.0, 1.0]))
    assert np.array_equal(k, np.array([1.0e300, 1.0e300]))
    assert np.array_equal(e, np.array([1.0, 1.0]))
    # mixed: the m == 1 element takes the polynomial-log branch (K=+Inf, E=NaN)
    k, e = evaluate_complete_elliptic_integrals(np.array([0.5, 1.0]))
    assert np.isinf(k[1]) and k[1] > 0
    assert np.isnan(e[1])
    assert np.isfinite(k[0]) and np.isfinite(e[0])
    with pytest.raises(ValueError):
        evaluate_complete_elliptic_integrals(np.array([-0.1, 0.5]))
    with pytest.raises(ValueError):
        evaluate_complete_elliptic_integrals(np.array([1.1]))
    with pytest.raises(ValueError):
        evaluate_complete_elliptic_integrals(np.array([np.nan]))


def test_green_response_matches_its_independent_closed_form():
    coil_radius, coil_z, current, turns = _example_coils()
    r0_raw, z0 = 0.31, -0.07
    radius, modulus, _ = _gseq_geometry(r0_raw, z0, coil_radius, coil_z)
    k, e = evaluate_complete_elliptic_integrals(modulus)
    flux, br, bz = evaluate_filament_coil_green_field(
        radius, z0, coil_radius, coil_z, current, turns, modulus, k, e)
    dz = z0 - coil_z
    factor = _MU0_OVER_2PI * turns * current
    distance = np.sqrt((radius + coil_radius) ** 2 + dz**2)
    separation2 = (radius - coil_radius) ** 2 + dz**2
    flux_expected = np.sum(factor / np.sqrt(modulus) * np.sqrt(radius * coil_radius)
                           * ((2.0 - modulus) * k - 2.0 * e))
    br_expected = np.sum(factor * dz / radius / distance
                         * ((radius**2 + coil_radius**2 + dz**2) / separation2 * e - k))
    bz_expected = np.sum(factor / distance
                         * ((coil_radius**2 - radius**2 - dz**2) / separation2 * e + k))
    assert flux == flux_expected
    assert br == br_expected
    assert bz == bz_expected
    assert all(np.isfinite(v) for v in (flux, br, bz))


def test_green_response_is_linear_in_current_and_symmetric_pair_gives_zero_br():
    coil_radius, coil_z, current, turns = _example_coils()
    radius, modulus, _ = _gseq_geometry(0.3, 0.0, coil_radius, coil_z)
    k, e = evaluate_complete_elliptic_integrals(modulus)
    flux, br, bz = evaluate_filament_coil_green_field(
        radius, 0.0, coil_radius, coil_z, current, turns, modulus, k, e)
    scaled = evaluate_filament_coil_green_field(
        radius, 0.0, coil_radius, coil_z, 2.0 * current, turns, modulus, k, e)
    assert scaled[0] == 2.0 * flux and scaled[1] == 2.0 * br and scaled[2] == 2.0 * bz
    # a mirrored coil pair on the midplane gives Br = 0
    pair_r = np.array([0.2, 0.2])
    pair_z = np.array([-0.1, 0.1])
    _, mod_pair, _ = _gseq_geometry(0.3, 0.0, pair_r, pair_z)
    k_p, e_p = evaluate_complete_elliptic_integrals(mod_pair)
    _, br_pair, _ = evaluate_filament_coil_green_field(
        radius, 0.0, pair_r, pair_z, np.array([10.0, 10.0]), np.array([2.0, 2.0]),
        mod_pair, k_p, e_p)
    assert abs(br_pair) < 1.0e-18


def test_green_response_with_scipy_elliptics_matches_the_baseline_asset():
    """Same filament geometry AND same elliptic values (scipy): the GSEQ
    closed form and the baseline circular-filament response are the same
    physics and must agree to round-off.  The baseline target receives the
    regularized radius because the GSEQ contract offsets the observation
    axis before evaluation."""
    rng = np.random.default_rng(71)
    from scipy.special import ellipe, ellipk
    for _ in range(5):
        rl = rng.uniform(0.1, 0.5)
        zl = rng.uniform(-0.4, 0.4)
        weight = rng.uniform(2.0, 30.0)
        r0_raw = rng.uniform(0.15, 0.8)
        z0 = rng.uniform(-0.3, 0.3)
        radius, modulus, _ = _gseq_geometry(r0_raw, z0, np.array([rl]), np.array([zl]))
        k = np.array([ellipk(modulus[0])])
        e = np.array([ellipe(modulus[0])])
        flux, br, bz = evaluate_filament_coil_green_field(
            radius, z0, np.array([rl]), np.array([zl]),
            np.array([weight]), np.array([1.0]), modulus, k, e)
        reference = circular_filament_green_response(
            np.array([[rl, zl, weight]]), np.array([[radius, z0]]))
        np.testing.assert_allclose(flux, reference["gpsi"][0], rtol=1e-12, atol=1e-18)
        np.testing.assert_allclose(br, reference["gBR"][0], rtol=1e-12, atol=1e-18)
        np.testing.assert_allclose(bz, reference["gBZ"][0], rtol=1e-12, atol=1e-18)


def test_source_approximation_degrades_the_response_within_documented_error():
    """Feeding the source's polynomial-log K/E instead of scipy's shifts the
    responses by the approximation error amplified through the closed form.
    Sampled bound over probed geometries (documented as sampled evidence)."""
    rng = np.random.default_rng(72)
    from scipy.special import ellipe, ellipk
    for _ in range(5):
        rl = rng.uniform(0.1, 0.5)
        zl = rng.uniform(-0.4, 0.4)
        weight = rng.uniform(2.0, 30.0)
        r0_raw = rng.uniform(0.15, 0.8)
        z0 = rng.uniform(-0.3, 0.3)
        radius, modulus, _ = _gseq_geometry(r0_raw, z0, np.array([rl]), np.array([zl]))
        k_src, e_src = evaluate_complete_elliptic_integrals(modulus)
        k_ref = np.array([ellipk(modulus[0])])
        e_ref = np.array([ellipe(modulus[0])])
        out_src = evaluate_filament_coil_green_field(
            radius, z0, np.array([rl]), np.array([zl]),
            np.array([weight]), np.array([1.0]), modulus, k_src, e_src)
        out_ref = evaluate_filament_coil_green_field(
            radius, z0, np.array([rl]), np.array([zl]),
            np.array([weight]), np.array([1.0]), modulus, k_ref, e_ref)
        for a, b in zip(out_src, out_ref):
            assert abs(a - b) <= 1e-5 * abs(b) + 1e-15


def test_singular_coincident_chain_is_rejected_not_returned_as_nan():
    """The recorded pre-review failure chain: a regularized radius that lands
    exactly on the filament ring drives the geometry operator to modulus == 1,
    the elliptic operator to its finite sentinel, and the source response to
    silent (2e293, NaN, NaN).  This port must reject at the response stage."""
    radius, modulus, _ = compute_axisymmetric_coil_modulus(
        0.99999999, 0.0, np.array([1.0]), np.array([0.0]))
    assert modulus[0] == 1.0
    k, e = evaluate_complete_elliptic_integrals(modulus)
    assert np.array_equal(k, np.array([1.0e300]))
    assert np.array_equal(e, np.array([1.0]))
    with pytest.raises(ValueError, match="singular coil geometry"):
        evaluate_filament_coil_green_field(
            radius, 0.0, np.array([1.0]), np.array([0.0]),
            np.array([1.0]), np.array([1.0]), modulus, k, e)
    # mixed singular coil among regular ones is likewise rejected: the m == 1
    # element takes the polynomial-log branch (K=+Inf, E=NaN) and is caught by
    # the input validation, which only tolerates non-finite pairings via the
    # separate zero-separation/modulus gate
    coil_radius = np.array([0.2, float(radius)])
    coil_z = np.array([0.0, 0.0])
    r2, modulus2, _ = compute_axisymmetric_coil_modulus(0.99999999, 0.0, coil_radius, coil_z)
    assert np.any(modulus2 == 1.0)
    k2, e2 = evaluate_complete_elliptic_integrals(modulus2)
    assert np.isinf(k2[1]) and np.isnan(e2[1])
    with pytest.raises(ValueError):
        evaluate_filament_coil_green_field(
            r2, 0.0, coil_radius, coil_z,
            np.array([1.0, 1.0]), np.array([1.0, 1.0]), modulus2, k2, e2)


def test_nonfinite_output_overflow_fails_closed():
    """Registered hardening: finite but extreme input magnitudes overflow the
    squared geometry sums or the response factor; the saved implementations
    would hand NaN/Inf downstream silently, this port raises instead."""
    # geometry: r0 = rl = 1e308 -> (r0+rl)^2 = inf -> modulus 0/inf, distance inf
    with pytest.raises(ValueError, match="overflowed"):
        compute_axisymmetric_coil_modulus(1e308, 0.0, np.array([1e308]), np.array([0.0]))
    # response: extreme current overflows the combined factor
    coil_radius, coil_z, current, turns = _example_coils()
    radius, modulus, _ = _gseq_geometry(0.31, -0.07, coil_radius, coil_z)
    k, e = evaluate_complete_elliptic_integrals(modulus)
    with pytest.raises(ValueError, match="overflowed"):
        evaluate_filament_coil_green_field(
            radius, -0.07, coil_radius, coil_z,
            np.full_like(current, 1e308), np.full_like(turns, 1e308), modulus, k, e)


def test_green_response_rejects_singular_and_misaligned_inputs():
    coil_radius, coil_z, current, turns = _example_coils()
    radius, modulus, _ = _gseq_geometry(0.31, -0.07, coil_radius, coil_z)
    k, e = evaluate_complete_elliptic_integrals(modulus)
    bad = [
        # modulus out of (0, 1]
        (radius, -0.07, coil_radius, coil_z, current, turns, modulus * 0.0, k, e),
        (radius, -0.07, coil_radius, coil_z, current, turns, modulus + 0.5, k, e),
        # non-finite elliptic pairing while modulus != 1
        (radius, -0.07, coil_radius, coil_z, current, turns, modulus, np.full_like(k, np.nan), e),
        (radius, -0.07, coil_radius, coil_z, current, turns, modulus, k, np.full_like(e, np.inf)),
        # shape mismatch
        (radius, -0.07, coil_radius, coil_z, current, turns[:-1], modulus, k, e),
        # non-positive coil radius
        (radius, -0.07, coil_radius * 0.0, coil_z, current, turns, modulus, k, e),
        # non-finite / non-positive observation radius
        (np.nan, -0.07, coil_radius, coil_z, current, turns, modulus, k, e),
        (-0.5, -0.07, coil_radius, coil_z, current, turns, modulus, k, e),
    ]
    for args in bad:
        with pytest.raises(ValueError):
            evaluate_filament_coil_green_field(*args)
    # non-finite observation z
    with pytest.raises(ValueError):
        evaluate_filament_coil_green_field(radius, np.nan, coil_radius, coil_z,
                                           current, turns, modulus, k, e)
