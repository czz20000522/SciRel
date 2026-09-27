"""Input contract shared by the collision-energy cross-section fits."""

from __future__ import annotations

import numpy as np


def finite_nonnegative_energy(value):
    try:
        raw = np.asarray(value)
        if raw.dtype.kind not in "iuf" or (
            isinstance(value, (list, tuple))
            and any(isinstance(item, (bool, np.bool_)) for item in np.asarray(value, dtype=object).flat)
        ):
            raise ValueError
        energy = np.asarray(raw, dtype=float)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("energy_ev must be a finite real array") from exc
    if not np.all(np.isfinite(energy)):
        raise ValueError("energy_ev must be finite")
    if np.any(energy < 0.0):
        raise ValueError("energy_ev must be nonnegative")
    return energy
