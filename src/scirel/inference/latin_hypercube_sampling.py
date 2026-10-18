"""Seeded stratified Latin-hypercube design for direct inversion."""
from __future__ import annotations
import numpy as np

def sample_latin_hypercube(*, bounds, n_samples, seed=None, fit_keys=None):
    """Generate a seeded stratified Latin-hypercube parameter design.

    Parameters
    ----------
    bounds : dict
        Mapping from parameter keys to finite increasing ``(low, high)``
        endpoint pairs. Only selected keys are validated and sampled.
    n_samples : int
        Positive number of strata and returned sample dictionaries.
    seed : object, optional
        Seed passed unchanged to ``numpy.random.default_rng``.
    fit_keys : iterable, optional
        Ordered subset of keys to sample; omitted keys follow ``bounds``
        insertion order.

    Returns
    -------
    dict
        Mapping with ``initial_samples``, an ordered list of dictionaries
        containing one draw in each stratum for every selected key.

    Raises
    ------
    ValueError
        If ``bounds`` or ``n_samples`` has an invalid type or selected bounds
        are nonfinite or nonincreasing.
    KeyError
        If ``fit_keys`` names a key absent from ``bounds``.
    """
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
