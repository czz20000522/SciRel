"""H(1s) radiative recombination rate from the saved analytic fit."""

from __future__ import annotations

import numpy as np

__all__ = ["evaluate_atomic_hydrogen_1s_radiative_recombination_rate"]

_RY_EV = 13.58
_LEVEL_N = 1.0
_A_NL = 3.92
_X_NL = 0.35


def _positive_temperature(value):
    try:
        raw = np.asarray(value)
        if raw.dtype.kind not in "iuf" or (
            isinstance(value, (list, tuple))
            and any(isinstance(item, (bool, np.bool_))
                    for item in np.asarray(value, dtype=object).flat)
        ):
            raise ValueError
        temperature = np.asarray(raw, dtype=float)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("electron_temperature_ev must contain real numeric values") from exc
    if not np.all(np.isfinite(temperature)):
        raise ValueError("electron_temperature_ev must be finite")
    if np.any(temperature <= 0.0):
        raise ValueError("electron_temperature_ev must be positive")
    return temperature


def evaluate_atomic_hydrogen_1s_radiative_recombination_rate(electron_temperature_ev):
    """Return the H+ + e -> H(1s) + hv rate coefficient in m^3/s."""
    temperature = _positive_temperature(electron_temperature_ev)
    clipped = np.minimum(np.maximum(temperature, 0.1), 2.01e4)
    ionization_energy_ev = _RY_EV / _LEVEL_N
    b_n = ionization_energy_ev / clipped
    rate = _A_NL * 1.0e-14 * np.sqrt(ionization_energy_ev / _RY_EV) * (b_n**1.5 / (b_n + _X_NL)) * 1.0e-6
    if not np.all(np.isfinite(rate)) or np.any(rate <= 0.0):
        raise ValueError("H(1s) radiative recombination fit produced a non-finite or nonpositive rate")
    return rate
