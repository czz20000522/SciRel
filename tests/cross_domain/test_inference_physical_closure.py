"""Explicit observational units and valid fixed-dimensional inverse trials."""

from copy import deepcopy
import numpy as np
import pytest
from scirel.diagnostics import synthesize_equilibrium_diagnostics as diagnose
from scirel.diagnostics import reduce_observation_residuals as reduce
from scirel.inference import evaluate_anisotropic_trial as trial
from scirel.inference import optimize_anisotropic_parameters as optimize


def diagnostic_input():
    R, Z = np.meshgrid([0.0, 1.0, 2.0], [-1.0, 0.0, 1.0])
    return {
        "R": R,
        "Z": Z,
        "equilibrium": {
            "psi": R**2,
            "psi_unit": "Wb/rad",
            "profiles": {"p_perp": 2 + R, "p_parallel": 3 + R},
            "profile_units": {"p_perp": "Pa", "p_parallel": "Pa"},
        },
        "observations": {
            "flux_loops": {"points": [[1.0, 0.0]], "quantity": "magnetic_flux", "unit": "Wb"}
        },
    }


def test_analytic_uniform_field_flux_has_explicit_2pi_conversion():
    # psi=Bz*R^2/2 with Bz=2 T; single-turn linked flux=pi*R^2*Bz.
    d = diagnostic_input()
    p = diagnose(d["equilibrium"], d["R"], d["Z"], d["observations"])
    np.testing.assert_allclose(p["flux_loops"], [2 * np.pi], rtol=1e-14)
    assert p["units"]["flux_loops"] == "Wb"
    d["observations"]["flux_loops"].update(quantity="raw_psi", unit="Wb/rad")
    np.testing.assert_allclose(
        diagnose(d["equilibrium"], d["R"], d["Z"], d["observations"])["flux_loops"],
        [1.0],
        rtol=1e-14,
    )
    d["equilibrium"]["psi_unit"] = "Wb"
    d["observations"]["flux_loops"].update(quantity="magnetic_flux", unit="Wb")
    np.testing.assert_allclose(
        diagnose(d["equilibrium"], d["R"], d["Z"], d["observations"])["flux_loops"],
        [1.0],
        rtol=1e-14,
    )


@pytest.mark.parametrize(
    "observation_request",
    [
        {},
        {"unknown": {}},
        {"flux_loops": {"points": [[1.0, 0.0]]}},
        {"thomson": {"points": [[1.0, 0.0]], "density": {"unit": "m^-3"}}},
    ],
)
def test_invalid_observation_requests_rejected(observation_request):
    d = diagnostic_input()
    d["observations"] = observation_request
    with pytest.raises(ValueError):
        diagnose(d["equilibrium"], d["R"], d["Z"], d["observations"])


def test_missing_requested_channel_never_drops_from_residual():
    obs = {"flux_loops": {"values": [1.0, 2.0]}, "thomson": {"p_perp": {"values": [3.0]}}}
    with pytest.raises(ValueError, match="p_perp"):
        reduce(predicted={"flux_loops": [1.0, 2.0], "thomson": {}}, observations=obs)


def test_units_must_match_without_implicit_rescaling():
    with pytest.raises(ValueError, match="unit"):
        reduce(
            predicted={"flux_loops": [1.0], "units": {"flux_loops": "Wb/rad"}},
            observations={"flux_loops": {"values": [1.0], "unit": "Wb"}},
        )


def test_failed_trial_keeps_dimension_and_short_circuits_diagnostics():
    calls = []
    obs = {"flux_loops": {"values": [1.0, 2.0, 3.0]}}
    result = trial(
        params={"a": 1.0},
        observations=obs,
        solver_config={"r_grid": [0.0], "z_grid": [0.0]},
        equilibrium_solver=lambda _: {"converged": False, "failure_reason": "iteration limit"},
        diagnostic_evaluator=lambda _: calls.append("bad"),
        residual_reducer=reduce,
    )
    assert result["residuals"].shape == (3,)
    assert not calls
    assert result["failure_reason"] == "iteration limit"
    assert not result["valid"]


@pytest.mark.parametrize(
    "method,bounds,initial",
    [
        ("bad", {"a": (0.0, 2.0)}, {"a": 1.0}),
        ("least_squares", {"a": (2.0, 0.0)}, {"a": 1.0}),
        ("least_squares", {"a": (0.0, np.inf)}, {"a": 1.0}),
        ("least_squares", {"a": (0.0, 2.0)}, {"a": 3.0}),
    ],
)
def test_invalid_optimizer_controls_never_call_science(method, bounds, initial):
    calls = []

    def port(**kw):
        calls.append(kw)
        return {
            "residuals": np.ones(2),
            "chi2": 2.0,
            "failure_reason": None,
            "equilibrium": {"converged": True},
        }

    with pytest.raises(ValueError):
        optimize(initial_params=initial, bounds=bounds, method=method, trial_evaluator=port)
    assert not calls


def test_failed_zero_chi2_never_becomes_best():
    def port(*, params):
        failed = params["a"] < 0.5
        r = np.array([0.0, 0.0]) if failed else np.array([params["a"] - 1.0, 0.2])
        return {
            "residuals": r,
            "chi2": float(r @ r),
            "failure_reason": "failed" if failed else None,
            "equilibrium": {"converged": not failed},
            "valid": not failed,
        }

    def lhs(**_):
        return {"initial_samples": [{"a": 0.1}, {"a": 1.2}]}

    result = optimize(
        initial_params={"a": 1.0},
        bounds={"a": (0.0, 2.0)},
        method="least_squares",
        trial_evaluator=port,
        lhs_sampler=lhs,
        n_initial_samples=2,
    )
    assert result["best_parameters"]["a"] >= 0.5
    assert result["equilibrium"]["converged"]
    assert result["chi2"] >= 0.04 - 1e-14


def test_real_picard_forward_recovers_two_physical_parameters_from_analytic_observations():
    import importlib.util
    from pathlib import Path

    spec = importlib.util.spec_from_file_location(
        "physical_recovery",
        Path(__file__).resolve().parents[1] / "fixtures/inference/anisotropic_recovery.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.run()
    assert result["failed_trials"] > 0


@pytest.mark.parametrize("which", ["nan", "shape", "chi2", "missing"])
def test_invalid_trial_contract_propagates_instead_of_becoming_physical_failure(which):
    reduced = {"residual_vector": [1.0, 2.0], "chi2": 5.0}
    if which == "nan":
        reduced["residual_vector"] = [np.nan, 2.0]
    if which == "shape":
        reduced["residual_vector"] = [1.0]
    if which == "chi2":
        reduced["chi2"] = 1.0
    if which == "missing":
        reduced = {}
    with pytest.raises(ValueError):
        trial(
            params={},
            observations={"flux_loops": {"values": [1.0, 2.0]}},
            solver_config={"r_grid": [0.0], "z_grid": [0.0]},
            equilibrium_solver=lambda _: {"converged": True},
            diagnostic_evaluator=lambda _: {},
            residual_reducer=lambda **_: reduced,
        )


def test_success_failure_success_keeps_shape_and_records_numerical_port():
    obs = {"flux_loops": {"values": [1.0, 2.0]}}

    def forward(payload):
        if payload["params"]["a"] < 0:
            raise FloatingPointError("firehose")
        return {"converged": True, "a": payload["params"]["a"]}

    records = [
        trial(
            params={"a": a},
            observations=obs,
            solver_config={"r_grid": [0.0], "z_grid": [0.0]},
            equilibrium_solver=forward,
            diagnostic_evaluator=lambda p: {"flux_loops": [p["equilibrium"]["a"]] * 2},
            residual_reducer=reduce,
        )
        for a in [1.0, -1.0, 2.0]
    ]
    assert [r["valid"] for r in records] == [True, False, True]
    assert all(r["residuals"].shape == (2,) for r in records)
    assert records[1]["exception_type"] == "FloatingPointError"
    assert records[1]["failed_port"] == "equilibrium_solver"


def test_inputs_are_deep_copied_before_injected_ports():
    config = {"r_grid": np.zeros((2, 2)), "z_grid": np.zeros((2, 2)), "nested": {"x": [1.0]}}
    params = {"a": [1.0]}
    observations = {"flux_loops": {"values": [1.0, 2.0]}}
    before = deepcopy((params, observations, config))

    def forward(payload):
        payload["nested"]["x"][0] = 7
        payload["r_grid"][:] = 3
        payload["params"]["a"][0] = 9
        return {"converged": True}

    trial(
        params=params,
        observations=observations,
        solver_config=config,
        equilibrium_solver=forward,
        diagnostic_evaluator=lambda p: {"flux_loops": [1.0, 2.0]},
        residual_reducer=reduce,
    )
    assert (
        params == before[0]
        and observations == before[1]
        and config["nested"] == before[2]["nested"]
    )
    np.testing.assert_array_equal(config["r_grid"], before[2]["r_grid"])


def test_budget_includes_finite_differences_and_fresh_recheck():
    calls = []

    def port(*, params):
        calls.append(params.copy())
        r = np.array([np.exp(params["a"]) - 3.0, 0.1])
        return {
            "chi2": float(r @ r),
            "residuals": r,
            "equilibrium": {"converged": True},
            "failure_reason": None,
        }

    result = optimize(
        initial_params={"a": 0.0},
        bounds={"a": (-2.0, 2.0)},
        method="least_squares",
        trial_evaluator=port,
        max_evaluations=5,
    )
    assert result["scientific_evaluations"] == len(calls) <= 5
    assert not result["converged"] and result["forward_converged"]
    assert "budget" in result["failure_reason"]
    assert calls[-1] == result["best_parameters"]


def test_all_failed_states_never_produce_a_best_fit():
    def port(*, params):
        return {
            "residuals": np.zeros(2),
            "chi2": 0.0,
            "equilibrium": {"converged": False},
            "failure_reason": "not converged",
        }

    result = optimize(
        initial_params={"a": 1.0},
        bounds={"a": (0.0, 2.0)},
        method="least_squares",
        trial_evaluator=port,
        max_evaluations=20,
    )
    assert result["best_parameters"] is None and result["best_valid_trial"] is None
    assert not result["converged"] and not result["forward_converged"]
    assert result["optimizer_converged"]  # stopping a constant penalty is not physics success
    assert result["chi2"] == 2e24 and result["residual_vector"].shape == (2,)


@pytest.mark.parametrize(
    "change",
    [{"turns": 2}, {"reference": 0.0}, {"unit": "T"}, {"quantity": "guess"}, {"points": []}],
)
def test_unsupported_flux_semantics_are_not_silently_ignored(change):
    d = diagnostic_input()
    d["observations"]["flux_loops"].update(change)
    with pytest.raises(ValueError):
        diagnose(d["equilibrium"], d["R"], d["Z"], d["observations"])


@pytest.mark.parametrize(
    "control",
    [
        {"fit_keys": []},
        {"fit_keys": ["a", "a"]},
        {"max_evaluations": True},
        {"max_evaluations": 2},
        {"n_initial_samples": 0},
        {"n_initial_samples": 1.5},
        {"n_initial_samples": 200},
        {"failure_penalty": np.inf},
        {"residual_size": 0},
    ],
)
def test_all_static_invalid_controls_precede_scientific_calls(control):
    calls = []
    with pytest.raises(ValueError):
        optimize(
            initial_params={"a": 1.0},
            bounds={"a": (0.0, 2.0)},
            method="least_squares",
            trial_evaluator=lambda **kw: calls.append(kw),
            **control,
        )
    assert not calls


def test_out_of_bounds_lhs_rejected_before_any_trial():
    calls = []
    with pytest.raises(ValueError, match="LHS samples"):
        optimize(
            initial_params={"a": 1.0},
            bounds={"a": (0.0, 2.0)},
            method="least_squares",
            trial_evaluator=lambda **kw: calls.append(kw),
            lhs_sampler=lambda **_: {"initial_samples": [{"a": 1.0}, {"a": 3.0}]},
            n_initial_samples=2,
        )
    assert not calls


def test_minimize_valid_terminal_is_same_params_state_and_residual():
    def port(*, params):
        r = np.array([params["a"] - 1.0, 0.2])
        return {
            "residuals": r,
            "chi2": float(r @ r),
            "equilibrium": {"converged": True, "a": params["a"]},
            "failure_reason": None,
        }

    result = optimize(
        initial_params={"a": 0.5}, bounds={"a": (0.0, 2.0)}, method="minimize", trial_evaluator=port
    )
    assert result["converged"]
    assert (
        result["best_parameters"]["a"]
        == result["equilibrium"]["a"]
        == result["optimizer_summary"]["parameters"]["a"]
    )
    np.testing.assert_allclose(
        result["residual_vector"], [result["best_parameters"]["a"] - 1.0, 0.2], rtol=0.0, atol=0.0
    )


def test_bilinear_manufactured_nonmutation_and_density_temperature_units():
    d = diagnostic_input()
    R, Z = d["R"], d["Z"]
    d["equilibrium"]["profiles"].update(density=2 + R + Z, electron_temperature=10 + R - 2 * Z)
    d["equilibrium"]["profile_units"].update(density="m^-3", electron_temperature="eV")
    points = [[0.25, 0.4], [2.0, -1.0]]
    d["observations"] = {
        "thomson": {
            "points": points,
            "density": {"unit": "m^-3"},
            "electron_temperature": {"unit": "eV"},
        }
    }
    before = deepcopy(d)
    p = diagnose(d["equilibrium"], d["R"], d["Z"], d["observations"])
    np.testing.assert_allclose(p["thomson"]["density"], [2.65, 3.0], rtol=1e-14)
    np.testing.assert_allclose(p["thomson"]["electron_temperature"], [9.45, 14.0], rtol=1e-14)
    np.testing.assert_array_equal(
        d["equilibrium"]["profiles"]["density"], before["equilibrium"]["profiles"]["density"]
    )


def test_explicit_failure_port_valueerror_is_a_contract_error():
    with pytest.raises(ValueError, match="bad contract"):
        trial(
            params={},
            observations={"flux_loops": {"values": [1.0, 2.0]}},
            solver_config={"r_grid": [0.0], "z_grid": [0.0]},
            equilibrium_solver=lambda _: (_ for _ in ()).throw(ValueError("bad contract")),
            diagnostic_evaluator=lambda _: None,
            residual_reducer=reduce,
        )


def test_numeric_callback_exceptions_are_counted_and_never_ranked():
    calls = []

    def scientific(*, params):
        calls.append(params["a"])
        raise FloatingPointError("synthetic overflow of numerical callback")

    result = optimize(
        initial_params={"a": 1.0},
        bounds={"a": (0.0, 2.0)},
        method="least_squares",
        trial_evaluator=scientific,
        residual_size=2,
        max_evaluations=7,
    )
    assert result["scientific_evaluations"] == len(calls)
    assert 1 <= len(calls) <= 7
    assert len(result["evaluation_log"]) == len(calls)
    assert all(not row["valid"] for row in result["evaluation_log"])
    assert result["best_parameters"] is None and result["best_valid_trial"] is None
    assert result["residual_vector"].shape == (2,) and not result["converged"]
