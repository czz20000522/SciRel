"""Composition orchestration for direct anisotropic parameter inversion."""
from __future__ import annotations
from functools import partial
from scirel.diagnostics.observation_residuals import _observation_layout

def _mapping(value, name):
    if not isinstance(value, dict):
        raise ValueError(f'{name} must be a mapping')
    return value

def _callable_port(value, name):
    if not callable(value):
        raise ValueError(f'{name} must be a callable cross-node port')
    return value

def run_composition(inputs, *, asset_loader):
    """Bind fixed observation layout and bounded valid-trial optimization.

    Caller ports supply the physical closure and observation units. Numerical
    optimizer convergence and forward convergence are reported separately;
    neither proves a global optimum or parameter identifiability.
    """
    inputs = _mapping(inputs, 'inputs')
    initial_params = dict(_mapping(inputs.get('initial_params'), 'initial_params'))
    bounds = dict(_mapping(inputs.get('bounds'), 'bounds'))
    observations = _mapping(inputs.get('observations'), 'observations')
    residual_size = sum(values.size for _, _, values, _, _ in _observation_layout(observations))
    solver_config = dict(_mapping(inputs.get('solver_config'), 'solver_config'))
    equilibrium_solver = _callable_port(inputs.get('equilibrium_solver'), 'equilibrium_solver')
    diagnostic_evaluator = _callable_port(inputs.get('diagnostic_evaluator'), 'diagnostic_evaluator')

    def equilibrium_port(payload):
        result = equilibrium_solver(payload)
        if isinstance(result, dict) and result.get('converged') is False and not result.get('failure_reason'):
            result = dict(result)
            result['failure_reason'] = 'equilibrium solver did not converge'
        return result
    if 'method' not in inputs:
        raise ValueError('method is required by composition.yaml')
    if not isinstance(inputs['method'], str):
        raise ValueError('method must be a string')
    residual_reducer = asset_loader('scirel.diagnostics.observation_residuals', 'reduce_observation_residuals')

    trial_evaluator = asset_loader(
        'scirel.inference.anisotropic_trial_evaluation',
        'evaluate_anisotropic_trial',
    )
    optimizer = asset_loader('scirel.inference.anisotropic_parameter_optimization', 'optimize_anisotropic_parameters')
    trial_port = partial(trial_evaluator, observations=observations, solver_config=solver_config, equilibrium_solver=equilibrium_port, diagnostic_evaluator=diagnostic_evaluator, residual_reducer=residual_reducer, residual_size=residual_size, failure_penalty=inputs.get('failure_penalty', 1.e12))
    arguments = {'initial_params': initial_params, 'bounds': bounds, 'method': inputs['method'], 'trial_evaluator': trial_port, 'fit_keys': inputs.get('fit_keys'), 'n_initial_samples': inputs.get('n_initial_samples'), 'seed': inputs.get('seed'), 'residual_size': residual_size, 'failure_penalty': inputs.get('failure_penalty',1.e12), 'max_evaluations': inputs.get('max_evaluations',200)}
    if inputs.get('n_initial_samples') is not None:
        arguments['lhs_sampler'] = asset_loader('scirel.inference.latin_hypercube_sampling', 'sample_latin_hypercube')
    result = optimizer(**arguments)
    if isinstance(result, dict) and not result.get('converged', False) and not result.get('failure_reason'):
        equilibrium = result.get('equilibrium')
        if isinstance(equilibrium, dict) and not equilibrium.get('converged', False):
            reason = equilibrium.get('failure_reason') or 'equilibrium solver did not converge'
        else:
            reason = 'parameter optimizer did not converge'
        result = dict(result)
        result['failure_reason'] = str(reason)
    return result

def solve_direct_anisotropic_inversion(inputs=None, **kwargs):
    """Run a bounded direct anisotropic inversion through caller-owned ports.

    Parameters
    ----------
    inputs : mapping, optional
        Mapping containing ``initial_params``, ``bounds``, ``method``,
        ``observations``, ``solver_config``, ``equilibrium_solver`` and
        ``diagnostic_evaluator``.  Optional controls include ``fit_keys``,
        ``n_initial_samples``, ``seed``, ``failure_penalty`` and
        ``max_evaluations``.
    **kwargs
        Composition overrides passed to the public composition boundary.

    Returns
    -------
    dict
        Inversion state containing the fixed-size ``residual_vector``,
        ``best_parameters``, ``equilibrium``, ``evaluation_log``,
        ``failure_reason`` and separate ``converged``,
        ``forward_converged`` and ``optimizer_converged`` flags.  A partial
        valid candidate may be returned when optimization or a forward trial
        stops; it is not a proof of fit completion or identifiability.

    Raises
    ------
    ValueError
        If the input mapping, observation layout, ports, method, bounds or
        evaluation budget violates the declared composition contract.
    Exception
        Scientific port, diagnostic, optimizer and dependency exceptions
        propagate according to their trial or composition boundary.
    """

    from scirel._composition import compose
    from scirel.diagnostics.observation_residuals import reduce_observation_residuals as _dependency_0
    from scirel.inference.anisotropic_trial_evaluation import evaluate_anisotropic_trial as _dependency_1
    from scirel.inference.anisotropic_parameter_optimization import optimize_anisotropic_parameters as _dependency_2
    from scirel.inference.latin_hypercube_sampling import sample_latin_hypercube as _dependency_3
    return compose(run_composition, inputs, kwargs, {'asset_loader': {'scirel.diagnostics.observation_residuals': _dependency_0, 'scirel.inference.anisotropic_trial_evaluation': _dependency_1, 'scirel.inference.anisotropic_parameter_optimization': _dependency_2, 'scirel.inference.latin_hypercube_sampling': _dependency_3}})
__all__ = ['solve_direct_anisotropic_inversion']
