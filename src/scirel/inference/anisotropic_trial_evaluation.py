"""Dimension-preserving, typed evaluation through caller-owned scientific ports."""
from __future__ import annotations
from collections.abc import Mapping
from copy import deepcopy
import numpy as np
from scirel.diagnostics.observation_residuals import _observation_layout


def _size(value):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)) or value < 1:
        raise ValueError('residual_size must be a positive integer')
    return int(value)


def _residual_record(reduced, size):
    if not isinstance(reduced, Mapping):
        raise ValueError('residual_reducer must return a mapping')
    vector = np.asarray(reduced.get('residual_vector'), dtype=float)
    if vector.shape != (size,) or not np.all(np.isfinite(vector)):
        raise ValueError(f'residual vector must be finite with fixed shape ({size},)')
    with np.errstate(over='ignore', invalid='ignore'):
        norm = float(vector @ vector)
    chi2 = float(reduced.get('chi2', np.nan))
    if not np.isfinite(norm) or not np.isfinite(chi2) or chi2 < 0 or not np.isclose(chi2, norm, rtol=1e-12, atol=0.):
        raise ValueError('chi2 must be finite and equal the squared residual norm')
    return vector.copy(), norm


def evaluate_anisotropic_trial(*, params, observations, solver_config,
        equilibrium_solver, diagnostic_evaluator, residual_reducer,
        residual_size=None, failure_penalty=1.e12):
    """Validate a trial or return a finite same-dimension numerical-failure record.

    Standard observation layout determines N before calling science. Custom
    diagnostic/reducer contracts must explicitly declare residual_size. Contract
    ValueError/TypeError/KeyError propagate; numerical ArithmeticError/RuntimeError
    are recorded separately from a forward state reporting nonconvergence.
    Caller mappings/arrays are deep-copied before port invocation.
    """
    if not all(isinstance(x, Mapping) for x in (params, observations, solver_config)):
        raise ValueError('params, observations and solver_config must be mappings')
    if not all(callable(x) for x in (equilibrium_solver, diagnostic_evaluator, residual_reducer)):
        raise ValueError('scientific ports must be callable')
    if not {'r_grid', 'z_grid'} <= set(solver_config):
        raise ValueError('solver_config must supply r_grid and z_grid')
    n = sum(values.size for _, _, values, _, _ in _observation_layout(observations)) if residual_size is None else _size(residual_size)
    penalty = float(failure_penalty)
    if not np.isfinite(penalty) or penalty <= 0 or not np.isfinite(penalty*penalty*n):
        raise ValueError('failure_penalty must be positive with a finite squared N-vector norm')
    equilibrium = None
    port = 'equilibrium_solver'
    def failed(kind, reason, error_type=None):
        residuals = np.full(n, penalty, dtype=float)
        return {'params':deepcopy(dict(params)), 'residuals':residuals,
                'chi2':float(residuals@residuals), 'equilibrium':equilibrium,
                'failure_reason':str(reason), 'valid':False, 'status':kind,
                'failed_port':port, 'exception_type':error_type}
    try:
        payload = deepcopy(dict(solver_config));payload['params'] = deepcopy(dict(params))
        equilibrium = equilibrium_solver(payload)
        if not isinstance(equilibrium, Mapping) or not isinstance(equilibrium.get('converged'), (bool, np.bool_)):
            raise ValueError('equilibrium_solver must return a mapping with boolean converged')
        if not equilibrium['converged']:
            return failed('forward_nonconvergence', equilibrium.get('failure_reason') or 'equilibrium solver did not converge')
        if equilibrium.get('failure_reason'):
            raise ValueError('converged equilibrium must not carry a failure_reason')
        port = 'diagnostic_evaluator'
        predicted = diagnostic_evaluator({'equilibrium':deepcopy(equilibrium),
            'R':deepcopy(solver_config['r_grid']), 'Z':deepcopy(solver_config['z_grid']),
            'observations':deepcopy(observations)})
        port = 'residual_reducer'
        reduced = residual_reducer(predicted=predicted, observations=deepcopy(observations))
        residuals, chi2 = _residual_record(reduced, n)
    except (ArithmeticError, RuntimeError) as exc:
        return failed('numerical_failure', exc, type(exc).__name__)
    return {'params':deepcopy(dict(params)), 'chi2':chi2, 'residuals':residuals,
            'equilibrium':equilibrium, 'failure_reason':None, 'valid':True,
            'status':'valid', 'failed_port':None, 'exception_type':None}

__all__ = ['evaluate_anisotropic_trial']
