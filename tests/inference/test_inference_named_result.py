"""Regression fixtures captured from the pre-Result inference implementation."""

from types import SimpleNamespace

import numpy as np
import pytest
from scipy import optimize

import scirel.inference as inference
from scirel._result import Result


_PUBLIC_EXAMPLE_COVERAGE = {
    "sample_latin_hypercube": "deterministic seeded design",
    "evaluate_anisotropic_trial": "nonconverged and valid branches",
    "optimize_anisotropic_parameters": "successful local fit",
}


def _assert_named_legacy_result(result, expected, *, vector_field=None, vector_shape=None):
    assert type(result) is Result
    assert isinstance(result, dict)
    assert list(result) == list(expected)
    for field, value in expected.items():
        np.testing.assert_equal(result[field], value)
        assert getattr(result, field) is result[field]
    if vector_field is not None:
        vector = result[vector_field]
        assert type(vector) is np.ndarray
        assert vector.shape == vector_shape
        assert vector.dtype == np.float64


def _optimizer_baseline(**changes):
    """Start from the complete pre-change result shape and ordered defaults."""
    expected = {
        "best_parameters": None,
        "chi2": 1.0e24,
        "residual_vector": np.array([1.0e12]),
        "converged": False,
        "forward_converged": False,
        "optimizer_converged": False,
        "equilibrium": None,
        "evaluation_log": [],
        "failure_reason": None,
        "optimizer_summary": None,
        "best_valid_trial": None,
        "scientific_evaluations": 0,
        "max_evaluations": 6,
        "valid_trial_count": 0,
        "residual_size": 1,
        "identifiability": "not_established",
    }
    assert set(changes) <= set(expected)
    expected.update(changes)
    return expected


def _valid_retained_trial(x):
    return {
        "params": {"x": x},
        "chi2": 0.0,
        "residuals": np.array([0.0]),
        "equilibrium": {"converged": True, "x": x},
        "failure_reason": None,
        "valid": True,
    }


def test_all_public_inference_callables_have_example_coverage():
    assert inference.__all__ == [
        "sample_latin_hypercube",
        "optimize_anisotropic_parameters",
        "evaluate_anisotropic_trial",
    ]
    assert set(_PUBLIC_EXAMPLE_COVERAGE) == set(inference.__all__)


def test_latin_hypercube_returns_legacy_values_as_a_named_result():
    result = inference.sample_latin_hypercube(
        bounds={"a": (0.0, 1.0), "b": (10.0, 20.0)},
        n_samples=5,
        seed=4,
    )
    expected = {
        "initial_samples": [
            {"a": 0.4161672047791204, "b": 17.804430159431977},
            {"a": 0.9214711663990058, "b": 14.954307047678412},
            {"a": 0.07529731687545452, "b": 10.860992555458827},
            {"a": 0.3603802413971614, "b": 13.577893435088658},
            {"a": 0.6349055632288056, "b": 19.968305999862242},
        ]
    }

    _assert_named_legacy_result(result, expected)


@pytest.mark.parametrize(
    "call,error_type,message,exception_args",
    [
        (
            lambda: inference.sample_latin_hypercube(bounds=[], n_samples=1),
            ValueError,
            "bounds mapping and positive integer n_samples required",
            ("bounds mapping and positive integer n_samples required",),
        ),
        (
            lambda: inference.sample_latin_hypercube(bounds={"a": (0.0, 1.0)}, n_samples=0),
            ValueError,
            "bounds mapping and positive integer n_samples required",
            ("bounds mapping and positive integer n_samples required",),
        ),
        (
            lambda: inference.sample_latin_hypercube(bounds={"a": (0.0, 1.0)}, n_samples=True),
            ValueError,
            "bounds mapping and positive integer n_samples required",
            ("bounds mapping and positive integer n_samples required",),
        ),
        (
            lambda: inference.sample_latin_hypercube(bounds={"a": (0.0, 1.0)}, n_samples=1.5),
            ValueError,
            "bounds mapping and positive integer n_samples required",
            ("bounds mapping and positive integer n_samples required",),
        ),
        (
            lambda: inference.sample_latin_hypercube(
                bounds={"a": (0.0, 1.0)}, n_samples=np.float64(2.0)
            ),
            ValueError,
            "bounds mapping and positive integer n_samples required",
            ("bounds mapping and positive integer n_samples required",),
        ),
        (
            lambda: inference.sample_latin_hypercube(bounds={"a": (1.0, 1.0)}, n_samples=2),
            ValueError,
            "finite increasing bounds required for a",
            ("finite increasing bounds required for a",),
        ),
        (
            lambda: inference.sample_latin_hypercube(bounds={"a": (1.0, 0.0)}, n_samples=2),
            ValueError,
            "finite increasing bounds required for a",
            ("finite increasing bounds required for a",),
        ),
        (
            lambda: inference.sample_latin_hypercube(
                bounds={"a": (0.0, float("inf"))}, n_samples=2
            ),
            ValueError,
            "finite increasing bounds required for a",
            ("finite increasing bounds required for a",),
        ),
        (
            lambda: inference.sample_latin_hypercube(
                bounds={"a": (float("nan"), 1.0)}, n_samples=2
            ),
            ValueError,
            "finite increasing bounds required for a",
            ("finite increasing bounds required for a",),
        ),
        (
            lambda: inference.sample_latin_hypercube(
                bounds={"a": (0.0, 1.0)}, n_samples=2, fit_keys=1
            ),
            TypeError,
            "'int' object is not iterable",
            ("'int' object is not iterable",),
        ),
        (
            lambda: inference.sample_latin_hypercube(
                bounds={"a": (0.0, 1.0)}, n_samples=2, fit_keys=["missing"]
            ),
            KeyError,
            "'missing'",
            ("missing",),
        ),
        (
            lambda: inference.sample_latin_hypercube(bounds={"a": (0.0,)}, n_samples=2),
            ValueError,
            "not enough values to unpack (expected 2, got 1)",
            ("not enough values to unpack (expected 2, got 1)",),
        ),
        (
            lambda: inference.sample_latin_hypercube(bounds={"a": (0.0, 1.0, 2.0)}, n_samples=2),
            ValueError,
            "too many values to unpack (expected 2)",
            ("too many values to unpack (expected 2)",),
        ),
        (
            lambda: inference.sample_latin_hypercube(bounds={"a": ("x", 1.0)}, n_samples=2),
            ValueError,
            "could not convert string to float: 'x'",
            ("could not convert string to float: 'x'",),
        ),
        (
            lambda: inference.sample_latin_hypercube(bounds={"a": (None, 1.0)}, n_samples=2),
            TypeError,
            "float() argument must be a string or a real number, not 'NoneType'",
            ("float() argument must be a string or a real number, not 'NoneType'",),
        ),
        (
            lambda: inference.sample_latin_hypercube(
                bounds={"a": (0.0, 1.0)}, n_samples=2, seed="bad"
            ),
            TypeError,
            "SeedSequence expects int or sequence of ints for entropy not bad",
            ("SeedSequence expects int or sequence of ints for entropy not bad",),
        ),
    ],
)
def test_latin_hypercube_rejections_match_prechange_baseline(
    call, error_type, message, exception_args
):
    with pytest.raises(error_type) as caught:
        call()
    assert type(caught.value) is error_type
    assert str(caught.value) == message
    assert caught.value.args == exception_args


def test_trial_failure_and_success_return_legacy_values_as_named_results():
    failure = inference.evaluate_anisotropic_trial(
        params={"p": 1.0},
        observations={"flux_loops": {"values": [1.0, 2.0]}},
        solver_config={"r_grid": [0.0], "z_grid": [0.0]},
        equilibrium_solver=lambda _: {
            "converged": False,
            "failure_reason": "iteration limit",
        },
        diagnostic_evaluator=lambda _: None,
        residual_reducer=lambda **_: None,
    )
    expected_failure = {
        "params": {"p": 1.0},
        "residuals": np.array([1.0e12, 1.0e12]),
        "chi2": 2.0e24,
        "equilibrium": {"converged": False, "failure_reason": "iteration limit"},
        "failure_reason": "iteration limit",
        "valid": False,
        "status": "forward_nonconvergence",
        "failed_port": "equilibrium_solver",
        "exception_type": None,
    }

    _assert_named_legacy_result(
        failure, expected_failure, vector_field="residuals", vector_shape=(2,)
    )

    success = inference.evaluate_anisotropic_trial(
        params={"p": 1.0},
        observations={"values": [0.5, -1.0]},
        solver_config={"r_grid": [0.0], "z_grid": [0.0]},
        equilibrium_solver=lambda _: {"converged": True, "state": "ok"},
        diagnostic_evaluator=lambda _: {"predicted": [2.0, 4.0]},
        residual_reducer=lambda **_: {
            "residual_vector": np.array([0.5, -1.0]),
            "chi2": 1.25,
        },
        residual_size=2,
    )
    expected_success = {
        "params": {"p": 1.0},
        "chi2": 1.25,
        "residuals": np.array([0.5, -1.0]),
        "equilibrium": {"converged": True, "state": "ok"},
        "failure_reason": None,
        "valid": True,
        "status": "valid",
        "failed_port": None,
        "exception_type": None,
    }

    _assert_named_legacy_result(
        success, expected_success, vector_field="residuals", vector_shape=(2,)
    )


@pytest.mark.parametrize(
    "failed_port,error_type,message,equilibrium_expected,expected_calls",
    [
        (
            "equilibrium_solver",
            FloatingPointError,
            "equilibrium arithmetic",
            None,
            (1, 0, 0),
        ),
        (
            "diagnostic_evaluator",
            ArithmeticError,
            "diagnostic arithmetic",
            {"converged": True, "marker": "eq"},
            (1, 1, 0),
        ),
        (
            "diagnostic_evaluator",
            RuntimeError,
            "diagnostic runtime",
            {"converged": True, "marker": "eq"},
            (1, 1, 0),
        ),
        (
            "residual_reducer",
            ArithmeticError,
            "reducer arithmetic",
            {"converged": True, "marker": "eq"},
            (1, 1, 1),
        ),
        (
            "residual_reducer",
            RuntimeError,
            "reducer runtime",
            {"converged": True, "marker": "eq"},
            (1, 1, 1),
        ),
    ],
)
def test_trial_numerical_failure_paths_match_prechange_baseline(
    failed_port, error_type, message, equilibrium_expected, expected_calls
):
    calls = [0, 0, 0]

    def equilibrium_solver(_):
        calls[0] += 1
        if failed_port == "equilibrium_solver":
            raise error_type(message)
        return {"converged": True, "marker": "eq"}

    def diagnostic_evaluator(_):
        calls[1] += 1
        if failed_port == "diagnostic_evaluator":
            raise error_type(message)
        return {"predicted": [1.0, 2.0]}

    def residual_reducer(**_):
        calls[2] += 1
        if failed_port == "residual_reducer":
            raise error_type(message)
        return {"residual_vector": np.array([0.0, 0.0]), "chi2": 0.0}

    result = inference.evaluate_anisotropic_trial(
        params={"p": 1.0},
        observations={"flux_loops": {"values": [1.0, 2.0]}},
        solver_config={"r_grid": [0.0], "z_grid": [0.0]},
        equilibrium_solver=equilibrium_solver,
        diagnostic_evaluator=diagnostic_evaluator,
        residual_reducer=residual_reducer,
    )
    expected = {
        "params": {"p": 1.0},
        "residuals": np.array([1.0e12, 1.0e12]),
        "chi2": 2.0e24,
        "equilibrium": equilibrium_expected,
        "failure_reason": message,
        "valid": False,
        "status": "numerical_failure",
        "failed_port": failed_port,
        "exception_type": error_type.__name__,
    }

    _assert_named_legacy_result(result, expected, vector_field="residuals", vector_shape=(2,))
    assert tuple(calls) == expected_calls


def test_optimizer_returns_legacy_values_as_a_named_result(monkeypatch):
    def fake_least_squares(function, x0, bounds, max_nfev):
        assert callable(function)
        np.testing.assert_array_equal(x0, [0.0])
        assert max_nfev == 3
        return SimpleNamespace(
            x=np.array([3.0]),
            success=True,
            status=1,
            message="forced success",
            nfev=0,
        )

    monkeypatch.setattr(optimize, "least_squares", fake_least_squares)

    def trial(*, params):
        residuals = np.array([params["x"] - 3.0])
        return {
            "chi2": float(residuals @ residuals),
            "residuals": residuals,
            "equilibrium": {"converged": True},
            "failure_reason": None,
        }

    result = inference.optimize_anisotropic_parameters(
        initial_params={"x": 0.0, "fixed": 7.0},
        bounds={"x": (-5.0, 5.0)},
        fit_keys=["x"],
        method="least_squares",
        trial_evaluator=trial,
        max_evaluations=3,
    )
    retained = {
        "params": {"x": 3.0, "fixed": 7.0},
        "chi2": 0.0,
        "residuals": np.array([0.0]),
        "equilibrium": {"converged": True},
        "failure_reason": None,
        "valid": True,
    }
    expected = {
        "best_parameters": {"x": 3.0, "fixed": 7.0},
        "chi2": 0.0,
        "residual_vector": np.array([0.0]),
        "converged": True,
        "forward_converged": True,
        "optimizer_converged": True,
        "equilibrium": {"converged": True},
        "evaluation_log": [
            {
                "params": {"x": 3.0, "fixed": 7.0},
                "chi2": 0.0,
                "failure_reason": None,
                "valid": True,
                "source": "terminal",
            }
        ],
        "failure_reason": None,
        "optimizer_summary": {
            "method": "least_squares",
            "success": True,
            "status": 1,
            "message": "forced success",
            "nfev": 0,
            "parameters": {"x": 3.0},
        },
        "best_valid_trial": retained,
        "scientific_evaluations": 1,
        "max_evaluations": 3,
        "valid_trial_count": 1,
        "residual_size": 1,
        "identifiability": "not_established",
    }

    _assert_named_legacy_result(result, expected, vector_field="residual_vector", vector_shape=(1,))


def test_optimizer_budget_exhaustion_matches_prechange_baseline(monkeypatch):
    def trial(*, params):
        x = params["x"]
        residual = np.array([x - 1.0])
        return {
            "chi2": float(residual @ residual),
            "residuals": residual,
            "equilibrium": {"converged": True, "x": x},
            "failure_reason": None,
        }

    def fake_least_squares(function, x0, bounds, max_nfev):
        assert max_nfev == 4
        for x in (0.0, 1.0, 2.0):
            function(np.array([x]))
        raise AssertionError("the third nonterminal evaluation must exhaust the budget")

    monkeypatch.setattr(optimize, "least_squares", fake_least_squares)
    result = inference.optimize_anisotropic_parameters(
        initial_params={"x": 0.0},
        bounds={"x": (-5.0, 5.0)},
        method="least_squares",
        trial_evaluator=trial,
        max_evaluations=4,
    )
    expected = _optimizer_baseline(
        best_parameters={"x": 1.0},
        chi2=0.0,
        residual_vector=np.array([0.0]),
        forward_converged=True,
        equilibrium={"converged": True, "x": 1.0},
        evaluation_log=[
            {
                "params": {"x": 0.0},
                "chi2": 1.0,
                "failure_reason": None,
                "valid": True,
                "source": "optimizer",
            },
            {
                "params": {"x": 1.0},
                "chi2": 0.0,
                "failure_reason": None,
                "valid": True,
                "source": "optimizer",
            },
            {
                "params": {"x": 1.0},
                "chi2": 0.0,
                "failure_reason": None,
                "valid": True,
                "source": "best_valid_recheck",
            },
        ],
        failure_reason="scientific evaluation budget exhausted",
        best_valid_trial=_valid_retained_trial(1.0),
        scientific_evaluations=3,
        max_evaluations=4,
        valid_trial_count=3,
    )

    _assert_named_legacy_result(result, expected, vector_field="residual_vector", vector_shape=(1,))


def test_optimizer_no_valid_candidate_matches_prechange_baseline(monkeypatch):
    def invalid_trial(*, params):
        return {
            "chi2": 0.25,
            "residuals": np.array([0.5]),
            "equilibrium": {"converged": False, "x": params["x"]},
            "failure_reason": "terminal invalid",
        }

    def fake_least_squares(function, x0, bounds, max_nfev):
        return SimpleNamespace(
            x=np.array([2.0]),
            success=True,
            status=1,
            message="terminal invalid",
            nfev=0,
        )

    monkeypatch.setattr(optimize, "least_squares", fake_least_squares)
    result = inference.optimize_anisotropic_parameters(
        initial_params={"x": 0.0},
        bounds={"x": (-5.0, 5.0)},
        method="least_squares",
        trial_evaluator=invalid_trial,
        max_evaluations=5,
    )
    expected = _optimizer_baseline(
        optimizer_converged=True,
        evaluation_log=[
            {
                "params": {"x": 2.0},
                "chi2": 0.25,
                "failure_reason": "terminal invalid",
                "valid": False,
                "source": "terminal",
            }
        ],
        failure_reason="terminal invalid",
        optimizer_summary={
            "method": "least_squares",
            "success": True,
            "status": 1,
            "message": "terminal invalid",
            "nfev": 0,
            "parameters": {"x": 2.0},
        },
        scientific_evaluations=1,
        max_evaluations=5,
    )

    _assert_named_legacy_result(result, expected, vector_field="residual_vector", vector_shape=(1,))


def test_optimizer_historical_fallback_matches_prechange_baseline(monkeypatch):
    def trial(*, params):
        x = params["x"]
        if x == 1.0:
            residual = np.array([0.0])
            equilibrium = {"converged": True, "x": x}
            failure_reason = None
        else:
            residual = np.array([0.5])
            equilibrium = {"converged": False, "x": x}
            failure_reason = "terminal invalid"
        return {
            "chi2": float(residual @ residual),
            "residuals": residual,
            "equilibrium": equilibrium,
            "failure_reason": failure_reason,
        }

    def fake_least_squares(function, x0, bounds, max_nfev):
        function(np.array([1.0]))
        return SimpleNamespace(
            x=np.array([2.0]),
            success=True,
            status=1,
            message="terminal invalid",
            nfev=1,
        )

    monkeypatch.setattr(optimize, "least_squares", fake_least_squares)
    result = inference.optimize_anisotropic_parameters(
        initial_params={"x": 0.0},
        bounds={"x": (-5.0, 5.0)},
        method="least_squares",
        trial_evaluator=trial,
        max_evaluations=6,
    )
    expected = _optimizer_baseline(
        best_parameters={"x": 1.0},
        chi2=0.0,
        residual_vector=np.array([0.0]),
        forward_converged=True,
        optimizer_converged=True,
        equilibrium={"converged": True, "x": 1.0},
        evaluation_log=[
            {
                "params": {"x": 1.0},
                "chi2": 0.0,
                "failure_reason": None,
                "valid": True,
                "source": "optimizer",
            },
            {
                "params": {"x": 2.0},
                "chi2": 0.25,
                "failure_reason": "terminal invalid",
                "valid": False,
                "source": "terminal",
            },
            {
                "params": {"x": 1.0},
                "chi2": 0.0,
                "failure_reason": None,
                "valid": True,
                "source": "best_valid_recheck",
            },
        ],
        failure_reason="terminal invalid",
        optimizer_summary={
            "method": "least_squares",
            "success": True,
            "status": 1,
            "message": "terminal invalid",
            "nfev": 1,
            "parameters": {"x": 2.0},
        },
        best_valid_trial=_valid_retained_trial(1.0),
        scientific_evaluations=3,
        valid_trial_count=2,
    )

    _assert_named_legacy_result(result, expected, vector_field="residual_vector", vector_shape=(1,))


def test_optimizer_numerical_failure_matches_prechange_baseline(monkeypatch):
    def fake_least_squares(function, x0, bounds, max_nfev):
        raise RuntimeError("solver runtime")

    def unreachable_trial(**_):
        raise AssertionError("the optimizer fails before any scientific trial")

    monkeypatch.setattr(optimize, "least_squares", fake_least_squares)
    result = inference.optimize_anisotropic_parameters(
        initial_params={"x": 0.0},
        bounds={"x": (-5.0, 5.0)},
        method="least_squares",
        trial_evaluator=unreachable_trial,
        residual_size=2,
        max_evaluations=6,
    )
    expected = _optimizer_baseline(
        chi2=2.0e24,
        residual_vector=np.array([1.0e12, 1.0e12]),
        failure_reason="optimizer numerical failure: RuntimeError: solver runtime",
        residual_size=2,
    )

    _assert_named_legacy_result(result, expected, vector_field="residual_vector", vector_shape=(2,))


def test_optimizer_minimize_non_success_matches_prechange_baseline(monkeypatch):
    def trial(*, params):
        x = params["x"]
        residual = np.array([x - 1.0])
        return {
            "chi2": float(residual @ residual),
            "residuals": residual,
            "equilibrium": {"converged": True, "x": x},
            "failure_reason": None,
        }

    def fake_minimize(objective, x0, method, bounds, options):
        assert method == "L-BFGS-B"
        assert options == {"maxfun": 6, "maxiter": 6}
        assert objective(np.array([0.5])) == 0.25
        return SimpleNamespace(
            x=np.array([1.0]),
            success=False,
            status=3,
            message="minimize stopped",
            nfev=2,
        )

    monkeypatch.setattr(optimize, "minimize", fake_minimize)
    result = inference.optimize_anisotropic_parameters(
        initial_params={"x": 0.0},
        bounds={"x": (-5.0, 5.0)},
        method="minimize",
        trial_evaluator=trial,
        max_evaluations=6,
    )
    expected = _optimizer_baseline(
        best_parameters={"x": 1.0},
        chi2=0.0,
        residual_vector=np.array([0.0]),
        forward_converged=True,
        equilibrium={"converged": True, "x": 1.0},
        evaluation_log=[
            {
                "params": {"x": 0.5},
                "chi2": 0.25,
                "failure_reason": None,
                "valid": True,
                "source": "optimizer",
            },
            {
                "params": {"x": 1.0},
                "chi2": 0.0,
                "failure_reason": None,
                "valid": True,
                "source": "terminal",
            },
        ],
        failure_reason="optimizer stopped: minimize stopped",
        optimizer_summary={
            "method": "minimize",
            "success": False,
            "status": 3,
            "message": "minimize stopped",
            "nfev": 2,
            "parameters": {"x": 1.0},
        },
        best_valid_trial=_valid_retained_trial(1.0),
        scientific_evaluations=2,
        valid_trial_count=2,
    )

    _assert_named_legacy_result(result, expected, vector_field="residual_vector", vector_shape=(1,))
