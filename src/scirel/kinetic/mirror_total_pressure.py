"""Assemble the terminal ion/electron state for the ambipolar mirror graph."""

from __future__ import annotations

import numpy as np


def assemble_mirror_total_pressure(kinetic_moments, electron_state):
    """Return the admitted total pressure and merged terminal state."""
    required_ion = {"p_parallel_pa", "p_perpendicular_pa", "density_m3"}
    required_electron = {
        "electron_density_m3",
        "electron_pressure_pa",
        "relative_charge_residual",
    }
    if not isinstance(kinetic_moments, dict) or not required_ion <= kinetic_moments.keys():
        raise ValueError("kinetic_moments is missing required ion moment fields")
    if not isinstance(electron_state, dict) or not required_electron <= electron_state.keys():
        raise ValueError("electron_state is missing required electron fields")
    p_parallel, p_perpendicular, electron_pressure = np.broadcast_arrays(
        np.asarray(kinetic_moments["p_parallel_pa"], dtype=float),
        np.asarray(kinetic_moments["p_perpendicular_pa"], dtype=float),
        np.asarray(electron_state["electron_pressure_pa"], dtype=float),
    )
    if not all(
        np.all(np.isfinite(value))
        for value in (p_parallel, p_perpendicular, electron_pressure)
    ):
        raise ValueError("pressure state must be finite")
    electrostatic_potential = electron_state.get("electrostatic_potential")
    state = dict(kinetic_moments)
    state.update(
        {
            "p_parallel": p_parallel + electron_pressure,
            "p_perpendicular": p_perpendicular + electron_pressure,
            "ion_density": kinetic_moments["density_m3"],
            "ion_p_parallel": p_parallel,
            "ion_p_perpendicular": p_perpendicular,
            "electron_density": electron_state["electron_density_m3"],
            "electron_pressure": electron_pressure,
            "electrostatic_potential": electrostatic_potential,
            "relative_charge_residual": electron_state["relative_charge_residual"],
            "kinetic_moments": kinetic_moments,
        }
    )
    return state


__all__ = ["assemble_mirror_total_pressure"]
