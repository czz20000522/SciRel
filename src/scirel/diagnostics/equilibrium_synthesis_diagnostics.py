"""Standalone synthetic point diagnostics for a declared equilibrium state."""
from __future__ import annotations
import hashlib
from pathlib import Path

def _required_mapping(value, name):
    if not isinstance(value, dict):
        raise ValueError(f'{name} must be a mapping')
    return value

def _required_field(mapping, key, owner):
    if key not in mapping or mapping[key] is None:
        raise ValueError(f'{owner} requires non-null field {key}')
    return mapping[key]

def _sample_field(asset_loader, R, Z, field, points):
    return asset_loader('scirel.geometry.bilinear_grid_sampling')(R, Z, field, points)['samples']

def run_graph(inputs, *, asset_loader):
    """Return declared optional flux-loop and Thomson-like predictions.

    The returned mapping deliberately has the same optional-key policy as
    ``predict_observations``: an empty or unknown-only observation mapping
    returns ``{}``; recognized requests appear in source order, flux loops then
    Thomson samples.  Neither this graph nor its nested sampler mutates the
    equilibrium mapping.
    """
    inputs = _required_mapping(inputs, 'inputs')
    equilibrium = _required_mapping(inputs.get('equilibrium'), 'equilibrium')
    observations = _required_mapping(inputs.get('observations'), 'observations')
    if 'R' not in inputs or 'Z' not in inputs:
        raise ValueError('R and Z are required explicit diagnostic-grid inputs')
    R = inputs['R']
    Z = inputs['Z']
    predicted = {}
    if 'flux_loops' in observations:
        flux_request = _required_mapping(observations['flux_loops'], 'observations.flux_loops')
        points = _required_field(flux_request, 'points', 'observations.flux_loops')
        psi = _required_field(equilibrium, 'psi', 'equilibrium')
        predicted['flux_loops'] = _sample_field(asset_loader, R, Z, psi, points)
    if 'thomson' in observations:
        thomson_request = _required_mapping(observations['thomson'], 'observations.thomson')
        points = _required_field(thomson_request, 'points', 'observations.thomson')
        profiles = _required_mapping(equilibrium.get('profiles'), 'equilibrium.profiles')
        thomson = {'p_parallel': _sample_field(asset_loader, R, Z, _required_field(profiles, 'p_parallel', 'equilibrium.profiles'), points), 'p_perp': _sample_field(asset_loader, R, Z, _required_field(profiles, 'p_perp', 'equilibrium.profiles'), points)}
        if profiles.get('density') is not None:
            thomson['density'] = _sample_field(asset_loader, R, Z, profiles['density'], points)
        if profiles.get('electron_temperature') is not None:
            thomson['electron_temperature'] = _sample_field(asset_loader, R, Z, profiles['electron_temperature'], points)
        predicted['thomson'] = thomson
    return predicted

def synthesize_equilibrium_diagnostics(inputs=None, **kwargs):
    from scirel._composition import compose
    from scirel.geometry.bilinear_grid_sampling import sample_rectilinear_field as _dependency_0
    return compose(run_graph, inputs, kwargs, {'asset_loader': {'scirel.geometry.bilinear_grid_sampling': _dependency_0}})
__all__ = ['synthesize_equilibrium_diagnostics']
