"""Materialize one source-faithful NBI energy component as a six-level state.

Source: FIDASIM NBI energy-component initial-state materialization -- the full,
half and third energy components each start with only atomic level 1
populated: ``states(1) = nneutrals * fraction / dv`` with
``nneutrals = 1e6 * power / (1e3 * E * e * sum_k(fraction_k / k))`` in the
source's cm-gram-second-derived units.  This relation is deliberately
separate from the older three-component projection, whose CODATA e0 remains
a distinct, explicitly documented contract.
"""

from __future__ import annotations

import numpy as np


# Source fidasim.f90:69.  The source ndmc path uses this value for states(1).
ELEMENTARY_CHARGE_C = 1.60217733e-19
_ENERGY_DENOMINATORS = (1.0, 2.0, 3.0)


def _scalar(value, name: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not np.isscalar(value):
        raise ValueError(f"{name} must be a scalar")
    number = float(value)
    if not np.isfinite(number) or (number <= 0.0 if positive else number < 0.0):
        qualifier = "finite and positive" if positive else "finite and nonnegative"
        raise ValueError(f"{name} must be {qualifier}")
    return number


def materialize_nbi_component_initial_state(
    injected_power_mw,
    injection_energy_kev,
    current_fractions,
    beam_grid_cell_volume_cm3,
    energy_component,
    nlevels,
):
    """Return ``states(1)=nneutrals*fraction/dv`` for one NBI component.

    The source has six atomic levels and independently starts the full, half,
    and third energy loops with only Fortran level 1 populated.  This operator
    is deliberately separate from the older three-component projection, whose
    CODATA e0 remains a distinct, explicitly documented contract.
    """
    power = _scalar(injected_power_mw, "injected_power_mw")
    energy = _scalar(injection_energy_kev, "injection_energy_kev", positive=True)
    volume = _scalar(beam_grid_cell_volume_cm3, "beam_grid_cell_volume_cm3", positive=True)
    if isinstance(nlevels, bool) or not isinstance(nlevels, (int, np.integer)) or int(nlevels) != 6:
        raise ValueError("nlevels must equal the source six-level contract")
    if isinstance(energy_component, bool) or not isinstance(energy_component, (int, np.integer)):
        raise ValueError("energy_component must be one of 1, 2, or 3")
    component = int(energy_component)
    if component not in (1, 2, 3):
        raise ValueError("energy_component must be one of 1, 2, or 3")
    fractions = np.asarray(current_fractions, dtype=float)
    if fractions.shape != (3,) or not np.all(np.isfinite(fractions)) or np.any(fractions < 0.0):
        raise ValueError("current_fractions must be a finite nonnegative triple")
    energy_factor = float(sum(fraction / denominator for fraction, denominator in zip(fractions, _ENERGY_DENOMINATORS)))
    # Registered hardening: three finite max-float fractions overflow the
    # weight-factor sum to Inf; the saved arm would then return rate 0 with
    # an Inf factor instead of failing.  The factor must be finite and
    # positive before the rate division.
    if not np.isfinite(energy_factor):
        raise ValueError(
            "energy weight factor overflowed to a non-finite value for "
            "finite but extreme current fractions (registered hardening)")
    if energy_factor <= 0.0 or fractions[component - 1] <= 0.0:
        raise ValueError("selected energy component and total current fraction must be positive")
    nneutrals = 1.0e6 * power / (1.0e3 * energy * ELEMENTARY_CHARGE_C * energy_factor)
    # Registered hardening: finite extreme power/volume ratios can overflow;
    # the saved arm would return Inf source-rate-per-volume values silently.  Both the total rate
    # and the per-cell source-rate-per-volume (rate * fraction / volume) are checked.
    if not np.isfinite(nneutrals):
        raise ValueError(
            'initial-state materialization overflowed to a non-finite rate '
            'for finite but extreme input magnitudes (registered hardening)')
    states = np.zeros(6, dtype=np.float64)
    states[0] = nneutrals * fractions[component - 1] / volume
    component_rate = nneutrals * fractions[component - 1]
    if not np.isfinite(states[0]) or not np.isfinite(component_rate):
        raise ValueError(
            'initial-state materialization overflowed to non-finite '
            'densities for finite but extreme input magnitudes (registered '
            'hardening)')
    return {
        "energy_component": component,
        "energy_component_name": ("full", "half", "third")[component - 1],
        "elementary_charge_c": ELEMENTARY_CHARGE_C,
        "energy_weight_factor": energy_factor,
        "total_neutral_rate_s_inv": float(nneutrals),
        "component_neutral_rate_s_inv": float(component_rate),
        "initial_state_rate_per_volume_cm_inv3_s_inv": states,
        "initial_state_index_one_based": 1,
        "nlevels": 6,
    }
