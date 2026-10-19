"""Terminal H2+ density and temperature from caller-owned state profiles.

The reaction table and frequencies are supplied directly. This relation does
not assemble collision tables or evolve a terminal molecular-ion state.
"""

from __future__ import annotations

import numpy as np

__all__ = ["reduce_terminal_molecular_ion_state"]


def _real_numeric(name, value):
    try:
        if not isinstance(value, np.ndarray) and any(
            isinstance(item, (bool, np.bool_))
            for item in np.asarray(value, dtype=object).flat
        ):
            raise ValueError
        raw = np.asarray(value)
        if raw.dtype.kind not in "iuf":
            raise ValueError
        return np.asarray(raw, dtype=float)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must contain real numeric values") from exc


def reduce_terminal_molecular_ion_state(
    molecular_density_m3,
    neutral_density_m3,
    ion_temperature_ev,
    mass_ratio,
    ionization_rate_s_inv,
    reaction_rate_table_s_inv,
    loss_frequency_s_inv,
):
    """Return four terminal H2+ profiles, each with shape (nx,)."""
    molecular_density = _real_numeric("molecular_density_m3", molecular_density_m3)
    neutral_density = _real_numeric("neutral_density_m3", neutral_density_m3)
    ion_temperature = _real_numeric("ion_temperature_ev", ion_temperature_ev)
    mass = _real_numeric("mass_ratio", mass_ratio)
    ionization_rate = _real_numeric("ionization_rate_s_inv", ionization_rate_s_inv)
    reaction_rates = _real_numeric("reaction_rate_table_s_inv", reaction_rate_table_s_inv)
    loss_frequency = _real_numeric("loss_frequency_s_inv", loss_frequency_s_inv)
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

    dissociation_channels = reaction_rates[:, 7:11]
    dissociation_frequency = neutral_density * np.sum(dissociation_channels, axis=1)
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
