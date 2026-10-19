"""Evaluate a clipped radial envelope for the Frank--Egedal pressure state."""
import numpy as np


def evaluate_frank_egedal_radial_envelope(psi, params):
    """Return the clipped source-order radial pressure envelope."""
    psi = np.asarray(psi, dtype=float)
    if psi.ndim != 2 or psi.size == 0 or not np.all(np.isfinite(psi)):
        raise ValueError("psi must be a finite two-dimensional [Z,R] grid")
    if not isinstance(params, dict):
        raise ValueError("params must be a mapping")
    psi_axis = float(params.get("psi_axis", np.nanmin(psi)))
    psi_edge = float(params.get("psi_edge", np.nanmax(psi)))
    alpha = float(params.get("alpha", 1.0))
    denominator = psi_edge - psi_axis
    if not np.all(np.isfinite([alpha, psi_axis, psi_edge, denominator])) or alpha < 0.0 or abs(denominator) < 1.0e-30:
        raise ValueError("psi_edge and psi_axis must define a finite radial profile")
    normalized = np.clip((psi - psi_axis) / denominator, 0.0, 1.0)
    return np.power(np.clip(1.0 - normalized, 0.0, None), alpha)

__all__ = ['evaluate_frank_egedal_radial_envelope']
