"""Seeded stratified Latin-hypercube designs for bounded inversion."""

from __future__ import annotations

import numpy as np


def sample_latin_hypercube(*, bounds, n_samples, seed=None, fit_keys=None):
    """Generate one uniformly jittered point in every selected stratum.

    ``bounds`` maps parameter names to finite increasing ``(low, high)``
    pairs.  ``fit_keys`` fixes the sampled column order; omitted keys follow
    mapping insertion order.  The returned ``initial_samples`` list is ready
    for the optimizer graph and contains no hidden parameters.

    Raises ``ValueError`` for malformed bounds or a non-positive sample count.
    A boolean ``n_samples`` is rejected explicitly instead of leaking a
    ``TypeError`` from NumPy array allocation.
    """
    if (
        not isinstance(bounds, dict)
        or isinstance(n_samples, (bool, np.bool_))
        or not isinstance(n_samples, int)
        or n_samples < 1
    ):
        raise ValueError("bounds mapping and positive integer n_samples required")
    keys = list(bounds) if fit_keys is None else list(fit_keys)
    rng = np.random.default_rng(seed)
    lower = np.empty(len(keys), dtype=float)
    upper = np.empty(len(keys), dtype=float)
    for column, key in enumerate(keys):
        low, high = map(float, bounds[key])
        if not np.isfinite(low) or not np.isfinite(high) or high <= low:
            raise ValueError(f"finite increasing bounds required for {key}")
        lower[column] = low
        upper[column] = high

    unit = np.empty((n_samples, len(keys)), dtype=float)
    strata = np.arange(n_samples, dtype=float)
    for column in range(len(keys)):
        unit[:, column] = (rng.permutation(strata) + rng.random(n_samples)) / n_samples
    samples = [
        {
            key: float(low + fraction * (high - low))
            for key, low, high, fraction in zip(keys, lower, upper, row)
        }
        for row in unit
    ]
    return {"initial_samples": samples}


run = sample_latin_hypercube
__all__ = ["sample_latin_hypercube"]
