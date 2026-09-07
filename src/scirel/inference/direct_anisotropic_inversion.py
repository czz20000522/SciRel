"""Standalone orchestration for direct anisotropic parameter inversion."""
from __future__ import annotations
from functools import partial
import hashlib
from pathlib import Path
import numpy as np

def _mapping(value, name):
    if not isinstance(value, dict):
        raise ValueError(f'{name} must be a mapping')
    return value

def _callable_port(value, name):
    if not callable(value):
        raise ValueError(f'{name} must be a callable cross-node port')
    return value

def run_graph(inputs, *, operator_loader):
    """Dispatch YAML-declared operators with explicit N6/N9 caller ports."""
    inputs = _mapping(inputs, 'inputs')
    initial_params = dict(_mapping(inputs.get('initial_params'), 'initial_params'))
    bounds = dict(_mapping(inputs.get('bounds'), 'bounds'))
    observations = _mapping(inputs.get('observations'), 'observations')
    solver_config = dict(_mapping(inputs.get('solver_config'), 'solver_config'))
    equilibrium_solver = _callable_port(inputs.get('equilibrium_solver'), 'equilibrium_solver')
    diagnostic_evaluator = _callable_port(inputs.get('diagnostic_evaluator'), 'diagnostic_evaluator')
    if 'method' not in inputs:
        raise ValueError('method is required by task_graph.yaml')
    if not isinstance(inputs['method'], str):
        raise ValueError('method must be a string')
    residual_reducer = operator_loader('scirel.diagnostics.observation_residuals', 'reduce_observation_residuals')

    def _evaluate_trial(*, params, observations, solver_config, equilibrium_solver, diagnostic_evaluator, residual_reducer):
        try:
            equilibrium_inputs = dict(solver_config)
            equilibrium_inputs['params'] = dict(params)
            equilibrium = equilibrium_solver(equilibrium_inputs)
            predicted = diagnostic_evaluator({'equilibrium': equilibrium, 'R': solver_config['r_grid'], 'Z': solver_config['z_grid'], 'observations': observations})
            reduced = residual_reducer(predicted=predicted, observations=observations)
            residuals = np.asarray(reduced['residual_vector'], dtype=float)
            chi2 = float(reduced['chi2'])
            converged = equilibrium['converged']
            if not isinstance(converged, (bool, np.bool_)):
                raise ValueError('equilibrium solver must return boolean converged')
            failure_reason = None if bool(converged) else str(equilibrium.get('failure_reason') or 'equilibrium solver did not converge')
        except Exception as exc:
            equilibrium = None
            residuals = np.full(1, 1000000000000.0, dtype=float)
            chi2 = float(np.dot(residuals, residuals))
            failure_reason = str(exc)
        return {'params': dict(params), 'chi2': chi2, 'residuals': residuals, 'equilibrium': equilibrium, 'failure_reason': failure_reason}
    trial_evaluator = _evaluate_trial
    optimizer = operator_loader('scirel.inference.anisotropic_parameter_optimization', 'optimize_anisotropic_parameters')
    trial_port = partial(trial_evaluator, observations=observations, solver_config=solver_config, equilibrium_solver=equilibrium_solver, diagnostic_evaluator=diagnostic_evaluator, residual_reducer=residual_reducer)
    arguments = {'initial_params': initial_params, 'bounds': bounds, 'method': inputs['method'], 'trial_evaluator': trial_port, 'fit_keys': inputs.get('fit_keys'), 'n_initial_samples': inputs.get('n_initial_samples'), 'seed': inputs.get('seed')}
    if inputs.get('n_initial_samples') is not None:
        arguments['lhs_sampler'] = operator_loader('scirel.inference.latin_hypercube_sampling', 'sample_latin_hypercube')
    result = optimizer(**arguments)
    if isinstance(result, dict) and (not result.get('converged', False)) and (not result.get('failure_reason')):
        equilibrium = result.get('equilibrium')
        if isinstance(equilibrium, dict) and (not equilibrium.get('converged', False)):
            reason = equilibrium.get('failure_reason') or 'equilibrium solver did not converge'
        else:
            reason = 'parameter optimizer did not converge'
        result = dict(result)
        result['failure_reason'] = str(reason)
    return result

def solve_direct_anisotropic_inversion(inputs=None, **kwargs):
    from scirel._composition import compose
    from scirel.diagnostics.observation_residuals import reduce_observation_residuals as _dependency_0
    from scirel.inference.anisotropic_parameter_optimization import optimize_anisotropic_parameters as _dependency_1
    from scirel.inference.latin_hypercube_sampling import sample_latin_hypercube as _dependency_2
    return compose(run_graph, inputs, kwargs, {'operator_loader': {'scirel.diagnostics.observation_residuals': _dependency_0, 'scirel.inference.anisotropic_parameter_optimization': _dependency_1, 'scirel.inference.latin_hypercube_sampling': _dependency_2}})
__all__ = ['solve_direct_anisotropic_inversion']
