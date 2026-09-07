"""Explicit source-compatible linear profile evaluation on flux surfaces."""
from __future__ import annotations
import numpy as np

def evaluate_flux_surface_profile(*, psi_samples, values, target, left=None, right=None) -> dict[str, np.ndarray]:
    """Evaluate a sorted unique ``psi`` profile with explicit endpoint policy."""
    coordinates = np.asarray(psi_samples, dtype=float).ravel()
    samples = np.asarray(values, dtype=float).ravel()
    query = np.asarray(target, dtype=float)
    if coordinates.size != samples.size or coordinates.size < 2:
        raise ValueError('psi_samples and values require at least two paired samples')
    if not np.all(np.isfinite(coordinates)) or not np.all(np.isfinite(samples)) or (not np.all(np.isfinite(query))):
        raise ValueError('profile coordinates, values, and target must be finite')
    order = np.argsort(coordinates)
    coordinates, samples = (coordinates[order], samples[order])
    coordinates, indices = np.unique(coordinates, return_index=True)
    samples = samples[indices]
    if coordinates.size < 2:
        raise ValueError('psi samples do not span a usable interval')
    left_value = float(samples[0] if left is None else left)
    right_value = float(samples[-1] if right is None else right)
    if not np.isfinite(left_value) or not np.isfinite(right_value):
        raise ValueError('profile endpoint values must be finite')
    result = np.interp(query.ravel(), coordinates, samples, left=left_value, right=right_value).reshape(query.shape)
    return {'values': result, 'psi': coordinates, 'profile_values': samples}
scientific_operator = evaluate_flux_surface_profile
__all__ = ['evaluate_flux_surface_profile']
