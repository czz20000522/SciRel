"""Explicit outer-seed convergence relation for H/H2 generation lifecycles."""

from __future__ import annotations

import numpy as np

__all__ = ["evaluate_neutral_outer_seed_convergence"]


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


def _profile_error(previous, current):
    """Compute the max-norm relative change used by the seed controller."""
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        return float(np.max(np.abs(previous - current)) / np.max(current))


def evaluate_neutral_outer_seed_convergence(
    previous_density_m3,
    current_density_m3,
    truncate,
):
    r"""Evaluate the source outer seed re-entry condition: computes seed_error and reentry_threshold (10*truncate), returns whether the outer seed pass should re-iterate.

    Parameters
    ----------
    previous_density_m3 : real array-like, shape [nx]
        The density profile before the pass. [m^-3].
        Constraints: Finite, nonnegative, one-dimensional.
    current_density_m3 : real array-like, shape [nx]
        The density profile after the pass. [m^-3].
        Constraints: Finite, nonnegative, one-dimensional, same shape as previous.
    truncate : real scalar, shape scalar
        The convergence threshold. [dimensionless].
        Constraints: Finite and strictly positive.

    Returns
    -------
    result : mapping of scalars and a boolean, shape mapping
        A mapping with seed_error (relative change), reentry_threshold (10*truncate), should_reiterate (bool), and reason ('reiterate' or 'converged'). [mixed (dimensionless ratio, boolean, string)].
        Constraints: Finite seed_error; reentry_threshold = 10*truncate; should_reiterate is a Python bool.

    Raises
    ------
    ValueError
        Raises ValueError for empty, non-real, non-finite, negative or misaligned density vectors, nonpositive current maximum, or non-real/non-finite/nonpositive truncate. Raises ValueError if finite inputs overflow seed_error or the 10*truncate threshold. Not applicable; this relation reports convergence, it does not iterate. Never returned; a rejected call produces no result.

    See Also
    --------
    scirel.kinetic.evaluate_outer_convergence : Related neutral-transport operation.

    Notes
    -----
        Evaluate the source outer seed re-entry condition: computes seed_error and reentry_threshold (10*truncate), returns whether the outer seed pass should re-iterate.
    nonempty aligned finite nonnegative real 1-D density arrays, positive current maximum, finite positive real truncate, and representable finite seed_error and 10*truncate threshold

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.kinetic import evaluate_neutral_outer_seed_convergence
    >>> prev = np.array([100.0, 200.0])
    >>> curr = np.array([100.5, 200.5])
    >>> result = evaluate_neutral_outer_seed_convergence(prev, curr, truncate=0.1)
    >>> assert result['should_reiterate'] is False
    >>> assert result['reentry_threshold'] == 1.0
    >>> prev2 = np.array([1000.0, 200.0])
    >>> curr2 = np.array([100.0, 200.0])
    >>> result2 = evaluate_neutral_outer_seed_convergence(prev2, curr2, truncate=0.1)
    >>> assert result2['should_reiterate'] is True
    """
    previous = _finite_real(previous_density_m3, "previous_density_m3")
    current = _finite_real(current_density_m3, "current_density_m3")
    truncate = _finite_real(truncate, "truncate", scalar=True)
    if (
        previous.ndim != 1
        or current.shape != previous.shape
        or previous.size == 0
        or np.any(previous < 0.0)
        or np.any(current < 0.0)
        or truncate <= 0.0
        or np.max(current) <= 0.0
    ):
        raise ValueError(
            "outer seed density profiles must be finite, nonnegative, aligned, "
            "and current density must be positive"
        )

    seed_error = _profile_error(previous, current)
    threshold = float(10.0 * truncate)
    if not np.isfinite(seed_error):
        raise ValueError("seed_error must be finite")
    if not np.isfinite(threshold):
        raise ValueError("reentry_threshold must be finite")
    should_reiterate = seed_error > threshold
    return {
        "seed_error": seed_error,
        "reentry_threshold": threshold,
        "should_reiterate": should_reiterate,
        "reason": "reiterate" if should_reiterate else "converged",
    }
