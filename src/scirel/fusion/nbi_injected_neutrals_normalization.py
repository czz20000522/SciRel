"""FIDASIM ndmc NBI power-to-neutral-state normalization (N2 leaf).

Source: FIDASIM ``ndmc`` normalization -- total neutral rate
``nneutrals = 1e6 * P_MW / (1e3 * E_keV * e * sum_k(fraction_k / k))`` with
e = 1.602176634e-19 C (CODATA 2018 in this leaf; the older
``scirel.fusion.nbi-component-initial-state`` leaf keeps the source's
1.60217733e-19 as a distinct, explicitly documented contract), component
rates ``nneutrals * fraction_k``, and per-cell initial densities divided by
the beam-grid cell volume.

Registered hardening: finite extreme inputs can overflow the weight factor,
the total rate or the densities; the saved arm returns Inf silently.  Zero
power is valid and yields an all-zero result.
"""
from __future__ import annotations

import numpy as np

__all__ = ["normalize_nbi_injected_neutrals"]

ELEMENTARY_CHARGE_C = 1.602176634e-19


def normalize_nbi_injected_neutrals(injected_power_mw, injection_energy_kev, current_fractions, beam_grid_cell_volume_cm3):
    """Return total neutral rate and full/half/third initial state density."""
    fractions = np.asarray(current_fractions, dtype=float)
    if (fractions.shape != (3,) or not np.all(np.isfinite(fractions))
            or np.any(fractions < 0)
            or not np.isfinite(injected_power_mw) or injected_power_mw < 0
            or not np.isfinite(injection_energy_kev) or injection_energy_kev <= 0
            or not np.isfinite(beam_grid_cell_volume_cm3)
            or beam_grid_cell_volume_cm3 <= 0):
        raise ValueError("power/fractions must be finite nonnegative and energy/volume finite positive")
    energy_factor = fractions @ np.array([1., .5, 1. / 3.])
    if energy_factor == 0:
        raise ValueError("at least one current fraction must be positive")
    if not np.isfinite(energy_factor):
        raise ValueError(
            "energy weight factor overflowed for finite but extreme current "
            "fractions (registered hardening)")
    total = 1e6 * injected_power_mw / (1e3 * injection_energy_kev * ELEMENTARY_CHARGE_C * energy_factor)
    densities = total * fractions / beam_grid_cell_volume_cm3
    if not np.isfinite(total) or not np.all(np.isfinite(densities)):
        raise ValueError(
            "NBI normalization overflowed to non-finite rates/densities for "
            "finite but extreme input magnitudes (registered hardening)")
    return {
        "total_neutral_rate_s_inv": total,
        "component_neutral_rate_s_inv": total * fractions,
        "initial_state_rate_per_volume_cm_inv3_s_inv": densities,
        "energy_weight_factor": energy_factor,
    }
