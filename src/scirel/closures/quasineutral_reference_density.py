"""Evaluate the reference electron-density relation."""

from __future__ import annotations
import numpy as np


def compute_reference_electron_density(density_ref_m3, ion_charge_state):
    """Return ``n_e,ref = Z_i * n_i,ref`` for positive-ion inputs."""
    density, charge_state = np.broadcast_arrays(
        np.asarray(density_ref_m3, dtype=float), np.asarray(ion_charge_state, dtype=float)
    )
    if not np.all(np.isfinite(density)) or np.any(density < 0.0):
        raise ValueError("density_ref_m3 must be finite and nonnegative")
    if not np.all(np.isfinite(charge_state)) or np.any(charge_state <= 0.0):
        raise ValueError("ion_charge_state must be finite and positive")
    result = charge_state * density
    if not np.all(np.isfinite(result)):
        raise FloatingPointError("electron reference density overflowed")
    return {"electron_density_ref_m3": result}


__all__ = ["compute_reference_electron_density"]
