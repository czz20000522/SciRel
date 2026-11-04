"""Bounded direct inversion with optional Latin-hypercube initialization."""
from __future__ import annotations
import numpy as np

def optimize_anisotropic_parameters(*, initial_params, bounds, method, trial_evaluator, fit_keys=None, lhs_sampler=None, n_initial_samples=None, seed=None):
    """Optimize a trial-evaluator port while preserving the source fallback record."""
    keys = list(bounds) if fit_keys is None else list(fit_keys)
    x0 = np.asarray([float(initial_params[key]) for key in keys], dtype=float)
    lower = np.asarray([float(bounds[key][0]) for key in keys], dtype=float)
    upper = np.asarray([float(bounds[key][1]) for key in keys], dtype=float)
    evaluations = []
    best = {'chi2': np.inf, 'params': dict(initial_params), 'residuals': None, 'equilibrium': None}

    def record(params, source):
        trial = trial_evaluator(params=params)
        evaluations.append({'params': dict(params), 'chi2': trial['chi2'], 'failure_reason': trial['failure_reason'], 'source': source})
        if trial['chi2'] < best['chi2']:
            best.update({'chi2': trial['chi2'], 'params': dict(params), 'residuals': trial['residuals'], 'equilibrium': trial['equilibrium']})
        return trial
    start = dict(initial_params)
    if n_initial_samples is not None:
        if lhs_sampler is None:
            raise ValueError('lhs_sampler is required when n_initial_samples is supplied')
        lhs_records = []
        for sample in lhs_sampler(bounds=bounds, n_samples=int(n_initial_samples), seed=seed, fit_keys=keys)['initial_samples']:
            params = dict(initial_params)
            params.update(sample)
            trial = record(params, 'latin_hypercube')
            lhs_records.append((dict(params), trial))
        best_lhs_params, _ = min(lhs_records, key=lambda item: item[1]['chi2'])
        start.update({key: best_lhs_params[key] for key in keys})
        x0 = np.asarray([float(start[key]) for key in keys], dtype=float)

    def evaluate(values):
        params = dict(start)
        params.update({key: float(value) for key, value in zip(keys, values)})
        return record(params, 'optimizer')['residuals']
    result = None
    failure_reason = None
    try:
        from scipy.optimize import least_squares, minimize
        if method == 'least_squares':
            result = least_squares(evaluate, x0, bounds=(lower, upper))
        elif method == 'minimize':

            def objective(values):
                residuals = evaluate(values)
                return float(np.dot(residuals, residuals))
            result = minimize(objective, x0, bounds=list(zip(lower, upper)))
        else:
            raise ValueError("method must be 'least_squares' or 'minimize'")
    except Exception as exc:
        failure_reason = str(exc)
        evaluate(x0)
    converged = bool(result is not None and getattr(result, 'success', False) and (best['equilibrium'] is not None) and best['equilibrium']['converged'])
    return {'best_parameters': best['params'], 'chi2': float(best['chi2']), 'residual_vector': np.asarray(best['residuals'], dtype=float), 'converged': converged, 'equilibrium': best['equilibrium'], 'evaluation_log': evaluations, 'failure_reason': failure_reason, 'optimizer_summary': None if result is None else {'method': method, 'success': bool(getattr(result, 'success', False)), 'status': getattr(result, 'status', None), 'message': str(getattr(result, 'message', '')), 'nfev': getattr(result, 'nfev', None)}}
run = optimize_anisotropic_parameters
__all__ = ['optimize_anisotropic_parameters']
