"""Fixed-layout, flux-first normalized residuals; no requested channel is dropped."""
from __future__ import annotations
from collections.abc import Mapping
import numpy as np

_CHANNELS = ('density', 'electron_temperature', 'p_parallel', 'p_perp')


def _observation_layout(observations):
    """Validate observations independently of predictions and freeze their order."""
    if not isinstance(observations, Mapping) or not observations:
        raise ValueError('observations must contain at least one usable signal')
    unknown = set(observations) - {'flux_loops', 'thomson'}
    if unknown:
        raise ValueError(f'unknown observation kinds: {sorted(unknown)}')
    layout = []
    if 'flux_loops' in observations:
        layout.append(('flux_loops', None, observations['flux_loops']))
    if 'thomson' in observations:
        observed = observations['thomson']
        if not isinstance(observed, Mapping):
            raise ValueError('thomson observation must be a mapping')
        unknown = set(observed) - set(_CHANNELS) - {'points'}
        if unknown:
            raise ValueError(f'unknown thomson channels: {sorted(unknown)}')
        if not any(key in observed for key in _CHANNELS):
            raise ValueError('thomson must request at least one usable signal')
        layout.extend(('thomson', key, observed[key]) for key in _CHANNELS if key in observed)
    validated = []
    for kind, key, observation in layout:
        label = kind if key is None else f'{kind}.{key}'
        if not isinstance(observation, Mapping) or 'values' not in observation:
            raise ValueError(f'{label} observation must contain values')
        values = np.asarray(observation['values'], dtype=float)
        if not values.size or not np.all(np.isfinite(values)):
            raise ValueError(f'{label} values must be nonempty and finite')
        try:
            sigma = np.broadcast_to(np.asarray(observation.get('sigma', 1.), dtype=float), values.shape)
        except ValueError as exc:
            raise ValueError(f'{label} sigma must be scalar or broadcast exactly to the observation shape') from exc
        if not np.all(np.isfinite(sigma)) or np.any(sigma <= 0.):
            raise ValueError(f'{label} values and sigma must be finite and sigma must be positive')
        unit = observation.get('unit')
        if unit is not None and (not isinstance(unit, str) or not unit.strip()):
            raise ValueError(f'{label} unit must be a nonempty string')
        validated.append((kind, key, values, sigma, unit))
    return validated


def reduce_observation_residuals(*, predicted, observations):
    """Return ordered (prediction-observation)/sigma and its squared norm.

    Every requested flux/profile channel must be present with exact shape.
    Explicit observed units require matching prediction ``units`` metadata;
    unitless records remain normalized algebra, without an inferred physical unit.
    """
    if not isinstance(predicted, Mapping):
        raise ValueError('predicted and observations must be mappings')
    residuals = []
    for kind, key, observed, sigma, unit in _observation_layout(observations):
        label = kind if key is None else f'{kind}.{key}'
        source = predicted.get(kind)
        if key is not None:
            source = source.get(key) if isinstance(source, Mapping) else None
        if source is None:
            raise ValueError(f'predicted must contain {label} for every requested usable signal')
        values = np.asarray(source, dtype=float)
        if values.shape != observed.shape:
            raise ValueError(f'{label} prediction and observation values must have exact same shape')
        if not np.all(np.isfinite(values)):
            raise ValueError(f'{label} prediction must be finite')
        if unit is not None:
            units = predicted.get('units', {})
            actual_unit = units.get(kind) if isinstance(units, Mapping) else None
            if key is not None:
                actual_unit = actual_unit.get(key) if isinstance(actual_unit, Mapping) else None
            if actual_unit != unit:
                raise ValueError(f'{label} prediction unit must match observation unit {unit!r}')
        with np.errstate(over='ignore', invalid='ignore', divide='ignore'):
            normalized = (values-observed)/sigma
        if not np.all(np.isfinite(normalized)):
            raise ValueError(f'{label} normalized residual must be finite')
        residuals.append(normalized.ravel())
    vector = np.concatenate(residuals)
    with np.errstate(over='ignore'):
        chi2 = float(vector @ vector)
    if not np.isfinite(chi2):
        raise ValueError('chi2 must be finite')
    return {'residual_vector': vector, 'chi2': chi2}

run = reduce_observation_residuals
__all__ = ['reduce_observation_residuals']
