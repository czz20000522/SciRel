"""Vectorized Boltzmann electron response and charge-neutrality residual."""

from __future__ import annotations
import numpy as np
from scirel._numerics import _scaled_difference

ELEMENTARY_CHARGE_C = 1.602176634e-19


def compute_boltzmann_electron_state(
    potential_v,
    electron_temperature_j,
    electron_density_ref_m3,
    electron_phi_ref_v,
    ion_density_m3,
    ion_charge_state,
):
    """Evaluate unclipped Boltzmann electrons and charge residuals in SI units.

    Density is exp(log(n_ref) + e*(phi-phi_ref)/T_e). The potential
    difference is formed before charge multiplication, with binary scaling for
    intermediate range limits, so a common potential gauge does not erase a
    represented difference. Positive populations
    retain their analytic log residual even when the density underflows to
    zero. The relative residual is tanh(log_ratio/2), avoiding density-sum
    overflow. For an exactly absent species only, logarithmic diagnostics use
    a signed finite proxy of magnitude at least one; the relative residual
    is exactly +/-1 (or zero
    for joint vacuum). A finite density/pressure output is required; an
    unrepresentable result raises rather than clipping the physical exponent.
    """
    potential, temperature, n_ref, phi_ref, ion_density = np.broadcast_arrays(
        *[
            np.asarray(x, dtype=float)
            for x in (
                potential_v,
                electron_temperature_j,
                electron_density_ref_m3,
                electron_phi_ref_v,
                ion_density_m3,
            )
        ]
    )
    z_i = float(ion_charge_state)
    if not np.isfinite(z_i) or z_i <= 0.0:
        raise ValueError("ion_charge_state must be finite and positive")
    if not all(
        np.all(np.isfinite(value))
        for value in (potential, temperature, n_ref, phi_ref, ion_density)
    ):
        raise ValueError("all fields must be finite")
    if np.any(temperature <= 0.0):
        raise ValueError("electron_temperature_j must be positive")
    if np.any(n_ref < 0.0) or np.any(ion_density < 0.0):
        raise ValueError("reference and ion densities cannot be negative")
    with np.errstate(over="ignore", under="ignore", invalid="ignore"):
        exponent = _scaled_difference(potential, phi_ref, ELEMENTARY_CHARGE_C, temperature)
    if not np.all(np.isfinite(exponent)):
        raise FloatingPointError("dimensionless electron potential is not representable")
    electron_log = np.full(n_ref.shape, -np.inf)
    ion_log = np.full(n_ref.shape, -np.inf)
    electrons = n_ref > 0
    ions = ion_density > 0
    electron_log[electrons] = np.log(n_ref[electrons]) + exponent[electrons]
    ion_log[ions] = np.log(ion_density[ions]) + np.log(z_i)
    with np.errstate(over="ignore", under="ignore", invalid="ignore"):
        electron_density = np.exp(electron_log)
        charge_density = z_i * ion_density
        electron_pressure = np.exp(electron_log + np.log(temperature))
    if not all(
        np.all(np.isfinite(x)) for x in (electron_density, charge_density, electron_pressure)
    ):
        raise FloatingPointError("density or pressure exceeds the finite output range")
    both = electrons & ions
    logarithmic_residual = np.zeros(n_ref.shape)
    logarithmic_residual[both] = ion_log[both] - electron_log[both]
    tiny_log = np.log(np.finfo(float).tiny)
    logarithmic_residual[ions & ~electrons] = np.maximum(
        1.0, np.abs(ion_log[ions & ~electrons] - tiny_log)
    )
    logarithmic_residual[electrons & ~ions] = -np.maximum(
        1.0, np.abs(electron_log[electrons & ~ions] - tiny_log)
    )
    if not np.all(np.isfinite(logarithmic_residual)):
        raise FloatingPointError("logarithmic charge residual must be finite")
    relative_residual = np.asarray(np.tanh(0.5 * logarithmic_residual))
    relative_residual[ions & ~electrons] = 1.0
    relative_residual[electrons & ~ions] = -1.0
    return {
        "electron_density_m3": electron_density,
        "electron_pressure_pa": electron_pressure,
        "logarithmic_charge_residual": logarithmic_residual,
        "charge_residual_m3": charge_density - electron_density,
        "relative_charge_residual": relative_residual,
    }


__all__ = ["compute_boltzmann_electron_state"]
