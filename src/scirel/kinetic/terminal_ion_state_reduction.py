"""Terminal molecular-ion density and temperature reduction for bounded N5."""
from __future__ import annotations

import numpy as np


def reduce_terminal_molecular_ion_state(
    molecular_density_m3,
    neutral_density_m3,
    ion_temperature_ev,
    mass_ratio,
    ionization_rate_s_inv,
    reaction_rate_table_s_inv,
    loss_frequency_s_inv,
):
    """Reduce caller-owned terminal state to source-defined nHP, THP, NuDis and NuE."""
    molecular_density = np.asarray(molecular_density_m3, dtype=float)
    neutral_density = np.asarray(neutral_density_m3, dtype=float)
    ion_temperature = np.asarray(ion_temperature_ev, dtype=float)
    mass = np.asarray(mass_ratio, dtype=float)
    ionization_rate = np.asarray(ionization_rate_s_inv, dtype=float)
    reaction_rates = np.asarray(reaction_rate_table_s_inv, dtype=float)
    loss_frequency = np.asarray(loss_frequency_s_inv, dtype=float)
    nx = molecular_density.size
    valid = (
        molecular_density.ndim == 1
        and nx > 0
        and neutral_density.shape == (nx,)
        and ion_temperature.shape == (nx,)
        and mass.ndim == 0
        and np.isfinite(mass)
        and float(mass) > 0.0
        and ionization_rate.shape == (nx,)
        and reaction_rates.ndim == 2
        and reaction_rates.shape == (nx, 11)
        and loss_frequency.shape == (nx,)
        and all(
            np.all(np.isfinite(value))
            for value in (
                molecular_density,
                neutral_density,
                ion_temperature,
                ionization_rate,
                reaction_rates,
                loss_frequency,
            )
        )
        and np.all(molecular_density >= 0.0)
        and np.all(neutral_density >= 0.0)
        and np.all(ion_temperature > 0.0)
        and np.all(ionization_rate >= 0.0)
        and np.all(reaction_rates >= 0.0)
        and np.all(loss_frequency >= 0.0)
    )
    if not valid:
        raise ValueError(
            "terminal molecular-ion inputs must be finite, shape-compatible, and physically nonnegative"
        )

    dissociation_frequency = neutral_density * np.sum(reaction_rates[:, 7:11], axis=1)
    energy_exchange_frequency = (
        7.7e-7 * neutral_density * 1.0e-6
    ) / (np.sqrt(float(mass)) * (ion_temperature**1.5))
    density_denominator = dissociation_frequency + loss_frequency
    if not np.all(np.isfinite(density_denominator)) or np.any(density_denominator <= 0.0):
        raise ValueError(
            "terminal molecular-ion reduction requires strictly positive molecular-ion density denominator"
        )
    molecular_ion_density = (
        molecular_density * neutral_density * ionization_rate / density_denominator
    )
    temperature_denominator = energy_exchange_frequency + density_denominator
    if not np.all(np.isfinite(temperature_denominator)) or np.any(temperature_denominator <= 0.0):
        raise ValueError(
            "terminal molecular-ion reduction requires strictly positive temperature denominator"
        )
    molecular_ion_temperature = (
        ion_temperature * energy_exchange_frequency / temperature_denominator
    )
    values = (
        molecular_ion_density,
        molecular_ion_temperature,
        dissociation_frequency,
        energy_exchange_frequency,
    )
    if not all(np.all(np.isfinite(value)) and np.all(value >= 0.0) for value in values):
        raise ValueError("terminal molecular-ion reduction produced an invalid profile")
    return {
        "molecular_ion_density_m3": molecular_ion_density,
        "molecular_ion_temperature_ev": molecular_ion_temperature,
        "dissociation_frequency_s_inv": dissociation_frequency,
        "energy_exchange_frequency_s_inv": energy_exchange_frequency,
    }
