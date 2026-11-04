"""Boltzmann electron response and charge-neutrality residual."""
from __future__ import annotations
import numpy as np
ELEMENTARY_CHARGE_C = 1.602176634e-19

def compute_boltzmann_electron_state(potential_v, electron_temperature_j, electron_density_ref_m3, electron_phi_ref_v, ion_density_m3, ion_charge_state):
    """Evaluate Boltzmann electrons and the logarithmic quasineutral residual.

    The ion density is supplied by a kinetic-moment producer.  ``ion_charge_state``
    is the positive integer-equivalent charge ``Z_i``; the returned residual is
    ``log(Z_i*n_i) - log(n_e)`` and is the quantity used by the ambipolar root solve.
    """
    potential, temperature, n_ref, phi_ref, ion_density = np.broadcast_arrays(np.asarray(potential_v, dtype=float), np.asarray(electron_temperature_j, dtype=float), np.asarray(electron_density_ref_m3, dtype=float), np.asarray(electron_phi_ref_v, dtype=float), np.asarray(ion_density_m3, dtype=float))
    z_i = float(ion_charge_state)
    if not np.isfinite(z_i) or z_i <= 0.0:
        raise ValueError('ion_charge_state must be finite and positive')
    if not all((np.all(np.isfinite(value)) for value in (potential, temperature, n_ref, phi_ref, ion_density))):
        raise ValueError('all fields must be finite')
    if np.any(temperature <= 0.0):
        raise ValueError('electron_temperature_j must be positive')
    if np.any(n_ref < 0.0) or np.any(ion_density < 0.0):
        raise ValueError('reference and ion densities cannot be negative')
    exponent = np.clip(ELEMENTARY_CHARGE_C * (potential - phi_ref) / temperature, -700.0, 700.0)
    electron_density = n_ref * np.exp(exponent)
    tiny = np.finfo(float).tiny
    charge_density = z_i * ion_density
    logarithmic_residual = np.log(np.maximum(charge_density, tiny)) - np.log(np.maximum(electron_density, tiny))
    charge_residual = charge_density - electron_density
    relative_residual = charge_residual / np.maximum(charge_density + electron_density, tiny)
    return {'electron_density_m3': electron_density, 'electron_pressure_pa': electron_density * temperature, 'logarithmic_charge_residual': logarithmic_residual, 'charge_residual_m3': charge_residual, 'relative_charge_residual': relative_residual}
__all__ = ['compute_boltzmann_electron_state']
