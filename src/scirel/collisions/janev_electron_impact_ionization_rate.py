"""Janev electron-impact ionization-rate fits for H and H2."""

from __future__ import annotations


import numpy as np

from ._energy_input import log_polynomial, positive_real_array

__all__ = ["evaluate_janev_electron_impact_ionization_rate"]

_COEFFICIENTS = {
    "H": np.array(
        [
            -3.271396786375e1,
            1.353655609057e1,
            -5.739328757388,
            1.563154982022,
            -2.877056004391e-1,
            3.482559773737e-2,
            -2.631976175590e-3,
            1.119543953861e-4,
            -2.039149852002e-6,
        ]
    ),
    "H2": np.array(
        [
            -3.568640293666e1,
            1.733468989961e1,
            -7.767469363538,
            2.211579405415,
            -4.169840174384e-1,
            5.088289820867e-2,
            -3.832737518325e-3,
            1.612863120371e-4,
            -2.893391904431e-6,
        ]
    ),
}


def evaluate_janev_electron_impact_ionization_rate(
    electron_temperature_ev,
    target_species,
):
    """Return the H or H2 Maxwellian ionization fit in m^3/s."""
    if not isinstance(target_species, str) or target_species not in _COEFFICIENTS:
        raise ValueError("target_species must be H or H2")
    temperature = positive_real_array(electron_temperature_ev, "electron_temperature_ev")
    clipped = np.clip(temperature, 0.1, 2.01e4)
    rate = np.exp(log_polynomial(np.log(clipped), _COEFFICIENTS[target_species])) * 1.0e-6
    if not np.all(np.isfinite(rate)) or np.any(rate <= 0.0):
        raise ValueError("Janev ionization fit produced a non-finite or nonpositive rate")
    return rate
