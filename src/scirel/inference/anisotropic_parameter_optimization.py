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
    """Fit bounded parameters without ranking a failed trial as a solution.

    Parameters
    ----------
    initial_params : mapping
        Complete initial parameter values [per parameter contract]. Fitted
        values must be finite and lie within their bounds; non-fitted values
        are deep-copied unchanged.
    bounds : mapping
        Mapping from parameter keys to finite increasing ``(low, high)``
        pairs [same as the parameters]. Every supplied interval is validated.
    method : {'least_squares', 'minimize'}
        Local optimizer selector [identifier]. ``least_squares`` minimizes the
        fixed residual vector; ``minimize`` uses L-BFGS-B on its squared norm.
    trial_evaluator : callable
        Physical-evaluation port ``trial_evaluator(*, params) -> mapping``
        [residuals are dimensionless; state follows the scientific contract].
        It must supply ``residuals`` and ``chi2``. ``equilibrium`` is required
        for a valid trial: when present it must be a mapping whose
        ``converged`` value is True. A missing or nonconverged equilibrium
        makes the trial invalid. ``failure_reason`` may be omitted or None when
        valid. If ``valid`` is present, it must be Boolean.
    fit_keys : sequence of str or None, optional
        Nonempty duplicate-free ordered subset of keys present in both
        mappings [identifier]. If None, ``bounds`` insertion order selects all
        fitted keys. The default is None.
    lhs_sampler : callable or None, optional
        Latin-hypercube design port [parameter units]. It is required when
        ``n_initial_samples`` is set and must accept keyword arguments
        ``bounds``, ``n_samples``, ``seed`` and ``fit_keys``. It returns a
        mapping whose ``initial_samples`` contain exactly the fitted keys. The
        default is None.
    n_initial_samples : int or None, optional
        Number of initial LHS evaluations [count]. It must be from 1 through
        ``max_evaluations - 3``. The default is None, which disables LHS.
    seed : object or None, optional
        Sampler-defined seed passed unchanged to ``lhs_sampler``
        [dimensionless]. It is unused when LHS is disabled. The default is
        None.
    residual_size : int or None, optional
        Predetermined residual count [count]. If omitted, N is taken from the
        first nonempty one-dimensional trial vector and then held fixed. The
        default is None.
    failure_penalty : float, optional
        Positive per-component penalty fed to the optimizer for an invalid
        trial [dimensionless]. N times its square must remain finite. The
        default is 1e12.
    max_evaluations : int, optional
        Upper bound on actual scientific trial calls, including LHS,
        optimizer differences and terminal validation [count]. It must be at
        least 3. The default is 200.

    Returns
    -------
    best_parameters : dict or None
        Revalidated optimizer terminal point, or a freshly revalidated
        historical valid candidate [parameter units]. It is None when no valid
        candidate exists.
    chi2 : float
        Squared residual norm of the returned state, or the failed-state
        penalty norm [dimensionless].
    residual_vector : ndarray of float64, shape (N,)
        Residuals from the same revalidated state as ``best_parameters``, or a
        same-size penalty vector [dimensionless].
    converged : bool
        Whether the optimizer succeeded and its freshly evaluated terminal
        point is valid [boolean]. A fallback is never reported as converged.
    forward_converged : bool
        Whether a valid forward state is returned, even if the optimizer did
        not converge [boolean].
    optimizer_converged : bool
        The optimizer library's success flag [boolean]. It may be True while
        the terminal forward state is invalid, so it is not physical success.
    equilibrium : mapping or None
        Forward state from the same revalidation as the returned residuals
        [mixed]. It is None when no valid candidate exists.
    evaluation_log : list of dict, length N_eval
        Every actual trial record with parameters, ``chi2``, validity, failure
        reason and source [mixed]. Sources are ``latin_hypercube``,
        ``optimizer``, ``terminal`` or ``best_valid_recheck``.
    failure_reason : str or None
        Reason for budget exhaustion, numerical failure, terminal failure or
        optimizer stop [identifier]. It is None only when ``converged`` is
        True.
    optimizer_summary : dict or None
        Method, success, status, message, ``nfev`` and optimizer terminal
        parameters [mixed state and counts]. SciPy's ``nfev`` is not the total
        scientific call count; this is None when no optimizer result exists.
    best_valid_trial : dict or None
        Lowest-chi2 valid trial seen during the run [mixed]. It is an
        observation record and must not be assigned the returned terminal
        point's convergence state.
    scientific_evaluations : int
        Number of actual trial calls [count]. It does not exceed
        ``max_evaluations`` and includes numerical differences.
    max_evaluations : int
        Validated scientific-call ceiling for this run [count].
    valid_trial_count : int
        Number of valid trial records in the evaluation log [count].
    residual_size : int
        Fixed residual-vector length for the run [count].
    identifiability : str
        Fixed value ``not_established`` [identifier]; a local optimizer stop
        is not an identifiability proof.

    Raises
    ------
    ValueError
        If a method, mapping, bound, fitted initial value, key set, LHS design,
        budget, failure penalty or trial residual record is invalid, or a
        numeric conversion raises ``ValueError``. Invalid optimizer proposals
        are also rejected rather than evaluated outside the bounds.
    TypeError
        If a numeric conversion or injected port raises ``TypeError``.
    KeyError
        If a required key is absent from an input or an injected port's
        mapping contract.
    ArithmeticError
        If an arithmetic failure escapes before a residual size is
        established. Once N is known, numerical trial failures are recorded and
        supplied to the optimizer as penalties.
    FloatingPointError
        A subclass of ArithmeticError with the same propagation and recording
        behavior.
    RuntimeError
        If a runtime failure escapes before N is established or from the LHS
        sampler. Numerical trial RuntimeErrors with known N are recorded as
        failed trials.

    See Also
    --------
    evaluate_anisotropic_trial : Validate one fixed-size physical trial.
    sample_latin_hypercube : Generate a deterministic bounded initial design.
    scirel.inference.direct_anisotropic_inversion : Compose diagnostics,
        trials and this optimizer into a physical inversion workflow.

    Notes
    -----
    This is a bounded local optimizer, not a global search, confidence
    calculation or identifiability proof. All static controls are validated
    before a scientific call. Optional LHS trials are evaluated in order; the
    valid sample with the lowest ``chi2`` becomes the optimizer start, while
    the submitted initial point is retained if no LHS sample is valid. The
    scientific-call budget counts LHS, optimizer evaluations, numerical
    differences and fresh terminal validation. An invalid trial supplies a
    fixed-N penalty to the optimizer and never becomes ``best_valid_trial``.
    A normally returned optimizer point is always evaluated again; an invalid
    terminal point can only fall back to a freshly revalidated historical
    valid candidate, with ``converged=False``. The failure penalty is only an
    optimization control and is not a physical solution.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.inference import optimize_anisotropic_parameters
    >>> def trial(*, params):
    ...     residuals = np.array([params['x'] - 3.0])
    ...     return {'chi2': float(residuals @ residuals), 'residuals': residuals, 'equilibrium': {'converged': True}, 'failure_reason': None}
    >>> r = optimize_anisotropic_parameters(initial_params={'x': 0.0, 'fixed': 7.0}, bounds={'x': (-5.0, 5.0)}, fit_keys=['x'], method='least_squares', trial_evaluator=trial)
    >>> assert abs(r['best_parameters']['x'] - 3.0) < 1e-6
    >>> assert r['best_parameters']['fixed'] == 7.0 and r['converged']
    >>> assert r['chi2'] == min(e['chi2'] for e in r['evaluation_log'])
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
