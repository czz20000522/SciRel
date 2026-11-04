"""Flux-first, Thomson-ordered normalized inversion residuals."""
from __future__ import annotations
from collections.abc import Mapping
import numpy as np

def _normalized_residual(prediction, observation, label):
    predicted_values = np.asarray(prediction, dtype=float)
    observed_values = np.asarray(observation['values'], dtype=float)
    if predicted_values.shape != observed_values.shape:
        raise ValueError(f'{label} prediction and observation values must have exact same shape')
    sigma = np.asarray(observation.get('sigma', 1.0), dtype=float)
    try:
        sigma = np.broadcast_to(sigma, observed_values.shape)
    except ValueError as exc:
        raise ValueError(f'{label} sigma must be scalar or broadcast exactly to the observation shape') from exc
    if not np.all(np.isfinite(predicted_values)) or not np.all(np.isfinite(observed_values)) or (not np.all(np.isfinite(sigma))) or np.any(sigma <= 0.0):
        raise ValueError(f'{label} prediction, observation values and sigma must be finite and sigma must be positive')
    residual = (predicted_values - observed_values) / sigma
    if not np.all(np.isfinite(residual)):
        raise ValueError(f'{label} normalized residual must be finite')
    return residual

def reduce_observation_residuals(*, predicted, observations):
    if not isinstance(predicted, Mapping) or not isinstance(observations, Mapping):
        raise ValueError('predicted and observations must be mappings')
    residuals = []
    if 'flux_loops' in observations:
        if 'flux_loops' not in predicted:
            raise ValueError('predicted must contain flux_loops for the requested observation')
        observed = observations['flux_loops']
        if not isinstance(observed, Mapping) or 'values' not in observed:
            raise ValueError('flux_loops observation must contain values')
        residuals.append(_normalized_residual(predicted['flux_loops'], observed, 'flux_loops'))
    if 'thomson' in observations:
        observed = observations['thomson']
        source = predicted.get('thomson')
        if isinstance(observed, Mapping) and isinstance(source, Mapping):
            for key in ('density', 'electron_temperature', 'p_parallel', 'p_perp'):
                if key in observed and key in source:
                    channel = observed[key]
                    if not isinstance(channel, Mapping) or 'values' not in channel:
                        raise ValueError(f'thomson.{key} observation must contain values')
                    residuals.append(_normalized_residual(source[key], channel, f'thomson.{key}'))
    if not residuals:
        raise ValueError('observations must contain at least one usable signal with a matching prediction')
    vector = np.concatenate([np.ravel(x) for x in residuals])
    chi2 = float(np.dot(vector, vector))
    if not np.isfinite(chi2):
        raise ValueError('chi2 must be finite')
    return {'residual_vector': vector, 'chi2': chi2}
run = reduce_observation_residuals
__all__ = ['reduce_observation_residuals']
