"""H(1s) radiative recombination rate from the saved analytic fit."""

from __future__ import annotations

# HELD: human-review exposure guard
from scirel._hold import require_review_import
require_review_import(__name__)


import numpy as np

from ._energy_input import positive_real_array

__all__ = ["evaluate_atomic_hydrogen_1s_radiative_recombination_rate"]

_RY_EV = 13.58
_LEVEL_N = 1.0
_A_NL = 3.92
_X_NL = 0.35


def evaluate_atomic_hydrogen_1s_radiative_recombination_rate(electron_temperature_ev):
    """Return the H+ + e -> H(1s) + hv rate coefficient in m^3/s."""
    temperature = positive_real_array(electron_temperature_ev, "electron_temperature_ev")
    clipped = np.minimum(np.maximum(temperature, 0.1), 2.01e4)
    ionization_energy_ev = _RY_EV / _LEVEL_N
    b_n = ionization_energy_ev / clipped
    rate = _A_NL * 1.0e-14 * np.sqrt(ionization_energy_ev / _RY_EV) * (b_n**1.5 / (b_n + _X_NL)) * 1.0e-6
    if not np.all(np.isfinite(rate)) or np.any(rate <= 0.0):
        raise ValueError("H(1s) radiative recombination fit produced a non-finite or nonpositive rate")
    return rate
