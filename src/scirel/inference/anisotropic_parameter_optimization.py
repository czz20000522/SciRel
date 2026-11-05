"""Budgeted bounded optimization around caller-owned scientific evaluations."""

from __future__ import annotations
from collections.abc import Mapping
from copy import deepcopy
import numpy as np
from .anisotropic_trial_evaluation import _size, _residual_record


class _BudgetExhausted(RuntimeError):
    pass


def optimize_anisotropic_parameters(
    *,
    initial_params,
    bounds,
    method,
    trial_evaluator,
    fit_keys=None,
    lhs_sampler=None,
    n_initial_samples=None,
    seed=None,
    residual_size=None,
    failure_penalty=1.0e12,
    max_evaluations=200,
):
    """Fit bounded parameters, never ranking a failed forward state as a solution.

    Bounds and controls reject before any scientific call. Failed numerical trials
    provide a fixed-N finite penalty to the optimizer and remain excluded from
    best-valid ranking. Budget counts all scientific calls including LHS, finite
    differences and fresh terminal validation (two slots reserved for terminal
    and valid fallback). Contract errors propagate, without a hidden retry.

    A successful optimizer's actual terminal point is freshly checked and returned;
    best_valid_trial separately records the lowest valid chi2 ever observed. A
    fresh fallback best is a useful partial result, never optimizer convergence.
    No optimizer stop implies identifiability, a global optimum or a good fit.
    """
    if method not in ("least_squares", "minimize"):
        raise ValueError("method must be 'least_squares' or 'minimize'")
    if not isinstance(initial_params, Mapping) or not isinstance(bounds, Mapping) or not bounds:
        raise ValueError("initial_params and nonempty bounds must be mappings")
    if not callable(trial_evaluator):
        raise ValueError("trial_evaluator must be callable")
    keys = list(bounds) if fit_keys is None else list(fit_keys)
    if not keys or any(not isinstance(k, str) for k in keys) or len(keys) != len(set(keys)):
        raise ValueError("fit_keys must contain distinct parameter names")
    if not set(keys) <= set(bounds) or not set(keys) <= set(initial_params):
        raise ValueError("every fit key must be present in bounds and initial_params")
    checked = {}
    for key, pair in bounds.items():
        try:
            values = np.asarray(pair, dtype=float)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"invalid bounds for {key}") from exc
        if values.shape != (2,) or not np.all(np.isfinite(values)) or values[0] >= values[1]:
            raise ValueError(f"finite increasing two-element bounds required for {key}")
        checked[key] = values
    lower, upper = np.array([checked[k] for k in keys]).T
    x0 = np.asarray([initial_params[k] for k in keys], dtype=float)
    if (
        x0.shape != lower.shape
        or not np.all(np.isfinite(x0))
        or np.any(x0 < lower)
        or np.any(x0 > upper)
    ):
        raise ValueError("initial fitted parameters must be finite and within bounds")
    if (
        isinstance(max_evaluations, (bool, np.bool_))
        or not isinstance(max_evaluations, (int, np.integer))
        or max_evaluations < 3
    ):
        raise ValueError("max_evaluations must be an integer >= 3")
    n = None if residual_size is None else _size(residual_size)
    penalty = float(failure_penalty)
    if not np.isfinite(penalty) or penalty <= 0 or not np.isfinite(penalty * penalty):
        raise ValueError("failure_penalty must be positive with finite squared norm")
    if n is not None and not np.isfinite(penalty * penalty * n):
        raise ValueError("failure_penalty vector squared norm must be finite")
    if n_initial_samples is not None:
        if (
            isinstance(n_initial_samples, (bool, np.bool_))
            or not isinstance(n_initial_samples, (int, np.integer))
            or not 1 <= n_initial_samples <= max_evaluations - 3
        ):
            raise ValueError(
                "n_initial_samples must be a positive integer leaving optimizer/terminal budget"
            )
        if not callable(lhs_sampler):
            raise ValueError("lhs_sampler is required when n_initial_samples is supplied")
    # Ask the unchanged scientific sampler only after complete control validation.
    samples = []
    if n_initial_samples is not None:
        design = lhs_sampler(
            bounds=deepcopy(dict(bounds)),
            n_samples=int(n_initial_samples),
            seed=seed,
            fit_keys=keys.copy(),
        )
        raw = design.get("initial_samples") if isinstance(design, Mapping) else None
        if not isinstance(raw, (list, tuple)) or len(raw) != n_initial_samples:
            raise ValueError("lhs_sampler returned the wrong number of samples")
        for sample in raw:
            if not isinstance(sample, Mapping) or set(sample) != set(keys):
                raise ValueError("each LHS sample must contain exactly the fitted keys")
            x = np.asarray([sample[k] for k in keys], dtype=float)
            if (
                x.shape != lower.shape
                or not np.all(np.isfinite(x))
                or np.any(x < lower)
                or np.any(x > upper)
            ):
                raise ValueError("LHS samples must be finite and within bounds")
            params = deepcopy(dict(initial_params))
            params.update({k: float(v) for k, v in zip(keys, x)})
            samples.append(params)
    logs, valid_trials = [], []
    best = None

    def record(params, source, terminal=False):
        nonlocal n, best
        if len(logs) >= max_evaluations - (0 if terminal else 2):
            raise _BudgetExhausted("scientific evaluation budget exhausted")
        # Validate every optimizer proposal even if a third-party optimizer misbehaves.
        x = np.asarray([params[k] for k in keys], dtype=float)
        if not np.all(np.isfinite(x)) or np.any(x < lower) or np.any(x > upper):
            raise ValueError("optimizer proposed parameters outside finite bounds")
        try:
            raw = trial_evaluator(params=deepcopy(params))
        except (ArithmeticError, RuntimeError) as exc:
            if n is None:
                raise  # A custom callback must declare N before numerical failure.
            failed_vector = np.full(n, penalty)
            raw = {
                "residuals": failed_vector,
                "chi2": float(failed_vector @ failed_vector),
                "equilibrium": None,
                "valid": False,
                "failure_reason": f"trial numerical failure: {type(exc).__name__}: {exc}",
            }
        if not isinstance(raw, Mapping):
            raise ValueError("trial_evaluator must return a mapping")
        vector = np.asarray(raw.get("residuals"), dtype=float)
        if n is None:
            if vector.ndim != 1 or not vector.size:
                raise ValueError(
                    "first trial must provide a nonempty one-dimensional residual vector"
                )
            n = vector.size
            if not np.isfinite(penalty * penalty * n):
                raise ValueError("failure_penalty vector squared norm must be finite")
        vector, chi2 = _residual_record({"residual_vector": vector, "chi2": raw.get("chi2")}, n)
        equilibrium = raw.get("equilibrium")
        physical = (
            isinstance(equilibrium, Mapping)
            and isinstance(equilibrium.get("converged"), (bool, np.bool_))
            and bool(equilibrium["converged"])
        )
        valid = physical and not raw.get("failure_reason") and raw.get("valid", True) is not False
        if "valid" in raw and not isinstance(raw["valid"], (bool, np.bool_)):
            raise ValueError("trial valid flag must be boolean")
        valid = valid and bool(raw.get("valid", True))
        failure = (
            None if valid else str(raw.get("failure_reason") or "trial forward state is not valid")
        )
        retained = {
            "params": deepcopy(params),
            "chi2": chi2,
            "residuals": vector,
            "equilibrium": deepcopy(equilibrium),
            "failure_reason": failure,
            "valid": valid,
        }
        logs.append(
            {
                "params": deepcopy(params),
                "chi2": chi2,
                "failure_reason": failure,
                "valid": valid,
                "source": source,
            }
        )
        if valid:
            valid_trials.append(retained)
            if best is None or chi2 < best["chi2"]:
                best = retained
        return retained

    for params in samples:
        record(params, "latin_hypercube")
    start = deepcopy(dict(initial_params))
    if best is not None:
        start.update({k: best["params"][k] for k in keys})
    x0 = np.asarray([start[k] for k in keys], dtype=float)

    def evaluate(x):
        params = deepcopy(start)
        params.update({k: float(v) for k, v in zip(keys, x)})
        value = record(params, "optimizer")
        return value["residuals"] if value["valid"] else np.full(n, penalty)

    result = None
    stop_reason = None
    try:
        from scipy.optimize import least_squares, minimize

        if method == "least_squares":
            result = least_squares(evaluate, x0, bounds=(lower, upper), max_nfev=max_evaluations)
        else:

            def objective(x):
                r = evaluate(x)
                return float(r @ r)

            result = minimize(
                objective,
                x0,
                method="L-BFGS-B",
                bounds=list(zip(lower, upper)),
                options={"maxfun": max_evaluations, "maxiter": max_evaluations},
            )
    except _BudgetExhausted as exc:
        stop_reason = str(exc)
    except (ArithmeticError, RuntimeError) as exc:
        if n is None:
            raise  # No residual contract has been established; never invent N.
        stop_reason = f"optimizer numerical failure: {type(exc).__name__}: {exc}"
    terminal = None
    if result is not None:
        params = deepcopy(start)
        params.update({k: float(v) for k, v in zip(keys, result.x)})
        terminal = record(params, "terminal", terminal=True)
    selected = terminal if terminal is not None and terminal["valid"] else None
    if selected is None and best is not None:
        fallback = record(best["params"], "best_valid_recheck", terminal=True)
        if fallback["valid"]:
            selected = fallback
    optimizer_success = bool(result is not None and result.success)
    converged = bool(
        optimizer_success and terminal is not None and terminal["valid"] and selected is terminal
    )
    if not converged and stop_reason is None:
        if terminal is not None and not terminal["valid"]:
            stop_reason = terminal["failure_reason"]
        elif result is not None:
            stop_reason = f"optimizer stopped: {result.message}"
        else:
            stop_reason = "no valid optimizer terminal state"
    vector = selected["residuals"] if selected is not None else np.full(n, penalty)
    summary = (
        None
        if result is None
        else {
            "method": method,
            "success": optimizer_success,
            "status": int(result.status),
            "message": str(result.message),
            "nfev": int(result.nfev),
            "parameters": {k: float(v) for k, v in zip(keys, result.x)},
        }
    )
    return {
        "best_parameters": None if selected is None else selected["params"],
        "chi2": float(vector @ vector),
        "residual_vector": vector,
        "converged": converged,
        "forward_converged": selected is not None,
        "optimizer_converged": optimizer_success,
        "equilibrium": None if selected is None else selected["equilibrium"],
        "evaluation_log": logs,
        "failure_reason": None if converged else stop_reason,
        "optimizer_summary": summary,
        "best_valid_trial": deepcopy(best),
        "scientific_evaluations": len(logs),
        "max_evaluations": int(max_evaluations),
        "valid_trial_count": len(valid_trials),
        "residual_size": n,
        "identifiability": "not_established",
    }


run = optimize_anisotropic_parameters
__all__ = ["optimize_anisotropic_parameters"]
