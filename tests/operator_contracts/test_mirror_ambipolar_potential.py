# 覆盖：端损失电流平衡、零密度、空损失锥拒绝、指定端势和 caller profile(psi) 等价。
import numpy as np
import pytest

from scirel.closures.mirror_ambipolar_potential import ELEMENTARY_CHARGE_C, solve_mirror_ambipolar_potential, solve_mirror_ambipolar_potential as scientific_operator


PROTON_MASS_KG = 1.67262192595e-27


def test_balances_end_loss_current_on_every_flux_surface():
    psi = np.linspace(0.0, 0.1, 5)
    result = scientific_operator(
        np.ones_like(psi),
        np.full_like(psi, 4.0),
        psi,
        PROTON_MASS_KG,
        ELEMENTARY_CHARGE_C,
        2.0e18,
        1000.0 * ELEMENTARY_CHARGE_C,
        2000.0 * ELEMENTARY_CHARGE_C,
        500.0 * ELEMENTARY_CHARGE_C,
        ion_loss_refill=0.05,
        potential_tolerance_v=1.0e-8,
    )
    assert result["converged"]
    assert np.all(result["potential_v"] < 0.0)
    assert np.max(np.abs(result["relative_current_residual"])) < 1.0e-9


def test_zero_density_surfaces_return_the_reference_potential():
    result = scientific_operator(
        1.0,
        3.0,
        np.array([0.0, 1.0]),
        PROTON_MASS_KG,
        ELEMENTARY_CHARGE_C,
        np.array([0.0, 2.0e18]),
        1000.0 * ELEMENTARY_CHARGE_C,
        2000.0 * ELEMENTARY_CHARGE_C,
        500.0 * ELEMENTARY_CHARGE_C,
        phi_reference_v=17.0,
        ion_loss_refill=0.05,
    )
    assert result["potential_v"][0] == 17.0
    assert result["relative_current_residual"][0] == 0.0


def test_rejects_an_empty_ion_loss_cone_for_ambipolar_solution():
    with pytest.raises(ValueError, match="ion_loss_refill"):
        scientific_operator(
            1.0, 3.0, 0.0, PROTON_MASS_KG, ELEMENTARY_CHARGE_C,
            2.0e18, 1000.0 * ELEMENTARY_CHARGE_C,
            2000.0 * ELEMENTARY_CHARGE_C, 500.0 * ELEMENTARY_CHARGE_C,
            ion_loss_refill=0.0,
        )


def test_prescribed_potential_evaluates_flux_without_solving():
    result = scientific_operator(
        np.ones(2), np.full(2, 4.0), np.array([0.0, 0.1]),
        PROTON_MASS_KG, ELEMENTARY_CHARGE_C, 2.0e18,
        1000.0 * ELEMENTARY_CHARGE_C, 2000.0 * ELEMENTARY_CHARGE_C,
        500.0 * ELEMENTARY_CHARGE_C, mode="evaluate", phi_plug_v=-1000.0,
    )
    assert result["iterations"] == 0 and result["converged"]
    assert np.all(result["ion_particle_flux_m2_s"] > 0.0)


def test_vectorized_density_profile_matches_explicit_values():
    psi = np.array([0.0, 0.1, 0.2])
    density = lambda value: 2.0e18 * (1.0 - 0.2 * value)
    callable_result = scientific_operator(
        np.ones(3), np.full(3, 4.0), psi, PROTON_MASS_KG, ELEMENTARY_CHARGE_C,
        density, 1000.0 * ELEMENTARY_CHARGE_C, 2000.0 * ELEMENTARY_CHARGE_C,
        500.0 * ELEMENTARY_CHARGE_C, mode="evaluate", phi_plug_v=-1000.0,
    )
    array_result = scientific_operator(
        np.ones(3), np.full(3, 4.0), psi, PROTON_MASS_KG, ELEMENTARY_CHARGE_C,
        density(psi), 1000.0 * ELEMENTARY_CHARGE_C, 2000.0 * ELEMENTARY_CHARGE_C,
        500.0 * ELEMENTARY_CHARGE_C, mode="evaluate", phi_plug_v=-1000.0,
    )
    np.testing.assert_allclose(callable_result["ion_particle_flux_m2_s"], array_result["ion_particle_flux_m2_s"])


def test_reviewed_relation_example():
    from scirel.closures.mirror_ambipolar_potential import solve_mirror_ambipolar_potential
    import numpy as np

    e = 1.602176634e-19
    m_e = 9.1093837139e-31
    m_i = 1.67262192595e-27

    # B_p=B_r 时 s=0。正离子在 phi_p-phi_r=1 V 上取 I_i=exp(-1/2)，
    # 电子取 I_e=1；这给出不依赖求根器的分段俯仰积分 oracle。
    evaluated = solve_mirror_ambipolar_potential(
        1.0, 1.0, 0.0, m_i, e, 2.0e18, 2.0 * e, 3.0 * e, e,
        electron_density_ref_m3=3.0e18,
        ion_loss_refill=0.25,
        electron_loss_refill=0.5,
        mode="evaluate",
        phi_plug_v=1.0,
    )
    expected_ion = 2.0e18 * np.sqrt((2.0 * e) / (2.0 * np.pi * m_i)) * np.exp(-0.5) * 0.25
    expected_electron = 3.0e18 * np.sqrt(e / (2.0 * np.pi * m_e)) * 0.5
    np.testing.assert_allclose(evaluated["ion_particle_flux_m2_s"], expected_ion)
    np.testing.assert_allclose(evaluated["electron_particle_flux_m2_s"], expected_electron)
    assert evaluated["iterations"] == 0 and evaluated["converged"]

    # 很窄的初始括区会被扩展；零密度表面保持调用方给出的参考电势。
    psi = np.array([0.0, 0.1])
    reference = np.array([0.0, 7.0])
    solved = solve_mirror_ambipolar_potential(
        np.ones(2), np.full(2, 4.0), psi, m_i, e, np.array([2.0e18, 0.0]),
        1000.0 * e, 2000.0 * e, 500.0 * e,
        phi_reference_v=reference,
        ion_loss_refill=0.05,
        initial_bracket_thermal=0.01,
        potential_tolerance_v=1e-8,
        max_iterations=200,
    )
    np.testing.assert_allclose(
        solved["ion_particle_flux_m2_s"][0],
        solved["electron_particle_flux_m2_s"][0],
        rtol=1e-8,
    )
    assert solved["potential_v"][0] < 0.0
    assert solved["potential_v"][1] == reference[1]
    assert abs(solved["relative_current_residual"][0]) < 1e-9

    # 迭代预算不足和八轮扩展后仍没有包住根都必须失败关闭。
    try:
        solve_mirror_ambipolar_potential(
            1.0, 4.0, 0.0, m_i, e, 2.0e18, 1000.0 * e, 2000.0 * e,
            500.0 * e, ion_loss_refill=0.05, max_iterations=1,
            potential_tolerance_v=1e-15, current_tolerance=1e-15,
        )
    except RuntimeError as exc:
        assert "did not converge" in str(exc)
    else:
        raise AssertionError("one bisection step must not be reported as converged")

    try:
        solve_mirror_ambipolar_potential(
            1.0, 1.0, 0.0, m_i, e, 1.0e100, e, e, e,
            electron_density_ref_m3=1.0e-100,
            initial_bracket_thermal=1e-4,
        )
    except RuntimeError as exc:
        assert "failed to bracket" in str(exc)
    else:
        raise AssertionError("an unbracketed extreme current ratio must be rejected")


def test_review_gate_rejects_nonfinite_and_noninteger_solver_controls():
    import pytest

    base = dict(
        b_reference_t=1.0, b_plug_t=2.0, psi=0.0,
        ion_mass_kg=1.67262192595e-27, ion_charge_c=1.602176634e-19,
        ion_density_ref_m3=1.0e18, ion_temperature_parallel_j=1.0e-16,
        ion_temperature_perpendicular_j=2.0e-16, electron_temperature_j=1.0e-16,
        mode="evaluate", phi_plug_v=0.0,
    )
    with pytest.raises(ValueError, match="ion_mass_kg"):
        scientific_operator(**{**base, "ion_mass_kg": np.nan})
    with pytest.raises(ValueError, match="ion_charge_c"):
        scientific_operator(**{**base, "ion_charge_c": np.nan})
    with pytest.raises(ValueError, match="max_iterations"):
        scientific_operator(**{**base, "max_iterations": 2.0})
