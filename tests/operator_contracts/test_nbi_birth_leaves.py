"""Direct contract tests for the r71 NBI birth/geometry leaf family
(FIDASIM sources): ``scale_nbi_velocity_for_energy_component``,
``materialize_nbi_component_initial_state``, ``sample_halo_velocity``,
``sample_beam_grid_cell`` and ``pitch_gyro_to_velocity_direction``.

All five leaves keep the randomness caller-owned (explicit draws), so every
test is a deterministic function of its inputs.  The registered hardenings
(finite positive scalar speed, strict integer component index, finite output
gates) discriminate against the saved arms' silent NaN/Inf returns.
Fixture random sources are freshly seeded per call so single affected-test
runs see byte-identical carriers to the whole-file run.
"""
from __future__ import annotations

import numpy as np
import pytest

from scirel.fusion import (
    materialize_nbi_component_initial_state,
    pitch_gyro_to_velocity_direction,
    sample_beam_grid_cell,
    sample_halo_velocity,
    scale_nbi_velocity_for_energy_component,
)


def _orthonormal_frame():
    return (np.array([1.0, 0.0, 0.0]),
            np.array([0.0, 1.0, 0.0]),
            np.array([0.0, 0.0, 1.0]))


def test_velocity_scaling_matches_the_closed_form_with_float32_divisor():
    rng = np.random.default_rng(90)
    ray = rng.normal(size=3)
    ray /= np.linalg.norm(ray)
    for component in (1, 2, 3):
        result = scale_nbi_velocity_for_energy_component(ray, 2.0e8, component)
        expected = ray * 2.0e8 / np.sqrt(np.float32(component))
        np.testing.assert_array_equal(result, expected)
        # full-energy component divides by exactly 1
        if component == 1:
            np.testing.assert_array_equal(result, ray * 2.0e8)
    # half/third components shorten the vector by the component factor
    len_full = np.linalg.norm(scale_nbi_velocity_for_energy_component(ray, 2.0e8, 1))
    len_half = np.linalg.norm(scale_nbi_velocity_for_energy_component(ray, 2.0e8, 2))
    len_third = np.linalg.norm(scale_nbi_velocity_for_energy_component(ray, 2.0e8, 3))
    assert len_half == pytest.approx(len_full / np.sqrt(2.0), rel=1e-7)
    assert len_third == pytest.approx(len_full / np.sqrt(3.0), rel=1e-7)


def test_velocity_scaling_rejects_nonfinite_speed_bool_and_float_component():
    ray = np.array([1.0, 0.0, 0.0])
    # recorded pre-review probes: NaN speed passes a naive <=0 check and
    # returns NaN; True/1.0 pass naive tuple membership as component 1.
    for bad_speed in (np.nan, np.inf, -1.0, 0.0):
        with pytest.raises(ValueError):
            scale_nbi_velocity_for_energy_component(ray, bad_speed, 1)
    for bad_component in (True, 1.0, 0, 4):
        with pytest.raises(ValueError):
            scale_nbi_velocity_for_energy_component(ray, 2.0e8, bad_component)
    for bad_ray in (np.array([np.nan, 0.0, 0.0]), np.array([2.0, 0.0, 0.0]),
                    np.array([1.0, 0.0])):
        with pytest.raises(ValueError):
            scale_nbi_velocity_for_energy_component(bad_ray, 2.0e8, 1)
    # Recorded overflow witness (reviewer-verified): a ray whose norm passes
    # the 1e-12 isclose window but exceeds 1.0 times the max finite speed
    # overflows the multiply; the finite-output gate rejects it.  The gate is
    # reachable, not merely a backstop.
    tilted_ray = np.array([1.0 + 1e-12, 0.0, 0.0])
    max_finite = float(np.finfo(float).max)
    assert np.isclose(np.linalg.norm(tilted_ray), 1.0, rtol=1e-12, atol=1e-12)
    with pytest.raises(ValueError, match="overflowed"):
        scale_nbi_velocity_for_energy_component(tilted_ray, max_finite, 1)
    # a strictly unit ray with the max finite speed stays finite
    result = scale_nbi_velocity_for_energy_component(
        np.array([1.0, 0.0, 0.0]), max_finite, 1)
    assert np.all(np.isfinite(result))
    assert result[0] == max_finite


def test_initial_state_materialization_matches_the_source_formula():
    out = materialize_nbi_component_initial_state(
        injected_power_mw=1.0, injection_energy_kev=50.0,
        current_fractions=np.array([0.6, 0.3, 0.1]),
        beam_grid_cell_volume_cm3=1.0e-6, energy_component=2, nlevels=6)
    expected_factor = 0.6 / 1.0 + 0.3 / 2.0 + 0.1 / 3.0
    assert out["energy_weight_factor"] == expected_factor
    expected_rate = 1.0e6 * 1.0 / (1.0e3 * 50.0 * 1.60217733e-19 * expected_factor)
    assert out["total_neutral_rate_s_inv"] == expected_rate
    assert out["component_neutral_rate_s_inv"] == expected_rate * 0.3
    states = out["initial_state_rate_per_volume_cm_inv3_s_inv"]
    assert states.shape == (6,)
    assert states[0] == expected_rate * 0.3 / 1.0e-6
    assert np.all(states[1:] == 0.0)
    assert out["nlevels"] == 6 and out["initial_state_index_one_based"] == 1
    assert out["energy_component"] == 2 and out["energy_component_name"] == "half"


def test_initial_state_rejects_bad_levels_components_and_extremes():
    good = dict(injected_power_mw=1.0, injection_energy_kev=50.0,
                current_fractions=np.array([0.6, 0.3, 0.1]),
                beam_grid_cell_volume_cm3=1.0e-6)
    for bad in (
        dict(good, energy_component=2, nlevels=3),
        dict(good, energy_component=2, nlevels=True),
        dict(good, energy_component=True, nlevels=6),
        dict(good, energy_component=1.0, nlevels=6),
        dict(good, energy_component=4, nlevels=6),
        dict(good, energy_component=2, nlevels=6, injected_power_mw=np.nan),
        dict(good, energy_component=2, nlevels=6, injection_energy_kev=0.0),
        dict(good, energy_component=2, nlevels=6,
             current_fractions=np.array([0.0, 0.0, 0.0])),
        dict(good, energy_component=2, nlevels=6,
             current_fractions=np.array([0.6, 0.3, 0.1]) * -1.0),
        # recorded overflow chains: (a) huge power overflows the total rate;
        # (b) a finite rate times a tiny volume overflows the per-cell source-rate-per-volume value
        # even though the rate itself stays finite -- the source-rate-per-volume gate catches
        # what the rate gate misses
        dict(good, energy_component=2, nlevels=6,
             injected_power_mw=1e308, beam_grid_cell_volume_cm3=1e-300),
        dict(good, energy_component=2, nlevels=6,
             injected_power_mw=1e300, beam_grid_cell_volume_cm3=1e-308),
        # recorded weight-factor overflow: three finite max-float fractions
        # overflow the weight sum to Inf (the saved arm returns rate 0 with
        # an Inf factor); the factor gate rejects before the rate division
        dict(good, energy_component=1, nlevels=6,
             current_fractions=np.array([np.finfo(float).max] * 3)),
    ):
        with pytest.raises(ValueError):
            materialize_nbi_component_initial_state(**bad)


def test_halo_sampling_is_deterministic_in_caller_owned_draws():
    rng = np.random.default_rng(91)
    rotation = np.array([1.0e5, 0.0, -2.0e5])
    draw = rng.standard_normal(3)
    out = sample_halo_velocity(
        plasma_rotation_cm_s=rotation, ion_temperature_kev=10.0,
        ion_mass_amu=2.0, velocity_squared_to_kev_per_amu=0.01,
        standard_normal_draw=draw)
    expected_thermal = np.sqrt(10.0 * 0.5 / (0.01 * 2.0))
    assert out["thermal_speed_cm_s"] == expected_thermal
    np.testing.assert_array_equal(out["halo_velocity_cm_s"],
                                  rotation + expected_thermal * draw)
    # identical draws give identical outputs (caller-owned randomness)
    again = sample_halo_velocity(
        plasma_rotation_cm_s=rotation, ion_temperature_kev=10.0,
        ion_mass_amu=2.0, velocity_squared_to_kev_per_amu=0.01,
        standard_normal_draw=draw)
    np.testing.assert_array_equal(again["halo_velocity_cm_s"],
                                  out["halo_velocity_cm_s"])
    # zero temperature collapses onto the rotation velocity
    cold = sample_halo_velocity(
        plasma_rotation_cm_s=rotation, ion_temperature_kev=0.0,
        ion_mass_amu=2.0, velocity_squared_to_kev_per_amu=0.01,
        standard_normal_draw=draw)
    np.testing.assert_array_equal(cold["halo_velocity_cm_s"], rotation)


def test_halo_sampling_rejects_bad_inputs_and_extremes():
    draw = np.zeros(3)
    for bad in (
        dict(plasma_rotation_cm_s=[np.nan, 0, 0], ion_temperature_kev=10.0,
             ion_mass_amu=2.0, velocity_squared_to_kev_per_amu=0.01,
             standard_normal_draw=draw),
        dict(plasma_rotation_cm_s=[0, 0, 0], ion_temperature_kev=-1.0,
             ion_mass_amu=2.0, velocity_squared_to_kev_per_amu=0.01,
             standard_normal_draw=draw),
        dict(plasma_rotation_cm_s=[0, 0, 0], ion_temperature_kev=10.0,
             ion_mass_amu=0.0, velocity_squared_to_kev_per_amu=0.01,
             standard_normal_draw=draw),
        dict(plasma_rotation_cm_s=[0, 0, 0], ion_temperature_kev=10.0,
             ion_mass_amu=2.0, velocity_squared_to_kev_per_amu=0.0,
             standard_normal_draw=draw),
        dict(plasma_rotation_cm_s=[0, 0, 0], ion_temperature_kev=10.0,
             ion_mass_amu=2.0, velocity_squared_to_kev_per_amu=0.01,
             standard_normal_draw=[np.inf, 0, 0]),
        dict(plasma_rotation_cm_s=[0, 0, 0], ion_temperature_kev=10.0,
             ion_mass_amu=2.0, velocity_squared_to_kev_per_amu=0.01,
             standard_normal_draw=[0, 0]),
    ):
        with pytest.raises(ValueError):
            sample_halo_velocity(**bad)
    # recorded overflow chain: a huge thermal speed (tiny mass/conversion
    # denominator with high temperature) times an extreme draw overflows the
    # velocity sum
    with pytest.raises(ValueError, match="overflowed"):
        sample_halo_velocity(
            plasma_rotation_cm_s=[0.0, 0.0, 0.0], ion_temperature_kev=1e300,
            ion_mass_amu=1e-160, velocity_squared_to_kev_per_amu=1e-160,
            standard_normal_draw=[1e200, 0.0, 0.0])
    # recorded contract normalization: a denominator underflowing to exactly
    # 0.0 makes the saved arm raise a bare ZeroDivisionError; the SciRel
    # failure contract converts it to the common ValueError
    with pytest.raises(ValueError, match="underflowed"):
        sample_halo_velocity(
            plasma_rotation_cm_s=[0.0, 0.0, 0.0], ion_temperature_kev=1.0,
            ion_mass_amu=1e-300, velocity_squared_to_kev_per_amu=1e-300,
            standard_normal_draw=[0.0, 0.0, 0.0])


def test_beam_grid_cell_sampling_is_the_zero_mean_affine_map():
    center = np.array([10.0, -20.0, 30.0])
    width = np.array([2.0, 4.0, 6.0])
    rng = np.random.default_rng(92)
    u = rng.uniform(0.0, 1.0, 3)
    result = sample_beam_grid_cell(cell_center_cm=center,
                                   cell_width_cm=width, uniform_draws=u)
    np.testing.assert_array_equal(result, center + width * (u - 0.5))
    # u = 0.5 maps exactly to the center on every axis
    mid = sample_beam_grid_cell(cell_center_cm=center, cell_width_cm=width,
                                uniform_draws=np.array([0.5, 0.5, 0.5]))
    np.testing.assert_array_equal(mid, center)
    # zero width keeps the center coordinate
    thin = sample_beam_grid_cell(cell_center_cm=center,
                                 cell_width_cm=np.zeros(3),
                                 uniform_draws=u)
    np.testing.assert_array_equal(thin, center)
    for bad in (
        dict(cell_center_cm=center, cell_width_cm=width,
             uniform_draws=np.array([1.0, 0.5, 0.5])),
        dict(cell_center_cm=center, cell_width_cm=width,
             uniform_draws=np.array([-0.1, 0.5, 0.5])),
        dict(cell_center_cm=np.array([np.nan, 0, 0]), cell_width_cm=width,
             uniform_draws=u),
        dict(cell_center_cm=center, cell_width_cm=np.array([-1.0, 0, 0]),
             uniform_draws=u),
        dict(cell_center_cm=center, cell_width_cm=width,
             uniform_draws=np.array([0.5, 0.5])),
    ):
        with pytest.raises(ValueError):
            sample_beam_grid_cell(**bad)
    # recorded overflow chain: center near the float ceiling plus a wide cell
    # and a draw above the midpoint overflows the affine sum
    with pytest.raises(ValueError, match="overflowed"):
        sample_beam_grid_cell(cell_center_cm=np.array([1.5e308, 0.0, 0.0]),
                              cell_width_cm=np.array([1e308, 0.0, 0.0]),
                              uniform_draws=np.array([1.0 - 1e-16, 0.5, 0.5]))


def test_pitch_gyro_direction_is_orthonormal_frame_decomposition():
    a, b, c = _orthonormal_frame()
    rng = np.random.default_rng(93)
    # any orthonormal frame: the dot(direction, b_unit) identity is exact
    # because b_unit is unit-norm, independent of frame orientation
    for _ in range(5):
        frame = np.linalg.qr(rng.normal(size=(3, 3)))[0].T
        pitch = float(rng.uniform(-0.9, 0.9))
        angle = float(rng.uniform(-np.pi, np.pi))
        direction = pitch_gyro_to_velocity_direction(
            pitch=pitch, gyroangle_rad=angle,
            a_unit=frame[0], b_unit=frame[1], c_unit=frame[2])
        assert direction.shape == (3,)
        np.testing.assert_allclose(np.linalg.norm(direction), 1.0, rtol=0, atol=1e-15)
        assert float(np.dot(direction, frame[1])) == pytest.approx(pitch, abs=1e-15)
    # canonical frame: the closed form is checked component-exactly
    for pitch, angle in ((0.0, 0.0), (0.5, np.pi / 3), (-0.5, -np.pi / 3),
                         (1.0, 2.0), (-1.0, 2.0)):
        direction = pitch_gyro_to_velocity_direction(
            pitch=pitch, gyroangle_rad=angle, a_unit=a, b_unit=b, c_unit=c)
        expected = (np.sqrt(1.0 - pitch ** 2) * np.cos(angle) * a + pitch * b
                    + np.sqrt(1.0 - pitch ** 2) * np.sin(angle) * c)
        np.testing.assert_array_equal(direction, expected)
    # pitch = +-1 fixes the direction on the b axis regardless of gyro angle
    plus = pitch_gyro_to_velocity_direction(pitch=1.0, gyroangle_rad=0.7,
                                            a_unit=a, b_unit=b, c_unit=c)
    minus = pitch_gyro_to_velocity_direction(pitch=-1.0, gyroangle_rad=0.7,
                                             a_unit=a, b_unit=b, c_unit=c)
    np.testing.assert_allclose(plus, b, atol=1e-15)
    np.testing.assert_allclose(minus, -b, atol=1e-15)


def test_pitch_gyro_direction_rejects_bad_frames_and_domains():
    a, b, c = _orthonormal_frame()
    for bad in (
        dict(pitch=1.5, gyroangle_rad=0.0, a_unit=a, b_unit=b, c_unit=c),
        dict(pitch=np.nan, gyroangle_rad=0.0, a_unit=a, b_unit=b, c_unit=c),
        dict(pitch=0.0, gyroangle_rad=np.nan, a_unit=a, b_unit=b, c_unit=c),
        dict(pitch=0.0, gyroangle_rad=0.0,
             a_unit=np.array([2.0, 0.0, 0.0]), b_unit=b, c_unit=c),
        # c not unit
        dict(pitch=0.0, gyroangle_rad=0.0,
             a_unit=a, b_unit=b, c_unit=np.array([0.0, 0.0, 2.0])),
        # b and c not orthogonal
        dict(pitch=0.0, gyroangle_rad=0.0,
             a_unit=a, b_unit=b, c_unit=np.array([0.0, 1.0, 1.0]) / np.sqrt(2.0)),
    ):
        with pytest.raises(ValueError):
            pitch_gyro_to_velocity_direction(**bad)
