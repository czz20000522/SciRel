"""the neutral-transport formulation H/H2 collision-generation stopping criterion."""

from __future__ import annotations

import numpy as np

__all__ = ["evaluate_neutral_generation_stopping"]


def _finite_real(value, name, *, scalar=False):
    try:
        if isinstance(value, (list, tuple)) and any(
            isinstance(item, (bool, np.bool_)) for item in np.asarray(value, dtype=object).flat
        ):
            raise ValueError
        raw = np.asarray(value)
        if raw.dtype.kind not in "iuf" or (scalar and raw.ndim != 0):
            raise ValueError
        result = np.asarray(raw, dtype=float)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be finite real {'scalar' if scalar else 'array'}") from exc
    if not np.all(np.isfinite(result)):
        raise ValueError(f"{name} must be finite real {'scalar' if scalar else 'array'}")
    return float(result) if scalar else result


def _relative_generation_change(generation, accumulated):
    """Return the source-defined max-norm generation ratio."""
    with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
        return float(np.max(generation) / np.max(accumulated))


def evaluate_neutral_generation_stopping(
    generation_density_m3,
    accumulated_density_m3,
    truncate,
    seed_iteration_enabled=False,
    seed_error=None,
):
    r"""Evaluate the source Delta_n stopping criterion for collision-generation convergence: returns the relative generation density ratio and whether the next generation is unnecessary.

    Parameters
    ----------
    generation_density_m3 : real array-like, shape [nx]
        The current generation density profile. [m^-3].
        Constraints: Finite, nonnegative, one-dimensional.
    accumulated_density_m3 : real array-like, shape [nx]
        The accumulated density profile. [m^-3].
        Constraints: Finite, nonnegative, one-dimensional, same shape as generation_density_m3, must contain a positive value.
    truncate : real scalar, shape scalar
        The convergence threshold. [dimensionless].
        Constraints: Finite and strictly positive.
    seed_iteration_enabled : boolean scalar, shape scalar
        Whether the outer seed iteration is enabled. [dimensionless].
        Constraints: Boolean scalar.
        Default: False.
    seed_error : real scalar, shape scalar
        The outer seed error from the previous pass. [dimensionless].
        Constraints: Required (and must be finite nonnegative) when seed_iteration_enabled is true; must be None when false.
        Default: None.

    Returns
    -------
    result : tuple(float, bool, str), shape tuple of 3 scalars
        A tuple (delta, done, reason): delta is the relative generation density ratio, done is whether the next generation is unnecessary, reason is 'truncate', 'seed_relative', or 'continue'. [mixed (dimensionless ratio, boolean, string)].
        Constraints: Finite delta; done is a Python bool; reason is a status string.

    Raises
    ------
    ValueError
        Raises ValueError for empty, non-real, non-finite, negative or mismatched density vectors, nonpositive accumulated maximum, non-real/non-finite/nonpositive truncate, nonboolean seed_iteration_enabled, or a missing, misplaced or invalid seed_error. Raises ValueError if the finite input ratio overflows to non-finite delta. Not applicable; this relation reports convergence, it does not iterate. Never returned; a rejected call produces no result.

    See Also
    --------
    scirel.kinetic.propagate_neutral_generation : Related neutral-transport operation.

    Notes
    -----
        Evaluate the source Delta_n stopping criterion for collision-generation convergence: returns the relative generation density ratio and whether the next generation is unnecessary.
    nonempty finite nonnegative 1-D density arrays of one shape; accumulated density has a positive maximum; finite positive real truncate; boolean seed_iteration_enabled and a finite nonnegative real seed_error exactly when enabled; derived delta finite

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.kinetic import evaluate_neutral_generation_stopping
    >>> delta, done, reason = evaluate_neutral_generation_stopping(
    ...     np.array([10.0, 20.0]), np.array([100.0, 200.0]), truncate=0.05)
    >>> assert delta == 0.1
    >>> assert done is False
    >>> assert reason == 'continue'
    >>> delta2, done2, reason2 = evaluate_neutral_generation_stopping(
    ...     np.array([0.001, 0.001]), np.array([100.0, 200.0]), truncate=0.1)
    >>> assert done2 is True
    >>> assert reason2 == 'truncate'
    """
    generation = _finite_real(generation_density_m3, "generation_density_m3")
    accumulated = _finite_real(accumulated_density_m3, "accumulated_density_m3")
    truncate = _finite_real(truncate, "truncate", scalar=True)
    if (
        generation.shape != accumulated.shape
        or generation.ndim != 1
        or generation.size == 0
        or np.any(generation < 0.0)
        or np.any(accumulated < 0.0)
        or truncate <= 0.0
    ):
        raise ValueError("density vectors must be finite/nonnegative and truncate positive")
    if not isinstance(seed_iteration_enabled, (bool, np.bool_)):
        raise ValueError("seed_iteration_enabled must be a boolean scalar")
    if seed_iteration_enabled:
        if seed_error is None:
            raise ValueError("seed_error is required when seed iteration is enabled")
        seed_error = _finite_real(seed_error, "seed_error", scalar=True)
        if seed_error < 0.0:
            raise ValueError("seed_error must be nonnegative")
    elif seed_error is not None:
        raise ValueError("seed_error must be None when seed iteration is disabled")
    maximum = float(np.max(accumulated))
    if maximum <= 0.0:
        raise ValueError("accumulated_density_m3 must contain a positive value")
    delta = _relative_generation_change(generation, accumulated)
    if not np.isfinite(delta):
        raise ValueError("delta must be finite")
    if delta < truncate:
        return delta, True, "truncate"
    if seed_iteration_enabled:
        if delta < 0.003 * seed_error:
            return delta, True, "seed_relative"
    return delta, False, "continue"
