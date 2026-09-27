"""FIDASIM DCX/halo collisional-radiative initial-state weighting.

Source: FIDASIM ``colrad`` initial-state preparation for one DCX/halo
marker (the saved package ``DCXCX初态与光子快离子修正``) -- select the
thermal species, add the fast-ion density only on the exact-isotope branch
(``beam_mass_amu == thermal_mass_amu[selected]``), weight the caller's
level-resolved CX rates by the source density, and derive the photon
fast-ion correction (the thermal share when the fast ion was included,
else 1).  Rates, densities and masses are caller-owned; the operator does
not generate rates, trajectories or photons.

Registered hardenings against the saved arm: the initial-state products
``rates * source_density`` can overflow to Inf for finite extremes; the
saved arm returns them silently and reports ``eligible=True``.  Every
returned value must stay finite.
"""
from __future__ import annotations

import numpy as np

__all__ = ["prepare_dcx_colrad_initial_state"]


def prepare_dcx_colrad_initial_state(*, cx_rate_per_s, thermal_ion_density_cm3,
                                     thermal_mass_amu, selected_thermal_species_index,
                                     fast_ion_density_cm3, beam_mass_amu):
    """Return the source ``states`` and photon fast-ion correction for one DCX marker."""
    rates = np.asarray(cx_rate_per_s, dtype=float)
    density = np.asarray(thermal_ion_density_cm3, dtype=float)
    masses = np.asarray(thermal_mass_amu, dtype=float)
    index = selected_thermal_species_index
    if (rates.ndim != 1 or rates.size == 0 or density.ndim != 1 or masses.shape != density.shape):
        raise ValueError("rates and aligned thermal density/mass vectors are required")
    if (not np.all(np.isfinite(rates)) or not np.all(np.isfinite(density)) or not np.all(np.isfinite(masses))
            or np.any(rates < 0.0) or np.any(density < 0.0) or np.any(masses <= 0.0)
            or fast_ion_density_cm3 < 0.0 or beam_mass_amu <= 0.0 or not np.isfinite(fast_ion_density_cm3)
            or not np.isfinite(beam_mass_amu) or isinstance(index, (bool, np.bool_))
            or not isinstance(index, (int, np.integer))
            or not 0 <= index < density.size):
        raise ValueError("finite nonnegative rates/densities and a valid selected species are required")
    index = int(index)
    thermal_density = float(density[index])
    same_isotope = bool(beam_mass_amu == masses[index])
    source_density = thermal_density + (float(fast_ion_density_cm3) if same_isotope else 0.0)
    initial_states = rates * source_density
    correction = thermal_density / source_density if same_isotope and source_density > 0.0 else 1.0
    # Registered hardening: finite extremes can overflow the products and
    # the correction denominator; the saved arm returns Inf silently.
    if not (np.all(np.isfinite(initial_states)) and np.isfinite(source_density)
            and np.isfinite(correction)):
        raise ValueError(
            "initial-state outputs are non-finite for finite but extreme "
            "input magnitudes (registered hardening)")
    eligible = bool(np.sum(initial_states) > 0.0)
    return {
        "initial_states": initial_states,
        "photon_fast_ion_correction": max(correction, 0.0),
        "source_density_cm3": source_density,
        "same_isotope": same_isotope,
        "eligible": eligible,
    }
