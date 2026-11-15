"""Complete returned-vector norms survive scientific port composition."""

from fractions import Fraction
import math

import numpy as np
import pytest

from scirel.diagnostics import reduce_observation_residuals
from scirel.inference import evaluate_anisotropic_trial, optimize_anisotropic_parameters


def assert_complete(actual, expected):
    """Compare on this quantity's scale without underflowing the budget."""
    assert abs(Fraction(float(actual)) - expected) <= Fraction(1e-13) * abs(expected), (
        "a public chi2 must retain the complete returned-vector square contributions"
    )


def trial_for(vector, *, reducer=reduce_observation_residuals):
    return evaluate_anisotropic_trial(
        params={},
        observations={"flux_loops": {"values": np.zeros_like(vector), "sigma": 1.0}},
        solver_config={"r_grid": [0.0], "z_grid": [0.0]},
        equilibrium_solver=lambda _: {"converged": True},
        diagnostic_evaluator=lambda _: {"flux_loops": vector},
        residual_reducer=reducer,
    )


@pytest.mark.parametrize("count", [4096, 32768])
def test_trial_retains_complete_tail_and_accepts_correct_reducer(count):
    vector = np.array([2.0**-511] + [2.0**-538] * count)
    expected = Fraction(2) ** -1022 + count * Fraction(2) ** -1076
    result = trial_for(vector)
    assert result.valid
    np.testing.assert_array_equal(result.residuals, vector)
    assert_complete(result.chi2, expected)


@pytest.mark.parametrize("method", ["least_squares", "minimize"])
def test_real_optimizer_preserves_complete_trial_norm_and_objective(method, monkeypatch):
    vector = np.array([2.0**-511] + [2.0**-538] * 4096)
    expected = Fraction(2) ** -1022 + 4096 * Fraction(2) ** -1076
    observed_objectives = []
    if method == "minimize":
        from scipy import optimize

        original = optimize.minimize

        def observe_objective(fun, x0, **kwargs):
            observed_objectives.append(fun(x0))
            return original(fun, x0, **kwargs)

        monkeypatch.setattr(optimize, "minimize", observe_objective)

    def trial(*, params):
        return {
            "residuals": vector.copy(),
            "chi2": float(expected),
            "equilibrium": {"converged": True},
            "failure_reason": None,
        }

    result = optimize_anisotropic_parameters(
        initial_params={"x": 0.5},
        bounds={"x": (0.0, 1.0)},
        method=method,
        trial_evaluator=trial,
        max_evaluations=20,
    )
    assert result.forward_converged
    np.testing.assert_array_equal(result.residual_vector, vector)
    assert_complete(result.chi2, expected)
    for record in result.evaluation_log:
        assert_complete(record["chi2"], expected)
    if method == "minimize":
        assert observed_objectives
        for objective in observed_objectives:
            assert_complete(objective, expected)


@pytest.mark.parametrize("consumer", ["trial", "least_squares", "minimize"])
def test_failure_penalty_vector_uses_complete_square_sum(consumer):
    count = 4096
    penalty = (1.0 + 2.0**-21) * 2.0**-538
    expected = count * Fraction(penalty) ** 2
    if consumer == "trial":

        def unexpected(_):
            raise AssertionError("nonconverged forward state must short-circuit diagnostics")

        result = evaluate_anisotropic_trial(
            params={},
            observations={},
            solver_config={"r_grid": [0.0], "z_grid": [0.0]},
            equilibrium_solver=lambda _: {"converged": False},
            diagnostic_evaluator=unexpected,
            residual_reducer=unexpected,
            residual_size=count,
            failure_penalty=penalty,
        )
        residual = result.residuals
        assert not result.valid
    else:

        def failing_trial(*, params):
            raise FloatingPointError("declared numerical port failure")

        result = optimize_anisotropic_parameters(
            initial_params={"x": 0.5},
            bounds={"x": (0.0, 1.0)},
            method=consumer,
            trial_evaluator=failing_trial,
            residual_size=count,
            failure_penalty=penalty,
            max_evaluations=20,
        )
        residual = result.residual_vector
        assert not result.forward_converged
    np.testing.assert_array_equal(residual, np.full(count, penalty))
    assert_complete(result.chi2, Fraction(float(expected)))
    assert result.chi2 > 0


@pytest.mark.parametrize(
    "exponent,steps,accepted", [(-518, 1, False), (-515, 30, True), (-515, 40, False)]
)
def test_original_port_match_budget_is_applied_without_tolerance_underflow(
    exponent, steps, accepted
):
    vector = np.array([1.5 * 2.0**exponent])
    expected = Fraction(vector[0]) ** 2
    claimed = float(expected) + steps * math.ulp(0.0)
    exact_close = abs(Fraction(claimed) - expected) <= Fraction(1e-12) * expected
    assert exact_close is accepted

    def reducer(**_):
        return {"residual_vector": vector, "chi2": claimed}

    if accepted:
        assert_complete(trial_for(vector, reducer=reducer).chi2, expected)
    else:
        with pytest.raises(ValueError, match="chi2"):
            trial_for(vector, reducer=reducer)


def test_true_final_overflow_is_still_a_rejected_port_record():
    vector = np.array([1e308])
    with pytest.raises(ValueError, match="chi2"):
        trial_for(vector, reducer=lambda **_: {"residual_vector": vector, "chi2": 1e308})
