"""Direct contract tests for the r72 cross-node leaf family (FIDASIM):
``dd_reaction_rate_per_s`` and ``calculate_fast_ion_relative_energy`` (N9
neutron_response), ``allocate_mc_markers_by_weight`` (N7
fast_ion_fida_response), ``normalize_nbi_injected_neutrals`` and
``nbi_cell_directed_ray`` (N2 neutral_beam_source_sampling).

These are independent leaves from different framework nodes; no cross-node
composition is asserted.  The saved package's own probes (centerline ray
acceptance, the theta_z-uses-focy quirk) are reproduced.  Registered
hardenings (finite-output gates, marker-count conservation, strict integer
branch index) discriminate against the saved arms' silent Inf returns.
Fixture random sources are freshly seeded per call so single affected-test
runs see byte-identical carriers to the whole-file run.
"""
from __future__ import annotations

import numpy as np
import pytest

from scirel.fusion import (
    allocate_mc_markers_by_weight,
    calculate_fast_ion_relative_energy,
    dd_reaction_rate_per_s,
    nbi_cell_directed_ray,
    normalize_nbi_injected_neutrals,
)


def _rate_table():
    rng = np.random.default_rng(94)
    # log10 rate table in [1, 3]: rates 10..1000 m^3/s after exponentiation
    return rng.uniform(1.0, 3.0, size=(4, 3, 2))


def _ray_kwargs(**overrides):
    kwargs = dict(
        cell_center_uvw_cm=[10, 0, 0], cell_offset_cm=[0, 0, 0],
        source_xyz_cm=[0, 0, 0], beam_origin_uvw_cm=[0, 0, 0],
        inverse_beam_basis=np.eye(3), beam_basis=np.eye(3),
        injection_speed_cm_s=100, neutral_type=1,
        aperture_distance_cm=[5], aperture_shape=[1],
        aperture_offset_y_cm=[0], aperture_offset_z_cm=[0],
        aperture_half_width_y_cm=[2], aperture_half_width_z_cm=[2],
        focus_y_cm=100, focus_z_cm=100,
        divergence_y_rad=[.1, .1, .1], divergence_z_rad=[.1, .1, .1],
    )
    kwargs.update(overrides)
    return kwargs


# ----------------------------- N9: DD rate table ---------------------------

def test_dd_rate_matches_independent_bilinear_recomputation():
    table = _rate_table()
    e_min, e_step, t_min, t_step = 1.0, 1.0, 1.0, 0.5
    beam_e, ti = 10.0 ** 1.7, 10.0 ** 1.4
    density = 3.0
    out = dd_reaction_rate_per_s(
        beam_energy_kev=beam_e, ion_temperature_kev=ti,
        deuterium_target_density_cm3=density,
        energy_log_min=e_min, energy_log_step=e_step,
        temperature_log_min=t_min, temperature_log_step=t_step,
        log_rate_table=table, min_log_rate=-10.0, branch_index=0)
    u, v = 1.7 - 1.0, (1.4 - 1.0) / 0.5
    i, j = int(np.floor(u)), int(np.floor(v))
    fu, fv = u - i, v - j
    expected_log = ((1 - fu) * (1 - fv) * table[i, j, 0]
                    + fu * (1 - fv) * table[i + 1, j, 0]
                    + (1 - fu) * fv * table[i, j + 1, 0]
                    + fu * fv * table[i + 1, j + 1, 0])
    np.testing.assert_allclose(out, density * 10.0 ** expected_log, rtol=1e-15)


def test_dd_rate_zero_beyond_last_interval_and_min_log_gate():
    table = _rate_table()
    e_min, e_step = 1.0, 1.0
    # beam energy beyond the last energy interval -> 0 (source behavior)
    out = dd_reaction_rate_per_s(
        beam_energy_kev=10.0 ** (e_min + 4 * e_step + 1.0), ion_temperature_kev=10.0,
        deuterium_target_density_cm3=1.0,
        energy_log_min=e_min, energy_log_step=e_step,
        temperature_log_min=1.0, temperature_log_step=0.5,
        log_rate_table=table, min_log_rate=2.5, branch_index=0)
    # clamped to the last interval; with min_log_rate above the table values
    # the min-log gate returns 0
    assert out == 0.0


def test_dd_rate_rejects_bad_table_and_branch():
    table = _rate_table()
    base = dict(beam_energy_kev=10.0, ion_temperature_kev=10.0,
                deuterium_target_density_cm3=1.0,
                energy_log_min=1.0, energy_log_step=1.0,
                temperature_log_min=1.0, temperature_log_step=0.5,
                log_rate_table=table, min_log_rate=-10.0)
    for bad in (
        dict(base, log_rate_table=np.zeros((4, 3))),
        dict(base, branch_index=True),
        dict(base, branch_index=2),
        dict(base, branch_index=1.0),
        dict(base, beam_energy_kev=0.0),
        dict(base, deuterium_target_density_cm3=-1.0),
        dict(base, energy_log_step=0.0),
        dict(base, log_rate_table=np.full_like(table, np.nan)),
        # recorded hardening: extreme axis step overflows the normalized
        # coordinates; the saved arm raises a bare OverflowError from
        # int(floor(inf)), this port raises the common ValueError.
        # beam_energy_kev=10^1.5 with energy_log_min=1.0 gives
        # u=(1.5-1.0)/1e-320 = Inf
        dict(base, beam_energy_kev=10.0 ** 1.5, energy_log_step=1e-320),
    ):
        with pytest.raises(ValueError):
            dd_reaction_rate_per_s(**bad)


def test_dd_rate_extreme_table_contents_fail_closed():
    # recorded hardening witness: table values near the exponentiation
    # ceiling overflow 10**log_rate; the saved arm returns Inf silently
    table = np.full((2, 2, 1), 400.0)
    with pytest.raises(ValueError, match="overflowed"):
        dd_reaction_rate_per_s(
            beam_energy_kev=10.0, ion_temperature_kev=10.0,
            deuterium_target_density_cm3=1e300,
            energy_log_min=1.0, energy_log_step=1.0,
            temperature_log_min=1.0, temperature_log_step=0.5,
            log_rate_table=table, min_log_rate=-10.0, branch_index=0)


# ------------------------- N9: fast-ion relative energy --------------------

def test_relative_energy_matches_closed_form_and_is_zero_at_rest():
    rotation = np.array([1.0e5, -2.0e5, 3.0e5])
    ion = rotation + np.array([3.0e7, -1.0e7, 5.0e7])
    out = calculate_fast_ion_relative_energy(
        ion_velocity_cm_s=ion, plasma_rotation_cm_s=rotation,
        ion_mass_amu=2.0, velocity_squared_to_kev_per_amu=0.01)
    expected = 0.01 * 2.0 * np.dot(ion - rotation, ion - rotation)
    assert out["relative_beam_energy_kev"] == expected
    np.testing.assert_array_equal(out["relative_velocity_cm_s"], ion - rotation)
    rest = calculate_fast_ion_relative_energy(
        ion_velocity_cm_s=rotation, plasma_rotation_cm_s=rotation,
        ion_mass_amu=2.0, velocity_squared_to_kev_per_amu=0.01)
    assert rest["relative_beam_energy_kev"] == 0.0


def test_relative_energy_rejects_bad_inputs_and_extremes():
    rotation = np.array([0.0, 0.0, 0.0])
    for bad in (
        dict(ion_velocity_cm_s=[np.nan, 0, 0], plasma_rotation_cm_s=rotation,
             ion_mass_amu=2.0, velocity_squared_to_kev_per_amu=0.01),
        dict(ion_velocity_cm_s=[1.0, 0], plasma_rotation_cm_s=rotation,
             ion_mass_amu=2.0, velocity_squared_to_kev_per_amu=0.01),
        dict(ion_velocity_cm_s=[1e7, 0, 0], plasma_rotation_cm_s=rotation,
             ion_mass_amu=0.0, velocity_squared_to_kev_per_amu=0.01),
        dict(ion_velocity_cm_s=[1e7, 0, 0], plasma_rotation_cm_s=rotation,
             ion_mass_amu=2.0, velocity_squared_to_kev_per_amu=0.0),
    ):
        with pytest.raises(ValueError):
            calculate_fast_ion_relative_energy(**bad)
    # recorded hardening witness: max-finite velocities overflow the dot
    with pytest.raises(ValueError, match="overflowed"):
        calculate_fast_ion_relative_energy(
            ion_velocity_cm_s=[np.finfo(float).max, 0.0, 0.0],
            plasma_rotation_cm_s=rotation,
            ion_mass_amu=1.0, velocity_squared_to_kev_per_amu=1.0)


# ------------------------- N7: MC marker allocation ------------------------

def test_marker_allocation_conserves_count_and_uses_fortran_order_cdf():
    weight = np.zeros((2, 2, 2))
    weight[0, 0, 0] = 1.0
    weight[1, 1, 1] = 3.0
    # 4 active cells * min 5 = 20 base markers; 10 remainder, all to cell
    # (1,1,1) because its weight dominates the CDF (draws 0.5 < 0.75/1.0
    # after the first cell's 0.25 share... verify against the independent
    # CDF recomputation below)
    draws = np.linspace(0.0, 0.95, 10)
    counts = allocate_mc_markers_by_weight(
        approximate_cell_weight=weight, requested_markers=20,
        cdf_uniform_draws=draws, minimum_per_active_cell=5)
    assert int(counts.sum()) == 20
    assert counts[0, 0, 0] >= 5 and counts[1, 1, 1] >= 5
    # independent CDF recomputation on the F-order flattened volume
    flat = weight.ravel(order="F")
    cdf = np.cumsum(flat)
    expected = np.zeros_like(counts)
    expected[weight > 0] = 5
    for d in draws:
        index = np.searchsorted(cdf, d * cdf[-1], side="right")
        expected[np.unravel_index(index, weight.shape, order="F")] += 1
    np.testing.assert_array_equal(counts, expected)


def test_marker_allocation_zero_remainder_skips_draw_validation():
    weight = np.ones((1, 1, 1))
    counts = allocate_mc_markers_by_weight(
        approximate_cell_weight=weight, requested_markers=5,
        cdf_uniform_draws=np.array([]), minimum_per_active_cell=5)
    assert counts[0, 0, 0] == 5


def test_marker_allocation_consumes_remainder_draws_and_conserves():
    weight = np.ones((1, 1, 1))
    counts = allocate_mc_markers_by_weight(
        approximate_cell_weight=weight, requested_markers=6,
        cdf_uniform_draws=np.array([0.5]), minimum_per_active_cell=5)
    assert counts[0, 0, 0] == 6
    assert int(counts.sum()) == 6
    # draws >= 1 are rejected when a remainder exists (validation reached)
    with pytest.raises(ValueError):
        allocate_mc_markers_by_weight(
            approximate_cell_weight=weight, requested_markers=6,
            cdf_uniform_draws=np.array([1.0]), minimum_per_active_cell=5)
    # recorded hardening: minimum allocation exceeding the request fails
    # closed instead of silently returning the overshoot (saved arm returns
    # count 5 for requested_markers=2 with minimum 5)
    with pytest.raises(ValueError, match="cannot be fulfilled"):
        allocate_mc_markers_by_weight(
            approximate_cell_weight=np.ones((1, 1, 1)), requested_markers=2,
            cdf_uniform_draws=np.array([]), minimum_per_active_cell=5)


def test_marker_allocation_rejects_bad_inputs_and_nonconservation_is_gated():
    weight = np.ones((1, 1, 1))
    for bad in (
        dict(approximate_cell_weight=np.full((1, 1, 1), np.nan),
             requested_markers=5, cdf_uniform_draws=np.array([0.5])),
        dict(approximate_cell_weight=np.full((1, 1, 1), -1.0),
             requested_markers=5, cdf_uniform_draws=np.array([0.5])),
        dict(approximate_cell_weight=weight, requested_markers=5.5,
             cdf_uniform_draws=np.array([0.5])),
        dict(approximate_cell_weight=weight, requested_markers=True,
             cdf_uniform_draws=np.array([0.5])),
        dict(approximate_cell_weight=np.zeros((1, 1, 1)), requested_markers=5,
             cdf_uniform_draws=np.array([0.5])),
    ):
        with pytest.raises(ValueError):
            allocate_mc_markers_by_weight(**bad)


# ----------------------- N2: NBI injected normalization --------------------

def test_nbi_normalization_matches_the_source_formula():
    out = normalize_nbi_injected_neutrals(
        1.0, 50.0, np.array([0.6, 0.3, 0.1]), 2.0e-6)
    expected_factor = 0.6 + 0.3 * 0.5 + 0.1 / 3.0
    assert out["energy_weight_factor"] == expected_factor
    expected_total = 1e6 * 1.0 / (1e3 * 50.0 * 1.602176634e-19 * expected_factor)
    assert out["total_neutral_rate_s_inv"] == expected_total
    np.testing.assert_array_equal(out["component_neutral_rate_s_inv"],
                                  expected_total * np.array([0.6, 0.3, 0.1]))
    np.testing.assert_array_equal(out["initial_state_rate_per_volume_cm_inv3_s_inv"],
                                  expected_total * np.array([0.6, 0.3, 0.1]) / 2.0e-6)


def test_nbi_normalization_zero_power_is_valid_and_extremes_fail_closed():
    out = normalize_nbi_injected_neutrals(
        0.0, 50.0, np.array([0.6, 0.3, 0.1]), 2.0e-6)
    assert out["total_neutral_rate_s_inv"] == 0.0
    np.testing.assert_array_equal(out["initial_state_rate_per_volume_cm_inv3_s_inv"],
                                  np.zeros(3))
    for bad in (
        (np.nan, 50.0, np.array([0.6, 0.3, 0.1]), 2.0e-6),
        (-1.0, 50.0, np.array([0.6, 0.3, 0.1]), 2.0e-6),
        (1.0, 0.0, np.array([0.6, 0.3, 0.1]), 2.0e-6),
        (1.0, 50.0, np.array([-0.1, 0.3, 0.1]), 2.0e-6),
        (1.0, 50.0, np.array([0.6, 0.3, 0.1]), 0.0),
        (1.0, 50.0, np.array([np.finfo(float).max] * 3), 2.0e-6),
        (1e308, 50.0, np.array([0.6, 0.3, 0.1]), 1e-300),
        # recorded hardening: non-finite energy passes a naive `<= 0` check
        # and returns rate 0; this port rejects it
        (1.0, float("inf"), np.array([0.6, 0.3, 0.1]), 1.0),
        (1.0, float("nan"), np.array([0.6, 0.3, 0.1]), 1.0),
    ):
        with pytest.raises(ValueError):
            normalize_nbi_injected_neutrals(*bad)


# --------------------------- N2: NBI cell ray ------------------------------

def test_ray_centerline_accepted_with_finite_weight_saved_probe():
    out = nbi_cell_directed_ray(
        [10, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], np.eye(3), np.eye(3),
        100, 1, [5], [1], [0], [0], [2], [2], 100, 100,
        [.1, .1, .1], [.1, .1, .1])
    assert out["accepted"]
    assert np.isclose(np.linalg.norm(out["velocity_uvw_cm_s"]), 100)
    assert out["trajectory_weight"] > 0


def test_ray_source_theta_z_keeps_focy_not_focz_saved_quirk():
    common = ([10, 0, 0], [0, 0, 0], [0, 1, 1], [0, 0, 0], np.eye(3),
              np.eye(3), 100, 1, [5], [1], [0], [0], [20], [20], 100)
    first = nbi_cell_directed_ray(*common, 10, [.1, .1, .1], [.1, .1, .1])["trajectory_weight"]
    second = nbi_cell_directed_ray(*common, 1000, [.1, .1, .1], [.1, .1, .1])["trajectory_weight"]
    assert np.isclose(first, second)


def test_ray_velocity_uses_the_float32_component_divisor():
    out = nbi_cell_directed_ray(
        [10, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], np.eye(3), np.eye(3),
        100, 1, [5], [1], [0], [0], [2], [2], 100, 100,
        [.1, .1, .1], [.1, .1, .1])
    # neutral_type=1 divides by sqrt(float32(1)) == 1: speed equals injection
    assert np.linalg.norm(out["velocity_uvw_cm_s"]) == 100.0
    out3 = nbi_cell_directed_ray(
        [10, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], np.eye(3), np.eye(3),
        100, 3, [5], [1], [0], [0], [2], [2], 100, 100,
        [.1, .1, .1], [.1, .1, .1])
    assert np.isclose(np.linalg.norm(out3["velocity_uvw_cm_s"]),
                      100.0 / np.sqrt(np.float32(3)), rtol=1e-7)


def test_ray_rejects_bad_contracts_and_extremes():
    for bad in (
        _ray_kwargs(cell_center_uvw_cm=[10, 0, 0], cell_offset_cm=[0, 0, 0],
                    source_xyz_cm=[0, 0, 0], beam_origin_uvw_cm=[10, 0, 0]),
        _ray_kwargs(neutral_type=4),
        _ray_kwargs(injection_speed_cm_s=0.0),
        _ray_kwargs(focus_y_cm=0.0),
        _ray_kwargs(aperture_shape=[3]),
        _ray_kwargs(aperture_distance_cm=[5, 5]),
        _ray_kwargs(divergence_y_rad=[0.0, 0.0, 0.0]),
    ):
        with pytest.raises(ValueError):
            nbi_cell_directed_ray(**bad)
    # recorded hardening witness: an extreme inverse_beam_basis drives the
    # receiver transform to Inf, which propagates into the outputs
    with pytest.raises(ValueError, match="non-finite"):
        nbi_cell_directed_ray(
            [np.finfo(float).max, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0],
            np.eye(3), np.eye(3), 100, 1, [5], [1], [0], [0], [2], [2],
            100, 100, [.1, .1, .1], [.1, .1, .1])
    # recorded hardening: py and pz each finite but their product overflows
    # to Inf (divergences near the float underflow); the saved arm returns
    # Inf silently
    with pytest.raises(ValueError, match="overflowed"):
        nbi_cell_directed_ray(
            [10, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], np.eye(3), np.eye(3),
            100, 1, [5], [1], [0], [0], [2], [2], 100, 100,
            [1e-160, 1e-160, 1e-160], [1e-160, 1e-160, 1e-160])
    # non-finite focus lengths are rejected (the saved arm checks only zero)
    with pytest.raises(ValueError):
        nbi_cell_directed_ray(**_ray_kwargs(focus_z_cm=float("inf")))
    # recorded hardening: extreme divergences underflow the Gaussian
    # exponentials to 0.0, making an accepted ray carry weight 0.0 (the
    # saved arm returns accepted=True, weight=0.0 silently)
    with pytest.raises(ValueError, match="non-positive trajectory weight"):
        nbi_cell_directed_ray(
            [10, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], np.eye(3), np.eye(3),
            100, 1, [5], [1], [0], [0], [2], [2], 100, 100,
            [1e308, 1e308, 1e308], [1e308, 1e308, 1e308])
    # recorded hardening: NaN aperture distance passes the saved arm (only
    # the acceptance flag flips to False); the finite-input check rejects it
    with pytest.raises(ValueError):
        nbi_cell_directed_ray(**_ray_kwargs(
            aperture_distance_cm=[float("nan")]))
