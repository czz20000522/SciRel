"""Seeded stratified Latin-hypercube designs for bounded inversion."""

from __future__ import annotations

import numpy as np


def sample_latin_hypercube(*, bounds, n_samples, seed=None, fit_keys=None):
    """Generate a seeded Latin-hypercube design over bounded parameters.

    Parameters
    ----------
    bounds : dict
        Mapping from parameter keys to finite increasing ``(low, high)``
        intervals [per-parameter caller units]. Only selected keys are read;
        unselected intervals are not validated.
    n_samples : int
        Number of strata and returned parameter dictionaries [count]. It must
        be a positive Python integer; Boolean values are rejected.
    seed : NumPy-compatible seed or None, optional
        Seed passed unchanged to ``numpy.random.default_rng`` [dimensionless].
        ``None`` selects a non-deterministic generator. The default is None.
    fit_keys : iterable of keys or None, optional
        Ordered parameter-key subset [identifier]. If None, use the insertion
        order of ``bounds``. Duplicate keys are not rejected; an output mapping
        keeps only the last column for a duplicate key. The default is None.

    Returns
    -------
    initial_samples : list of dict
        ``n_samples`` dictionaries in draw order. Each contains only the
        selected keys and one independently jittered value in every stratum
        [per-parameter caller units].

    Raises
    ------
    ValueError
        If ``bounds`` is not a dict, ``n_samples`` is not a positive Python
        integer, or a selected interval is non-finite or not strictly
        increasing. A malformed interval also raises ``ValueError``.
    KeyError
        If a selected key is absent from ``bounds``.
    TypeError
        If ``fit_keys`` is not iterable, ``bounds`` uses an unsupported key
        type, or a conversion raises ``TypeError``. A nonnumeric selected bound
        may instead propagate ``ValueError`` from its conversion.

    See Also
    --------
    optimize_anisotropic_parameters : Fit bounded parameters using an initial
        design and a caller-owned trial evaluator.
    evaluate_anisotropic_trial : Validate one physical trial with a fixed
        residual dimension.

    Notes
    -----
    Each coordinate independently permutes the strata ``0, ..., n_samples -
    1`` and adds one uniform offset inside every stratum. Affine mapping of
    the unit value into ``[low, high)`` gives one sample dictionary per row.
    This is an initial design only: it does not encode correlations, priors,
    posterior uncertainty, physical admissibility, or optimizer convergence.
    The selected key order, installed NumPy generator, and seed define the
    realized design.

    Examples
    --------
    >>> from scirel.inference import sample_latin_hypercube
    >>> bounds = {'a': (0.0, 1.0), 'b': (10.0, 20.0)}
    >>> a = sample_latin_hypercube(bounds=bounds, n_samples=5, seed=4)['initial_samples']
    >>> b = sample_latin_hypercube(bounds=bounds, n_samples=5, seed=4)['initial_samples']
    >>> assert a == b
    >>> assert sorted(int(row['a'] * 5) for row in a) == list(range(5))
    >>> assert sorted(int((row['b'] - 10) / 10 * 5) for row in a) == list(range(5))
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
