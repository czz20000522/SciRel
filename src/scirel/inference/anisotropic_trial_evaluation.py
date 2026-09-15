"""Evaluate one anisotropic inversion trial through caller-owned solver ports."""

from __future__ import annotations

import numpy as np


def evaluate_anisotropic_trial(
    *,
    params,
    observations,
    solver_config,
    equilibrium_solver,
    diagnostic_evaluator,
    residual_reducer,
):
    """Return a penalty record when either injected nested port fails."""
    try:
        equilibrium_inputs = dict(solver_config)
        equilibrium_inputs["params"] = dict(params)
        equilibrium = equilibrium_solver(equilibrium_inputs)
        predicted = diagnostic_evaluator(
            {
                "equilibrium": equilibrium,
                "R": solver_config["r_grid"],
                "Z": solver_config["z_grid"],
                "observations": observations,
            }
        )
        reduced = residual_reducer(predicted=predicted, observations=observations)
        residuals = np.asarray(reduced["residual_vector"], dtype=float)
        chi2 = float(reduced["chi2"])
        failure_reason = None if equilibrium["converged"] else equilibrium["failure_reason"]
    except Exception as exc:
        equilibrium = None
        residuals = np.full(1, 1.0e12, dtype=float)
        chi2 = float(np.dot(residuals, residuals))
        failure_reason = str(exc)
    return {
        "params": dict(params),
        "chi2": chi2,
        "residuals": residuals,
        "equilibrium": equilibrium,
        "failure_reason": failure_reason,
    }


__all__ = ["evaluate_anisotropic_trial"]
