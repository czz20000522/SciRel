import numpy as np
import pytest

from scirel.closures.quasineutral_potential import solve_quasineutral_potential, solve_quasineutral_potential as scientific_operator


def test_monotone_log_charge_residual_reaches_known_root():
    def residual(potential):
        return {"logarithmic_charge_residual": 0.5 - np.asarray(potential)}

    result = scientific_operator(0.0, 2.0, 1.0, 1.0, np.array([True, True]), residual, potential_tolerance_v=1.0e-10)
    np.testing.assert_allclose(result["potential_v"], 0.5, atol=1.0e-8)
    assert result["converged"]
    assert np.max(np.abs(result["logarithmic_charge_residual"])) <= 1.0e-10


def test_inactive_surface_returns_reference_potential():
    result = scientific_operator(17.0, 2.0, 1.0, 1.0, np.array([False]), lambda p: {"logarithmic_charge_residual": np.ones_like(p)})
    assert result["potential_v"].item() == 17.0
    assert result["converged"]


def test_invalid_residual_contract_fails_closed():
    with pytest.raises(ValueError, match="logarithmic_charge_residual"):
        scientific_operator(0.0, 2.0, 1.0, 1.0, np.array([True]), lambda _: {})


def test_reviewed_relation_example():
    from scirel.closures.quasineutral_potential import solve_quasineutral_potential
    import numpy as np

    ELEMENTARY_CHARGE = 1.602176634e-19
    # f(phi)=phi_root-phi 具有求解器要求的符号方向。热能取 0.1 eV，
    # 初始半括区为 0.02 V，因此首、末根位于初始括区之外，会实际触发扩展。
    roots = np.array([0.8, 123.0, -0.35])
    active = np.array([True, False, True])

    def residual(potential):
        return {"logarithmic_charge_residual": roots - np.asarray(potential)}

    result = solve_quasineutral_potential(
        np.zeros(3), 0.1 * ELEMENTARY_CHARGE, 0.1 * ELEMENTARY_CHARGE,
        ELEMENTARY_CHARGE, active, residual,
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
            0.0, 1.0, 1.0, 1.0, True, residual=lambda phi: {
                "logarithmic_charge_residual": 0.8 - np.asarray(phi)
            },
            potential_tolerance_v=1e-15,
            quasineutral_tolerance=1e-15,
            max_iterations=1,
            initial_bracket_thermal=0.1,
        )
    except RuntimeError as exc:
        assert "did not converge" in str(exc)
    else:
        raise AssertionError("one bisection step must not be reported as converged")

    try:
        solve_quasineutral_potential(
            0.0, 1.0, 1.0, 1.0, True,
            residual=lambda phi: {"logarithmic_charge_residual": np.ones_like(phi)},
            initial_bracket_thermal=0.1,
        )
    except RuntimeError as exc:
        assert "failed to bracket" in str(exc)
    else:
        raise AssertionError("a residual without a sign change must be rejected")


def test_review_gate_rejects_nonfinite_solver_controls_and_accepts_mapping_results():
    import pytest

    def residual(potential):
        return {"logarithmic_charge_residual": 0.5 - np.asarray(potential)}

    with pytest.raises(ValueError, match="invalid quasineutral solver controls"):
        solve_quasineutral_potential(0.0, 1.0, 1.0, 1.0, True, residual, potential_tolerance_v=np.nan)

    with pytest.raises(ValueError, match="max_iterations must be an integer"):
        solve_quasineutral_potential(0.0, 1.0, 1.0, 1.0, True, residual, max_iterations=3.5)

    class MappingResult(dict):
        pass

    result = solve_quasineutral_potential(
        0.0, 1.0, 1.0, 1.0, True,
        lambda potential: MappingResult({"logarithmic_charge_residual": 0.5 - np.asarray(potential)}),
        potential_tolerance_v=1.0e-8,
        quasineutral_tolerance=1.0e-8,
    )
    assert result["converged"]
