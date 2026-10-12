"""Resolver for the YAML-declared Frank--Egedal closure assets."""
from __future__ import annotations
import hashlib
from pathlib import Path

def run_graph(inputs, *, asset_loader):
    """Resolve the N4 pipeline without graph-local numerical implementation."""
    if not isinstance(inputs, dict):
        raise ValueError('inputs must be a mapping')
    if 'params' not in inputs:
        raise ValueError('params is required by task_graph.yaml')
    if not isinstance(inputs['params'], dict):
        raise ValueError('params must be a mapping')
    params = dict(inputs['params'])
    radial = asset_loader('scirel.kinetic.frank_egedal_radial_envelope')(inputs.get('psi'), params)
    source = asset_loader('scirel.kinetic.frank_egedal_source_projection')(params, spectrum_operator=asset_loader('scirel.kinetic.loss_cone_spectrum'))
    hot = asset_loader('scirel.kinetic.frank_egedal_hot_ion_moments')(inputs.get('B'), params, source['degrees'], source['source_coefficients'], source['legendre_terms'], source['fractional_mode'])
    result = asset_loader('scirel.kinetic.frank_egedal_pressure_state')(inputs.get('psi'), radial, hot['hot_parallel_shape'], hot['hot_perpendicular_shape'], hot['hot_density_shape'], params)
    result['closure_state'] = {'normalized_field': hot['normalized_field'], 'radial_shape': radial, 'xi_tp_mid': source['xi_tp_mid'], 'degrees': source['degrees'], 'source_coefficients': source['source_coefficients'], 'degree_source': source['degree_source'], 'legendre_backend': source.get('legendre_backend', 'truncated'), 'legendre_terms': source['legendre_terms'], 'normalization': 'pressure moments referenced to hot_parallel(b=1); density referenced to hot_density(b=1)', 'quadrature': hot['quadrature'], 'velocity_domain': hot['velocity_domain'], 'quadrature_convergence': hot['quadrature_convergence'], 'reference_raw_moments': hot['reference_raw_moments']}
    return result

def solve_frank_egedal_pressure_closure(inputs=None, **kwargs):
    from scirel._composition import compose
    from scirel.kinetic.frank_egedal_hot_ion_moments import evaluate_frank_egedal_hot_ion_moments as _dependency_0
    from scirel.kinetic.frank_egedal_pressure_state import assemble_frank_egedal_pressure as _dependency_1
    from scirel.kinetic.frank_egedal_radial_envelope import evaluate_frank_egedal_radial_envelope as _dependency_2
    from scirel.kinetic.frank_egedal_source_projection import project_frank_egedal_source_modes as _dependency_3
    from scirel.kinetic.loss_cone_spectrum import solve_loss_cone_spectrum as _dependency_4
    return compose(run_graph, inputs, kwargs, {'asset_loader': {'scirel.kinetic.frank_egedal_hot_ion_moments': _dependency_0, 'scirel.kinetic.frank_egedal_pressure_state': _dependency_1, 'scirel.kinetic.frank_egedal_radial_envelope': _dependency_2, 'scirel.kinetic.frank_egedal_source_projection': _dependency_3, 'scirel.kinetic.loss_cone_spectrum': _dependency_4}})
__all__ = ['solve_frank_egedal_pressure_closure']
