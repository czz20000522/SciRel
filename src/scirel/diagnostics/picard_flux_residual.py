"""Scaled relative residual between two flux states."""

import numpy as np


def compute_picard_flux_residual(psi_previous, psi_next):
    """Evaluate the L2 relative-change formula with scaled finite arithmetic."""
    previous = np.asarray(psi_previous, dtype=float)
    next_state = np.asarray(psi_next, dtype=float)
    if previous.shape != next_state.shape or previous.ndim != 2:
        raise ValueError("psi_previous and psi_next must be same-shape two-dimensional [Z,R] arrays")
    if not np.all(np.isfinite(previous)) or not np.all(np.isfinite(next_state)):
        raise ValueError("psi_previous and psi_next must contain only finite values")
    scale = max(float(np.max(np.abs(previous), initial=0.0)),
                float(np.max(np.abs(next_state), initial=0.0)))
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


__all__ = ['compute_picard_flux_residual']
