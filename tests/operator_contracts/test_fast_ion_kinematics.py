"""Direct contract tests for the r70 fast-ion kinematics family:
``dd_neutron_kinematic_anisotropy`` and
``first_order_larmor_guiding_center_correction`` (FIDASIM sources).

The integrated ``scirel.fusion.dd-neutron-lab-energy`` asset already covers
the D-D neutron lab-energy relation (same FIDASIM source); this batch adds
the anisotropy factor and the FLR correction only, and the DD-energy asset
serves here as a cross-reference arm.  Fixture random sources are freshly
seeded per call so single affected-test runs see byte-identical carriers to
the whole-file run.
"""
from __future__ import annotations

import numpy as np
import pytest

from scirel.fusion import (
    dd_neutron_kinematic_anisotropy,
    first_order_larmor_guiding_center_correction,
    calculate_dd_neutron_lab_energy_kev,
)


def test_anisotropy_matches_the_saved_frozen_probe_value():
    """The saved package's own forward probe (exact to rtol 1e-14)."""
    kappa = dd_neutron_kinematic_anisotropy(
        ion_velocity_cm_s=[2e8, 0, 0],
        neutron_velocity_cm_s=[1, 0, 0],
        plasma_rotation_cm_s=[0, 0, 0],
        velocity_squared_to_kev_per_amu=1e-15)
    assert np.isclose(kappa, 1.3312066426953741, rtol=1e-14, atol=0.0)


def test_anisotropy_is_finite_and_positive_inside_the_table_domain():
    """The declared table domain bounds the ion source energy: the general
    condition is 0.5*scale*|v1 - vrot|^2 < 116.909 keV; with the test scale
    0.01 keV/(cm/s)^2 this bounds |v1 - vrot| below about 153 cm/s.  Random
    in-domain fixtures must return finite positive factors."""
    rng = np.random.default_rng(80)
    for _ in range(20):
        v1 = rng.uniform(-100.0, 100.0, 3)
        vrot = rng.uniform(-10.0, 10.0, 3)
        kappa = dd_neutron_kinematic_anisotropy(
            ion_velocity_cm_s=v1,
            neutron_velocity_cm_s=rng.uniform(-1e9, 1e9, 3),
            plasma_rotation_cm_s=vrot,
            velocity_squared_to_kev_per_amu=0.01)
        assert np.isfinite(kappa) and kappa > 0.0


def test_anisotropy_symmetry_in_the_transverse_direction():
    """The emission anisotropy depends on the emission angle only; rotating
    the neutron direction about the ion-velocity axis by 90 degrees swaps
    cos^2/cos^4 through the same angle, so the mirrored pair must agree."""
    base = dict(ion_velocity_cm_s=[5.0, 0, 0],
                plasma_rotation_cm_s=[0, 0, 0],
                velocity_squared_to_kev_per_amu=0.01)
    kappa_a = dd_neutron_kinematic_anisotropy(
        neutron_velocity_cm_s=[0, 1.0, 0], **base)
    kappa_b = dd_neutron_kinematic_anisotropy(
        neutron_velocity_cm_s=[0, 0, 1.0], **base)
    assert kappa_a == pytest.approx(kappa_b, rel=1e-12)


def test_anisotropy_rejects_upper_table_boundary_and_bad_inputs():
    # saved package's own boundary: the canonical probe at the table top is
    # rejected (vrel = 200 cm/s at scale .01 -> ehalf = 200 keV > 116.909)
    with pytest.raises(ValueError, match="upper-table"):
        dd_neutron_kinematic_anisotropy(
            ion_velocity_cm_s=[100, 0, 0],
            neutron_velocity_cm_s=[0, 1, 0],
            plasma_rotation_cm_s=[-100, 0, 0],
            velocity_squared_to_kev_per_amu=.01)
    for kwargs in (
        dict(ion_velocity_cm_s=[np.nan, 0, 0], neutron_velocity_cm_s=[0, 1, 0],
             plasma_rotation_cm_s=[0, 0, 0], velocity_squared_to_kev_per_amu=0.01),
        dict(ion_velocity_cm_s=[10, 0], neutron_velocity_cm_s=[0, 1, 0],
             plasma_rotation_cm_s=[0, 0, 0], velocity_squared_to_kev_per_amu=0.01),
        dict(ion_velocity_cm_s=[2e8, 0, 0], neutron_velocity_cm_s=[1, 0, 0],
             plasma_rotation_cm_s=[0, 0, 0], velocity_squared_to_kev_per_amu=0.0),
        dict(ion_velocity_cm_s=[2e8, 0, 0], neutron_velocity_cm_s=[1, 0, 0],
             plasma_rotation_cm_s=[0, 0, 0], velocity_squared_to_kev_per_amu=np.nan),
        # extreme ion velocity overflows the source energy: upper-table reject
        dict(ion_velocity_cm_s=[1e200, 0, 0], neutron_velocity_cm_s=[1, 0, 0],
             plasma_rotation_cm_s=[0, 0, 0], velocity_squared_to_kev_per_amu=0.01),
    ):
        with pytest.raises(ValueError):
            dd_neutron_kinematic_anisotropy(**kwargs)


def test_anisotropy_extreme_norm_overflow_is_contained_by_documented_fallback():
    """Extreme neutron velocities overflow the vector norms, but the angle
    algebra's own fallback (`abs(k0*sinphi) <= 1` false for NaN) forces
    costheta to 0 and the anisotropy stays finite.  This is documented
    source behavior, verified here on the extreme probes; the non-finite
    output gate guards any remaining combination."""
    for v3 in ([1e308, 0, 0], [0, 1e308, 0], [1e200, 1e200, 0]):
        kappa = dd_neutron_kinematic_anisotropy(
            ion_velocity_cm_s=[1.0, 0, 0],
            neutron_velocity_cm_s=v3,
            plasma_rotation_cm_s=[0, 0, 0],
            velocity_squared_to_kev_per_amu=1e-15)
        assert np.isfinite(kappa)
        assert kappa == pytest.approx(1.0, rel=1e-12)


def _flr_inputs():
    rng = np.random.default_rng(81)
    b_unit = np.array([0.0, 0.0, 1.0])
    velocity = np.array([1e7, 0.0, 0.0])
    position = np.array([10.0, 20.0, 30.0])
    return position, velocity, b_unit, rng


def test_flr_order0_is_identity():
    position, velocity, b_unit, _ = _flr_inputs()
    out = first_order_larmor_guiding_center_correction(
        guiding_center_position_cm=position, ion_velocity_cm_s=velocity,
        magnetic_unit_vector=b_unit, magnetic_magnitude_t=2.0,
        ion_mass_amu=2.0, flr_order=0)
    np.testing.assert_array_equal(out["particle_position_cm"], position)
    np.testing.assert_array_equal(out["gyro_radius_vector_cm"], np.zeros(3))
    assert out["gyro_scale_factor"] == 1.0


def test_flr_order1_gyro_radius_is_perpendicular_to_b_and_matches_cross_product():
    position, velocity, b_unit, _ = _flr_inputs()
    out = first_order_larmor_guiding_center_correction(
        guiding_center_position_cm=position, ion_velocity_cm_s=velocity,
        magnetic_unit_vector=b_unit, magnetic_magnitude_t=2.0,
        ion_mass_amu=2.0, flr_order=1)
    expected_radius = np.cross(velocity, b_unit) * (2.0 * 1.660539040e-27 / (2.0 * 1.60217733e-19))
    np.testing.assert_array_equal(out["gyro_radius_vector_cm"], expected_radius)
    np.testing.assert_array_equal(out["particle_position_cm"], position - expected_radius)
    assert out["gyro_scale_factor"] == 1.0
    assert np.dot(out["gyro_radius_vector_cm"], b_unit) == pytest.approx(0.0, abs=1e-30)
    # flr_enabled default reproduces the historical order-1 contract
    out_default = first_order_larmor_guiding_center_correction(
        guiding_center_position_cm=position, ion_velocity_cm_s=velocity,
        magnetic_unit_vector=b_unit, magnetic_magnitude_t=2.0, ion_mass_amu=2.0)
    np.testing.assert_array_equal(out_default["gyro_radius_vector_cm"],
                                  out["gyro_radius_vector_cm"])


def test_flr_order2_scale_keeps_the_position_on_the_gyro_circle():
    position, velocity, b_unit, _ = _flr_inputs()
    machine_position = np.array([30.0, 40.0, 0.0])
    matrix = np.eye(3)
    state = {name: 0.1 * index for index, name in enumerate(
        ("br_t", "bt_t", "bz_t", "dbr_dr_t_cm", "dbr_dphi_t_rad", "dbr_dz_t_cm",
         "dbt_dr_t_cm", "dbt_dphi_t_rad", "dbt_dz_t_cm", "dbz_dr_t_cm",
         "dbz_dphi_t_rad", "dbz_dz_t_cm"))}
    out2 = first_order_larmor_guiding_center_correction(
        guiding_center_position_cm=position, ion_velocity_cm_s=velocity,
        magnetic_unit_vector=b_unit, magnetic_magnitude_t=2.0, ion_mass_amu=2.0,
        flr_order=2,
        guiding_center_machine_position_cm=machine_position,
        coordinate_to_machine_matrix=matrix,
        cylindrical_magnetic_state=state)
    out1 = first_order_larmor_guiding_center_correction(
        guiding_center_position_cm=position, ion_velocity_cm_s=velocity,
        magnetic_unit_vector=b_unit, magnetic_magnitude_t=2.0, ion_mass_amu=2.0,
        flr_order=1)
    # uniform magnetic field (all derivatives zero) must give scale exactly 1
    zero_state = {name: 0.0 for name in state}
    zero_state["bz_t"] = 2.0
    out2_uniform = first_order_larmor_guiding_center_correction(
        guiding_center_position_cm=position, ion_velocity_cm_s=velocity,
        magnetic_unit_vector=b_unit, magnetic_magnitude_t=2.0, ion_mass_amu=2.0,
        flr_order=2,
        guiding_center_machine_position_cm=machine_position,
        coordinate_to_machine_matrix=matrix,
        cylindrical_magnetic_state=zero_state)
    assert out2_uniform["gyro_scale_factor"] == 1.0
    np.testing.assert_array_equal(out2_uniform["gyro_radius_vector_cm"],
                                  out1["gyro_radius_vector_cm"])
    # the non-uniform state moves the result but keeps it finite and scaled
    assert 0.0 < out2["gyro_scale_factor"] < 2.0
    assert np.all(np.isfinite(out2["particle_position_cm"]))


def test_flr_rejects_scale_outside_source_window_and_bad_geometry():
    position, velocity, b_unit, _ = _flr_inputs()
    machine_position = np.array([30.0, 40.0, 0.0])
    matrix = np.eye(3)
    # a huge magnetic-field gradient drives the scale outside (0, 2)
    big_state = {name: 0.0 for name in (
        "br_t", "bt_t", "bz_t", "dbr_dr_t_cm", "dbr_dphi_t_rad", "dbr_dz_t_cm",
        "dbt_dr_t_cm", "dbt_dphi_t_rad", "dbt_dz_t_cm", "dbz_dr_t_cm",
        "dbz_dphi_t_rad", "dbz_dz_t_cm")}
    big_state["bz_t"] = 2.0
    big_state["dbz_dr_t_cm"] = 1e12
    with pytest.raises(ValueError, match="outside \\(0,2\\)"):
        first_order_larmor_guiding_center_correction(
            guiding_center_position_cm=position, ion_velocity_cm_s=velocity,
            magnetic_unit_vector=b_unit, magnetic_magnitude_t=2.0,
            ion_mass_amu=2.0, flr_order=2,
            guiding_center_machine_position_cm=machine_position,
            coordinate_to_machine_matrix=matrix,
            cylindrical_magnetic_state=big_state)
    # flr_order=2 on the cylindrical axis is undefined
    with pytest.raises(ValueError, match="cylindrical axis"):
        first_order_larmor_guiding_center_correction(
            guiding_center_position_cm=position, ion_velocity_cm_s=velocity,
            magnetic_unit_vector=b_unit, magnetic_magnitude_t=2.0,
            ion_mass_amu=2.0, flr_order=2,
            guiding_center_machine_position_cm=np.array([0.0, 0.0, 0.0]),
            coordinate_to_machine_matrix=matrix,
            cylindrical_magnetic_state=big_state)
    # the recorded overflow chain: finite radius (about -1.04e308 in x) plus
    # finite position 1e308 overflows the subtraction; the final field check
    # must reject it instead of returning Inf
    with pytest.raises(ValueError, match="non-finite"):
        first_order_larmor_guiding_center_correction(
            guiding_center_position_cm=np.array([1e308, 0.0, 0.0]),
            ion_velocity_cm_s=np.array([0.0, -1e308, 0.0]),
            magnetic_unit_vector=np.array([0.0, 0.0, 1.0]),
            magnetic_magnitude_t=1e-8, ion_mass_amu=1.0)
    # missing cylindrical state keys
    with pytest.raises(ValueError, match="missing"):
        first_order_larmor_guiding_center_correction(
            guiding_center_position_cm=position, ion_velocity_cm_s=velocity,
            magnetic_unit_vector=b_unit, magnetic_magnitude_t=2.0,
            ion_mass_amu=2.0, flr_order=2,
            guiding_center_machine_position_cm=machine_position,
            coordinate_to_machine_matrix=matrix,
            cylindrical_magnetic_state={"br_t": 0.0})
    # non-unit b, bad order, non-positive B/mass
    with pytest.raises(ValueError):
        first_order_larmor_guiding_center_correction(
            guiding_center_position_cm=position, ion_velocity_cm_s=velocity,
            magnetic_unit_vector=np.array([0.0, 0.0, 2.0]),
            magnetic_magnitude_t=2.0, ion_mass_amu=2.0)
    with pytest.raises(ValueError):
        first_order_larmor_guiding_center_correction(
            guiding_center_position_cm=position, ion_velocity_cm_s=velocity,
            magnetic_unit_vector=b_unit, magnetic_magnitude_t=2.0,
            ion_mass_amu=2.0, flr_order=3)
    with pytest.raises(ValueError):
        first_order_larmor_guiding_center_correction(
            guiding_center_position_cm=position, ion_velocity_cm_s=velocity,
            magnetic_unit_vector=b_unit, magnetic_magnitude_t=0.0,
            ion_mass_amu=2.0)


def test_dd_energy_asset_remains_the_referenced_lab_energy_relation():
    """The D-D lab-energy relation stays on the integrated asset (registered
    reuse; its return is a plain keV float, not a mapping)."""
    energy = calculate_dd_neutron_lab_energy_kev(
        reactant1_velocity_cm_s=np.array([1e8, 0.0, 0.0]),
        reactant2_velocity_cm_s=np.array([-1e8, 0.0, 0.0]),
        detector_unit_vector=np.array([0.0, 0.0, 1.0]))
    assert isinstance(energy, float)
    assert np.isfinite(energy) and energy > 0.0
