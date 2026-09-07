"""Relative flux-state residual used by SciRel Picard feedback."""
import numpy as np

def compute_picard_flux_residual(psi_previous, psi_next):
    """Return the source-equivalent L2 relative change with a safe zero denominator floor."""
    previous = np.asarray(psi_previous, dtype=float)
    next_state = np.asarray(psi_next, dtype=float)
    if previous.shape != next_state.shape or previous.ndim != 2:
        raise ValueError('psi_previous and psi_next must be same-shape two-dimensional [Z,R] arrays')
    if not np.all(np.isfinite(previous)) or not np.all(np.isfinite(next_state)):
        raise ValueError('psi_previous and psi_next must contain only finite values')
    denominator = max(float(np.linalg.norm(previous.ravel())), 1e-30)
    return {'residual': float(np.linalg.norm((next_state - previous).ravel()) / denominator)}
__all__ = ['compute_picard_flux_residual']
