import numpy as np
import pytest

from scirel.inference.anisotropic_parameter_optimization import optimize_anisotropic_parameters, optimize_anisotropic_parameters as direct_anisotropic_optimizer


def test_recovers_scalar_trial_minimum_and_keeps_fallback():
    def trial(*, params):
        residual = np.asarray([params["x"] - 3.0])
        return {"chi2": float(np.dot(residual, residual)), "residuals": residual, "equilibrium": {"converged": True}, "failure_reason": None}
    result = direct_anisotropic_optimizer(initial_params={"x": 0.0}, bounds={"x": (-5.0, 5.0)}, method="least_squares", trial_evaluator=trial)
    assert result["best_parameters"]["x"] == pytest.approx(3.0)
    assert result["converged"]
    failed = direct_anisotropic_optimizer(initial_params={"x": 0.0}, bounds={"x": (-1.0, 1.0)}, method="bad", trial_evaluator=trial)
    assert failed["failure_reason"] is not None


def test_reviewed_relation_example():
    import numpy as np
    from scirel.inference.anisotropic_parameter_optimization import optimize_anisotropic_parameters

    def trial(*, params):
        residuals = np.asarray([params["x"] - 3.0])
        return {
            "params": dict(params),
            "chi2": float(residuals @ residuals),
            "residuals": residuals,
            "equilibrium": {"converged": True},
            "failure_reason": None,
        }

    result = optimize_anisotropic_parameters(
        initial_params={"x": 0.0, "fixed": 7.0},
        bounds={"x": (-5.0, 5.0)},
        fit_keys=["x"],
        method="least_squares",
        trial_evaluator=trial,
    )
    assert abs(result["best_parameters"]["x"] - 3.0) < 1.0e-6
    assert result["best_parameters"]["fixed"] == 7.0
    assert np.allclose(result["chi2"], result["residual_vector"] @ result["residual_vector"])
    assert result["chi2"] == min(item["chi2"] for item in result["evaluation_log"])
    assert result["converged"]

    # LHS 只负责选择直接优化起点；日志顺序和起点选择均是公开算法合同。
    def sampler(*, bounds, n_samples, seed, fit_keys):
        assert n_samples == 2 and seed == 9 and fit_keys == ["x"]
        return {"initial_samples": [{"x": -4.0}, {"x": 2.5}]}

    seeded = optimize_anisotropic_parameters(
        initial_params={"x": 0.0, "fixed": 7.0},
        bounds={"x": (-5.0, 5.0)},
        fit_keys=["x"],
        method="least_squares",
        trial_evaluator=trial,
        lhs_sampler=sampler,
        n_initial_samples=2,
        seed=9,
    )
    assert [item["source"] for item in seeded["evaluation_log"][:3]] == [
        "latin_hypercube", "latin_hypercube", "optimizer"
    ]
    assert seeded["evaluation_log"][2]["params"]["x"] == 2.5

    # 未知方法进入受控 fallback：在起点补做 trial，但不伪造优化收敛。
    fallback = optimize_anisotropic_parameters(
        initial_params={"x": 1.0},
        bounds={"x": (-5.0, 5.0)},
        method="unknown",
        trial_evaluator=trial,
    )
    assert fallback["optimizer_summary"] is None
    assert "method must be" in fallback["failure_reason"]
    assert not fallback["converged"]
    assert len(fallback["evaluation_log"]) == 1
    assert fallback["evaluation_log"][0]["source"] == "optimizer"
