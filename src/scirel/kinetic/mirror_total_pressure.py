"""Combine ion and electron pressures into one finite mirror state with charge residual diagnostics."""

from __future__ import annotations

import numpy as np


def assemble_mirror_total_pressure(kinetic_moments, electron_state):
    """Assemble species pressures and preserve finite observational charge residual.

    This leaf does not certify neutrality; the calling potential solver owns
    that gate. Invalid density/residual/potential states are rejected instead
    of the predecessor unchecked pass-through."""
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
    # Include all physical fields in the common broadcast shape; scalar
    # moments remain valid when an observational potential carries the grid.
    fields = [
        kinetic_moments["p_parallel_pa"],
        kinetic_moments["p_perpendicular_pa"],
        electron_state["electron_pressure_pa"],
        kinetic_moments["density_m3"],
        electron_state["electron_density_m3"],
        electron_state["relative_charge_residual"],
    ]
    if electron_state.get("electrostatic_potential") is not None:
        fields.append(electron_state["electrostatic_potential"])
    physical = np.broadcast_arrays(*[np.asarray(x, dtype=float) for x in fields])
    p_parallel, p_perpendicular, electron_pressure = physical[:3]
    if not all(
        np.all(np.isfinite(value)) for value in (p_parallel, p_perpendicular, electron_pressure)
    ):
        raise ValueError("pressure state must be finite")
    for name, value in (
        ("ion density", kinetic_moments["density_m3"]),
        ("electron density", electron_state["electron_density_m3"]),
    ):
        values = np.asarray(value, dtype=float)
        if not np.all(np.isfinite(values)) or np.any(values < 0):
            raise ValueError(f"{name} must be finite and nonnegative")
        try:
            np.broadcast_to(values, p_parallel.shape)
        except ValueError as exc:
            raise ValueError(f"{name} must match the pressure shape") from exc
    residual = np.asarray(electron_state["relative_charge_residual"], dtype=float)
    if not np.all(np.isfinite(residual)):
        raise ValueError("relative charge residual must be finite")
    try:
        np.broadcast_to(residual, p_parallel.shape)
    except ValueError as exc:
        raise ValueError("relative charge residual must match the pressure shape") from exc
    if any(np.any(x < 0) for x in (p_parallel, p_perpendicular, electron_pressure)):
        raise ValueError("species pressures must be nonnegative")
    if not np.all(np.isfinite(p_parallel + electron_pressure)) or not np.all(
        np.isfinite(p_perpendicular + electron_pressure)
    ):
        raise FloatingPointError("total pressure exceeds the finite output range")
    electrostatic_potential = electron_state.get("electrostatic_potential")
    if electrostatic_potential is not None:
        potential = np.asarray(electrostatic_potential, dtype=float)
        if not np.all(np.isfinite(potential)):
            raise ValueError("electrostatic potential must be finite")
        try:
            np.broadcast_to(potential, p_parallel.shape)
        except ValueError as exc:
            raise ValueError("electrostatic potential must match the pressure shape") from exc
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
