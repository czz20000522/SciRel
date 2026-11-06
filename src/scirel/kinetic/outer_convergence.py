"""Top-level outer-loop convergence relation.

This operator is intentionally separate from the 10*truncate seed relation
used inside the neutral transport closures.  The top-level outer loop compares
the molecular density before and after an outer pass and re-enters while the
relative change is greater than ``truncate``.
"""

from __future__ import annotations

import numpy as np

__all__ = ["evaluate_outer_convergence"]


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
    """Compute the top-level outer-pass max-norm relative change."""
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        return float(np.max(np.abs(current - previous)) / np.max(current))


def evaluate_outer_convergence(
    previous_density_m3,
    current_density_m3,
    truncate,
):
    r"""Evaluate the top-level outer-pass convergence: compares molecular density before/after an outer pass, re-enters while relative change exceeds truncate.

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
        A mapping with seed_error (relative change), reentry_threshold (truncate), should_reiterate (bool), and reason ('reiterate' or 'converged'). [mixed (dimensionless ratio, boolean, string)].
        Constraints: Finite seed_error; reentry_threshold = truncate; should_reiterate is a Python bool.

    Raises
    ------
    ValueError
        Raises ValueError for empty, non-real, non-finite, negative or misaligned density vectors, nonpositive current maximum, or non-real/non-finite/nonpositive truncate. Raises ValueError if finite inputs overflow seed_error. Not applicable; this relation reports convergence, it does not iterate. Never returned; a rejected call produces no result.

    See Also
    --------
    scirel.kinetic.evaluate_neutral_outer_seed_convergence : Related neutral-transport operation.

    Notes
    -----
        Evaluate the top-level outer-pass convergence: compares molecular density before/after an outer pass, re-enters while relative change exceeds truncate.
    nonempty aligned finite nonnegative real 1-D density arrays, positive current maximum, finite positive real truncate, and representable finite seed_error

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.kinetic import evaluate_outer_convergence
    >>> prev = np.array([100.0])
    >>> curr = np.array([100.05])
    >>> result = evaluate_outer_convergence(prev, curr, truncate=0.1)
    >>> assert result['should_reiterate'] is False
    >>> assert result['reentry_threshold'] == 0.1
    >>> curr2 = np.array([120.0])
    >>> result2 = evaluate_outer_convergence(prev, curr2, truncate=0.1)
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
            "top-level outer density profiles must be finite, nonnegative, "
            "aligned, and current density must be positive"
        )

    seed_error = _profile_error(previous, current)
    if not np.isfinite(seed_error):
        raise ValueError("seed_error must be finite")
    threshold = float(truncate)
    should_reiterate = seed_error > threshold
    return {
        "seed_error": seed_error,
        "reentry_threshold": threshold,
        "should_reiterate": should_reiterate,
        "reason": "reiterate" if should_reiterate else "converged",
    }
