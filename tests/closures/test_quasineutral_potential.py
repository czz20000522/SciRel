import numpy as np
import pytest

from scirel.closures.quasineutral_potential import (
    solve_quasineutral_potential,
    solve_quasineutral_potential as scientific_function,
)

ELEMENTARY_CHARGE = 1.602176634e-19


def test_monotone_log_charge_residual_reaches_known_root():
    def residual(potential):
        return {"logarithmic_charge_residual": 0.5 - np.asarray(potential)}

    result = scientific_function(
        0.0,
        2.0 * ELEMENTARY_CHARGE,
        1.0 * ELEMENTARY_CHARGE,
        ELEMENTARY_CHARGE,
        np.array([True, True]),
        residual,
        potential_tolerance_v=1.0e-10,
    )
    np.testing.assert_allclose(result["potential_v"], 0.5, atol=1.0e-8)
    assert result["converged"]
    assert np.max(np.abs(result["logarithmic_charge_residual"])) <= 1.0e-10


def test_inactive_surface_returns_reference_potential():
    result = scientific_function(
        17.0,
        2.0,
        1.0,
        1.0,
        np.array([False]),
        lambda p: {"logarithmic_charge_residual": np.ones_like(p)},
    )
    assert result["potential_v"].item() == 17.0
    assert result["converged"]


def test_all_inactive_surfaces_still_evaluate_the_returned_residual_once():
    observations = []

    def residual(potential):
        observations.append(np.asarray(potential).copy())
        return {"logarithmic_charge_residual": 0.5 - np.asarray(potential)}

    reference = np.array([17.0, 99.0])
    result = scientific_function(
        reference,
        ELEMENTARY_CHARGE,
        ELEMENTARY_CHARGE,
        ELEMENTARY_CHARGE,
        [False, False],
        residual,
    )
    assert len(observations) == 1
    np.testing.assert_array_equal(observations[0], reference)
    np.testing.assert_array_equal(result["potential_v"], reference)
    np.testing.assert_array_equal(
        result["logarithmic_charge_residual"],
        0.5 - reference,
    )
    assert result["iterations"] == 0 and result["converged"] is True


def test_invalid_residual_contract_fails_closed():
    with pytest.raises(ValueError, match="logarithmic_charge_residual"):
        scientific_function(0.0, 2.0, 1.0, 1.0, np.array([True]), lambda _: {})


def test_reviewed_relation_example():
    from scirel.closures.quasineutral_potential import solve_quasineutral_potential
    import numpy as np

    # f(phi)=phi_root-phi 具有求解器要求的符号方向。热能取 0.1 eV，
    # 初始半括区为 0.02 V，因此首、末根位于初始括区之外，会实际触发扩展。
    roots = np.array([0.8, 123.0, -0.35])
    active = np.array([True, False, True])

    def residual(potential):
        return {"logarithmic_charge_residual": roots - np.asarray(potential)}

    result = solve_quasineutral_potential(
        np.zeros(3),
        0.1 * ELEMENTARY_CHARGE,
        0.1 * ELEMENTARY_CHARGE,
        ELEMENTARY_CHARGE,
        active,
        residual,
        potential_tolerance_v=1e-11,
        quasineutral_tolerance=1e-10,
        max_iterations=200,
        initial_bracket_thermal=0.1,
    )
    np.testing.assert_allclose(result["potential_v"][active], roots[active], atol=1e-9)
    np.testing.assert_allclose(result["potential_v"][~active], 0.0)
    assert result["converged"]
    assert np.max(np.abs(result["logarithmic_charge_residual"][active])) <= 1e-9

    # 非收敛和无法括根都必须失败关闭，而不是返回一个貌似可用的电势。
    try:
        solve_quasineutral_potential(
            0.0,
            1.0,
            1.0,
            1.0,
            True,
            residual=lambda phi: {"logarithmic_charge_residual": 0.8 - np.asarray(phi)},
            potential_tolerance_v=1e-15,
            quasineutral_tolerance=1e-15,
            max_iterations=1,
            initial_bracket_thermal=0.1,
        )
    except ValueError as exc:
        assert "at least 2" in str(exc)
    else:
        raise AssertionError("one bisection step must not be reported as converged")

    try:
        solve_quasineutral_potential(
            0.0,
            1.0,
            1.0,
            1.0,
            True,
            residual=lambda phi: {"logarithmic_charge_residual": np.ones_like(phi)},
            initial_bracket_thermal=0.1,
        )
    except RuntimeError as exc:
        assert "failed to bracket" in str(exc)
    else:
        raise AssertionError("a residual without a sign change must be rejected")


def test_contract_rejects_nonfinite_solver_controls_and_accepts_mapping_results():
    import pytest

    def residual(potential):
        return {"logarithmic_charge_residual": 0.5 - np.asarray(potential)}

    with pytest.raises(ValueError, match="invalid quasineutral solver controls"):
        solve_quasineutral_potential(
            0.0, 1.0, 1.0, 1.0, True, residual, potential_tolerance_v=np.nan
        )

    with pytest.raises(ValueError, match="max_iterations must be an integer"):
        solve_quasineutral_potential(0.0, 1.0, 1.0, 1.0, True, residual, max_iterations=3.5)

    class MappingResult(dict):
        pass

    result = solve_quasineutral_potential(
        0.0,
        1.0,
        1.0,
        1.0,
        True,
        lambda potential: MappingResult(
            {"logarithmic_charge_residual": 0.5 - np.asarray(potential)}
        ),
        potential_tolerance_v=1.0e-8,
        quasineutral_tolerance=1.0e-8,
    )
    assert result["converged"]


def test_mixed_active_inactive_residual_uses_reference_at_inactive_surfaces():
    observations = []

    def residual(potential):
        values = np.asarray(potential)
        observations.append(values.copy())
        assert values[0] == pytest.approx(17.0)
        assert values[2] == pytest.approx(99.0)
        return {"logarithmic_charge_residual": 0.5 - values}

    result = solve_quasineutral_potential(
        np.array([17.0, 0.0, 99.0]),
        2.0 * ELEMENTARY_CHARGE,
        1.0 * ELEMENTARY_CHARGE,
        ELEMENTARY_CHARGE,
        np.array([False, True, False]),
        residual,
        potential_tolerance_v=1.0e-10,
        quasineutral_tolerance=1.0e-10,
        max_iterations=60,
        initial_bracket_thermal=1.0,
    )

    np.testing.assert_allclose(result["potential_v"], [17.0, 0.5, 99.0], atol=1.0e-8)
    assert observations


def test_iteration_budget_has_no_hidden_convergence_evaluation():
    calls = []

    def residual(potential):
        values = np.asarray(potential)
        calls.append(values.copy())
        return {"logarithmic_charge_residual": 1.0 - values}

    with pytest.raises(RuntimeError, match="did not converge"):
        solve_quasineutral_potential(
            0.0,
            2.0 * ELEMENTARY_CHARGE,
            1.0 * ELEMENTARY_CHARGE,
            ELEMENTARY_CHARGE,
            np.array([True]),
            residual,
            potential_tolerance_v=1.0e-12,
            quasineutral_tolerance=1.0e-14,
            max_iterations=4,
            initial_bracket_thermal=1.0,
        )

    assert len(calls) == 2 + 4


def test_max_iterations_must_allow_a_real_bisection_decision():
    with pytest.raises(ValueError, match="at least 2"):
        solve_quasineutral_potential(
            0.0,
            2.0 * ELEMENTARY_CHARGE,
            1.0 * ELEMENTARY_CHARGE,
            ELEMENTARY_CHARGE,
            np.array([True]),
            lambda potential: {"logarithmic_charge_residual": -np.asarray(potential)},
            max_iterations=1,
        )
