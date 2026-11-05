"""Scaled relative residual between two flux states."""

import numpy as np


def compute_picard_flux_residual(psi_previous, psi_next):
    """Compute the scaled relative L2 change between two flux states.

    Parameters
    ----------
    psi_previous : array_like, shape (N_Z, N_R)
        Two-dimensional flux state before the Picard update in ``[Wb]``.  All
        values must be finite, and the shape must exactly match ``psi_next``.
        An all-zero state is allowed.
    psi_next : array_like, shape (N_Z, N_R)
        Two-dimensional flux state after the Picard update in ``[Wb]``.  All
        values must be finite, and the shape must exactly match
        ``psi_previous``.  An all-zero state is allowed.

    Returns
    -------
    residual : float
        Nonnegative finite relative Euclidean change in ``[dimensionless]``.
        The defining value is
        ``||psi_next - psi_previous||_2 /
        max(||psi_previous||_2, 1e-30 Wb)``, evaluated with a common
        magnitude scale.  Two zero states return ``0.0``.

    Raises
    ------
    ValueError
        If the inputs are not same-shape two-dimensional arrays, contain
        nonfinite values, produce a zero scaled denominator, or produce a
        nonfinite relative residual.
    TypeError
        If either input cannot be converted to a floating-point array.

    See Also
    --------
    scirel.diagnostics.reduce_observation_residuals
        Reduce observations against already-computed predictions.
    scirel.diagnostics.compute_parallel_pressure_residual
        Check a local fixed-flux pressure relation.

    Notes
    -----
    Both arrays are indexed as ``[Z, R]`` and every entry has equal weight; no
    grid spacing, active-cell mask, or physical force-balance interpretation is
    applied.  The ``1e-30 Wb`` denominator floor changes the ratio when the
    previous-state norm is smaller than the floor.  The scaled arithmetic
    handles selected very large and very small magnitudes, but a mathematical
    ratio that is not representable as finite float64 is rejected.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.diagnostics import compute_picard_flux_residual
    >>> previous = np.array([[3.0, 4.0]])
    >>> assert compute_picard_flux_residual(previous, previous)['residual'] == 0.0
    >>> assert np.isclose(compute_picard_flux_residual(previous, 2*previous)['residual'], 1.0)
    """
    previous = np.asarray(psi_previous, dtype=float)
    next_state = np.asarray(psi_next, dtype=float)
    if previous.shape != next_state.shape or previous.ndim != 2:
        raise ValueError(
            "psi_previous and psi_next must be same-shape two-dimensional [Z,R] arrays"
        )
    if not np.all(np.isfinite(previous)) or not np.all(np.isfinite(next_state)):
        raise ValueError("psi_previous and psi_next must contain only finite values")
    scale = max(
        float(np.max(np.abs(previous), initial=0.0)), float(np.max(np.abs(next_state), initial=0.0))
    )
    if scale == 0.0:
        return {"residual": 0.0}
    previous_scaled = previous / scale
    # Subtract first where representable to preserve small changes of large states.
    with np.errstate(over="ignore"):
        change = next_state - previous
    overflow = ~np.isfinite(change)
    change_scaled = change / scale
    if np.any(overflow):
        change_scaled[overflow] = next_state[overflow] / scale - previous_scaled[overflow]
    denominator = max(float(np.hypot.reduce(previous_scaled.ravel(), initial=0.0)), 1.0e-30 / scale)
    if denominator == 0.0:
        raise ValueError("relative residual exceeds the finite floating-point range")
    residual = float(np.hypot.reduce(change_scaled.ravel(), initial=0.0)) / denominator
    if not np.isfinite(residual):
        raise ValueError("relative residual exceeds the finite floating-point range")
    return {"residual": residual}


__all__ = ["compute_picard_flux_residual"]
