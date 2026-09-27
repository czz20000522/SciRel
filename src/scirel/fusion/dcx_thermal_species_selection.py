"""FIDASIM DCX thermal-species selection by source index."""
from __future__ import annotations

import numpy as np

__all__ = ["select_dcx_thermal_species_mass"]


def select_dcx_thermal_species_mass(thermal_mass_amu, selected_thermal_species_index):
    """Return the declared thermal-ion mass for the source species loop."""
    masses = np.asarray(thermal_mass_amu, float)
    selected = selected_thermal_species_index
    if (masses.ndim != 1 or masses.size == 0 or not np.all(np.isfinite(masses))
            or np.any(masses <= 0) or isinstance(selected, bool) or not isinstance(selected, (int, np.integer))
            or not 0 <= selected < masses.size):
        raise ValueError("selected_thermal_species_index must be an in-range integer")
    return float(masses[selected])
