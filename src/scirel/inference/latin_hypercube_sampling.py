"""Seeded stratified Latin-hypercube design for direct inversion."""
from __future__ import annotations
import numpy as np

def sample_latin_hypercube(*, bounds, n_samples, seed=None, fit_keys=None):
    if not isinstance(bounds, dict) or not isinstance(n_samples, int) or n_samples < 1:
        raise ValueError('bounds mapping and positive n_samples required')
    keys = list(bounds) if fit_keys is None else list(fit_keys)
    rng = np.random.default_rng(seed)
    unit = np.empty((n_samples, len(keys)))
    samples = []
    for index, key in enumerate(keys):
        low, high = map(float, bounds[key])
        if not np.isfinite(low) or not np.isfinite(high) or high <= low:
            raise ValueError(f'finite increasing bounds required for {key}')
        unit[:, index] = (rng.permutation(n_samples) + rng.random(n_samples)) / n_samples
    for row in unit:
        samples.append({key: float(bounds[key][0]) + value * (float(bounds[key][1]) - float(bounds[key][0])) for key, value in zip(keys, row)})
    return {'initial_samples': samples}
run = sample_latin_hypercube
__all__ = ['sample_latin_hypercube']
