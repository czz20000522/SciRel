import numpy as np

from scirel.mirror.mirror_invariant_distribution import (
    evaluate_mirror_invariant_distribution,
    evaluate_mirror_invariant_distribution as scientific_function,
)


E, M = 1.602176634e-19, 1.67262192595e-27


def _call(vpar, vperp, B, phi):
    return scientific_function(vpar, vperp, B, 0.0, phi, M, E, 2e18, 1200 * E, 2400 * E, 1.0)


def test_distribution_is_invariant_at_equal_energy_and_magnetic_moment():
    mu, energy = 900 * E, 5000 * E
    b1, b2, phi1, phi2 = 1.0, 2.0, 0.0, 200.0
    vperp1, vperp2 = np.sqrt(2 * mu * b1 / M), np.sqrt(2 * mu * b2 / M)
    vpar1 = np.sqrt(2 * (energy - mu * b1 - E * phi1) / M)
    vpar2 = np.sqrt(2 * (energy - mu * b2 - E * phi2) / M)
    np.testing.assert_allclose(
        _call(vpar1, vperp1, b1, phi1)["f0_s3_m6"],
        _call(vpar2, vperp2, b2, phi2)["f0_s3_m6"],
        rtol=2e-14,
    )


def test_loss_cone_marks_unconfined_particle_with_refill():
    result = scientific_function(
        2e6,
        1e5,
        1.0,
        0.0,
        0.0,
        M,
        E,
        2e18,
        1200 * E,
        2400 * E,
        1.0,
        b_plug_left_t=4.0,
        b_plug_right_t=5.0,
        phi_plug_left_v=800.0,
        phi_plug_right_v=1000.0,
        loss_cone_refill=0.1,
    )
    assert result["occupation"] in {0.1, 1.0}


def test_plugged_default_is_the_source_empty_loss_cone_default():
    kwargs = dict(
        b_plug_left_t=4.0, b_plug_right_t=5.0, phi_plug_left_v=800.0, phi_plug_right_v=1000.0
    )
    default = scientific_function(
        2e6, 1e5, 1.0, 0.0, 0.0, M, E, 2e18, 1200 * E, 2400 * E, 1.0, **kwargs
    )
    explicit = scientific_function(
        2e6, 1e5, 1.0, 0.0, 0.0, M, E, 2e18, 1200 * E, 2400 * E, 1.0, loss_cone_refill=0.0, **kwargs
    )
    assert default["occupation"] == explicit["occupation"] == 0.0


def test_reference_profiles_are_evaluated_at_psi():
    psi = np.array([0.0, 0.5])
    profiled = scientific_function(
        np.ones(2),
        np.ones(2),
        np.ones(2),
        psi,
        0.0,
        M,
        E,
        lambda x: 2e18 * (1 + x),
        1200 * E,
        2400 * E,
        1.0,
    )
    explicit = scientific_function(
        np.ones(2),
        np.ones(2),
        np.ones(2),
        psi,
        0.0,
        M,
        E,
        2e18 * (1 + psi),
        1200 * E,
        2400 * E,
        1.0,
    )
    np.testing.assert_allclose(profiled["f0_s3_m6"], explicit["f0_s3_m6"])


def test_reviewed_relation_example():
    import math
    import numpy as np

    ELEMENTARY_CHARGE = 1.602176634e-19
    PROTON_MASS = 1.67262192595e-27
    v_parallel = 2.0e6
    v_perpendicular = 1.0e5
    result = evaluate_mirror_invariant_distribution(
        v_parallel,
        v_perpendicular,
        1.0,
        0.0,
        0.0,
        PROTON_MASS,
        ELEMENTARY_CHARGE,
        2.0e18,
        1200.0 * ELEMENTARY_CHARGE,
        2400.0 * ELEMENTARY_CHARGE,
        1.0,
        b_plug_left_t=4.0,
        b_plug_right_t=5.0,
        phi_plug_left_v=800.0,
        phi_plug_right_v=1000.0,
        loss_cone_refill=0.1,
    )
    expected_mu = PROTON_MASS * v_perpendicular**2 / 2.0
    expected_energy = 0.5 * PROTON_MASS * v_parallel**2 + expected_mu
    temperature_parallel = 1200.0 * ELEMENTARY_CHARGE
    temperature_perpendicular = 2400.0 * ELEMENTARY_CHARGE
    exponent = -(
        (expected_energy - ELEMENTARY_CHARGE * 0.0) / temperature_parallel
        + expected_mu * 1.0 * (1.0 / temperature_perpendicular - 1.0 / temperature_parallel)
    )
    normalization = (
        2.0e18
        * (PROTON_MASS / (2.0 * math.pi)) ** 1.5
        / (temperature_perpendicular * math.sqrt(temperature_parallel))
    )
    expected_f0 = normalization * math.exp(np.clip(exponent, -745.0, 700.0)) * 0.1
    assert np.allclose(result["magnetic_moment_j_t"], expected_mu)
    assert np.allclose(result["energy_j"], expected_energy)
    assert float(result["occupation"]) == 0.1
    assert np.allclose(result["f0_s3_m6"], expected_f0)
    reversed_velocity = evaluate_mirror_invariant_distribution(
        -v_parallel,
        -v_perpendicular,
        1.0,
        0.0,
        0.0,
        PROTON_MASS,
        ELEMENTARY_CHARGE,
        2.0e18,
        1200.0 * ELEMENTARY_CHARGE,
        2400.0 * ELEMENTARY_CHARGE,
        1.0,
    )
    unplugged = evaluate_mirror_invariant_distribution(
        v_parallel,
        v_perpendicular,
        1.0,
        0.0,
        0.0,
        PROTON_MASS,
        ELEMENTARY_CHARGE,
        2.0e18,
        1200.0 * ELEMENTARY_CHARGE,
        2400.0 * ELEMENTARY_CHARGE,
        1.0,
    )
    assert np.allclose(reversed_velocity["f0_s3_m6"], unplugged["f0_s3_m6"])


def test_contract_rejects_nonfinite_mass_and_charge():
    import pytest

    base = dict(
        v_parallel_m_s=1.0e5,
        v_perpendicular_m_s=2.0e5,
        b_t=1.0,
        psi=0.0,
        potential_v=0.0,
        mass_kg=M,
        charge_c=E,
        density_ref_m3=1.0e18,
        temperature_parallel_j=1200.0 * E,
        temperature_perpendicular_ref_j=2400.0 * E,
        b_ref_t=1.0,
    )
    with pytest.raises(ValueError, match="mass_kg"):
        scientific_function(**{**base, "mass_kg": np.nan})
    with pytest.raises(ValueError, match="charge_c"):
        scientific_function(**{**base, "charge_c": np.nan})
