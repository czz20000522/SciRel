"""Unit-explicit equilibrium point sampling for declared observations."""
from __future__ import annotations
from collections.abc import Mapping
import numpy as np
from .observation_residuals import _CHANNELS


def _mapping(value, name):
    if not isinstance(value, Mapping):
        raise ValueError(f'{name} must be a mapping')
    return value


def _field(mapping, key, name):
    if key not in mapping or mapping[key] is None:
        raise ValueError(f'{name} requires non-null field {key}')
    return mapping[key]


def _unit(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{name} requires an explicit nonempty unit')
    return value


def run_composition(inputs, *, asset_loader):
    """Sample raw psi or single-turn linked flux, and explicitly requested profiles.

    ``flux_loops.quantity`` is ``raw_psi`` or ``magnetic_flux``. Only declared
    ``equilibrium.psi_unit='Wb/rad'`` is multiplied by 2*pi for Wb magnetic
    flux; Wb inputs are unchanged. Raw psi retains its declared unit and gauge.
    Loop turns, reference subtraction and instrument response are not inferred.
    ``thomson`` is a legacy namespace for profile sampling, not scattering.
    """
    inputs = _mapping(inputs, 'inputs')
    equilibrium = _mapping(inputs.get('equilibrium'), 'equilibrium')
    observations = _mapping(inputs.get('observations'), 'observations')
    if not observations or set(observations)-{'flux_loops', 'thomson'}:
        raise ValueError('observations must request known nonempty flux_loops or thomson channels')
    R, Z = _field(inputs, 'R', 'inputs'), _field(inputs, 'Z', 'inputs')
    sampler = asset_loader('scirel.geometry.bilinear_grid_sampling')
    def sample(values, points):
        points = np.asarray(points, dtype=float)
        if points.ndim != 2 or points.shape[1] != 2 or not points.shape[0]:
            raise ValueError('diagnostic points must have nonempty shape (N, 2)')
        return sampler(R, Z, values, points)['samples']
    predicted, units = {}, {}
    if 'flux_loops' in observations:
        request = _mapping(observations['flux_loops'], 'observations.flux_loops')
        if set(request)-{'points','quantity','unit','values','sigma'}:
            raise ValueError('unsupported flux-loop request fields; turns/reference subtraction are not implicit')
        points = _field(request, 'points', 'observations.flux_loops')
        source_unit = _unit(equilibrium.get('psi_unit'), 'equilibrium.psi_unit')
        target_unit = _unit(request.get('unit'), 'observations.flux_loops.unit')
        quantity = request.get('quantity')
        if quantity == 'raw_psi':
            if target_unit != source_unit:
                raise ValueError('raw_psi unit must equal equilibrium.psi_unit')
            factor = 1.
        elif quantity == 'magnetic_flux':
            if target_unit != 'Wb' or source_unit not in ('Wb/rad', 'Wb'):
                raise ValueError('magnetic_flux requires Wb output and Wb/rad or Wb source psi')
            factor = 2*np.pi if source_unit == 'Wb/rad' else 1.
        else:
            raise ValueError('flux_loops quantity must explicitly be raw_psi or magnetic_flux')
        values = sample(_field(equilibrium, 'psi', 'equilibrium'), points)*factor
        if not np.all(np.isfinite(values)):
            raise FloatingPointError('magnetic flux conversion is not finite')
        predicted['flux_loops'], units['flux_loops'] = values, target_unit
    if 'thomson' in observations:
        request = _mapping(observations['thomson'], 'observations.thomson')
        if set(request)-set(_CHANNELS)-{'points'} or not any(k in request for k in _CHANNELS):
            raise ValueError('thomson must explicitly request known profile channels')
        points = _field(request, 'points', 'observations.thomson')
        profiles = _mapping(equilibrium.get('profiles'), 'equilibrium.profiles')
        profile_units = _mapping(equilibrium.get('profile_units'), 'equilibrium.profile_units')
        predicted['thomson'], units['thomson'] = {}, {}
        for key in _CHANNELS:
            if key not in request:
                continue
            channel = _mapping(request[key], f'thomson.{key}')
            unit = _unit(channel.get('unit'), f'thomson.{key}.unit')
            if unit != profile_units.get(key):
                raise ValueError(f'thomson.{key} unit must match equilibrium.profile_units')
            if key in ('p_parallel', 'p_perp') and unit != 'Pa':
                raise ValueError(f'thomson.{key} pressure unit must be Pa')
            if key == 'density' and unit != 'm^-3':
                raise ValueError('thomson.density unit must be m^-3')
            if key == 'electron_temperature' and unit not in ('K', 'eV', 'J'):
                raise ValueError('electron_temperature unit must be explicitly K, eV or J')
            predicted['thomson'][key] = sample(_field(profiles, key, 'equilibrium.profiles'), points)
            units['thomson'][key] = unit
    predicted['units'] = units
    return predicted


def synthesize_equilibrium_diagnostics(inputs=None, **kwargs):
    """Sample declared equilibrium diagnostics at caller-supplied points.

    Parameters
    ----------
    inputs : mapping, optional
        Mapping containing ``R``, ``Z``, ``equilibrium`` and nonempty
        ``observations``. Flux-loop requests declare ``quantity`` and ``unit``;
        profile requests use explicit ``thomson`` channel units.
    **kwargs
        Named inputs merged with ``inputs`` by the composition boundary.

    Returns
    -------
    dict
        Requested ``flux_loops`` and/or ``thomson`` samples plus matching
        ``units`` metadata. Only explicitly requested channels are returned.

    Raises
    ------
    ValueError
        If grids, observation requests, points, fields or units are missing,
        incompatible or outside the declared domain.
    FloatingPointError
        If a magnetic-flux conversion produces a nonfinite value.
    """
    from scirel._composition import compose
    from scirel.geometry.bilinear_grid_sampling import sample_rectilinear_field
    return compose(run_composition, inputs, kwargs, {'asset_loader': {'scirel.geometry.bilinear_grid_sampling': sample_rectilinear_field}})

__all__ = ['synthesize_equilibrium_diagnostics']
