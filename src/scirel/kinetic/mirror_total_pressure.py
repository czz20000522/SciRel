"""Assemble the terminal ion/electron state for the ambipolar mirror graph."""
from __future__ import annotations
import numpy as np

def assemble_mirror_total_pressure(kinetic_moments, electron_state):
    """Return the source-defined total pressure and merged terminal state."""
    required_ion = {'p_parallel_pa', 'p_perpendicular_pa', 'density_m3'}
    required_electron = {'electron_density_m3', 'electron_pressure_pa', 'relative_charge_residual'}
    if not isinstance(kinetic_moments, dict) or not required_ion <= kinetic_moments.keys():
        raise ValueError('kinetic_moments is missing required ion moment fields')
    if not isinstance(electron_state, dict) or not required_electron <= electron_state.keys():
        raise ValueError('electron_state is missing required electron fields')
    try:
        p_parallel, p_perpendicular, electron_pressure, ion_density, electron_density, charge_residual = np.broadcast_arrays(np.asarray(kinetic_moments['p_parallel_pa'], dtype=float), np.asarray(kinetic_moments['p_perpendicular_pa'], dtype=float), np.asarray(electron_state['electron_pressure_pa'], dtype=float), np.asarray(kinetic_moments['density_m3'], dtype=float), np.asarray(electron_state['electron_density_m3'], dtype=float), np.asarray(electron_state['relative_charge_residual'], dtype=float))
    except ValueError as exc:
        raise ValueError('required ion and electron state fields must share a broadcast shape') from exc
    if not all((np.all(np.isfinite(value)) for value in (p_parallel, p_perpendicular, electron_pressure, ion_density, electron_density, charge_residual))) or np.any(p_parallel < 0.0) or np.any(p_perpendicular < 0.0) or np.any(electron_pressure < 0.0) or np.any(ion_density < 0.0) or np.any(electron_density < 0.0):
        raise ValueError('required ion and electron state fields must be finite and physically nonnegative')
    state = dict(kinetic_moments)
    state.update({'p_parallel': p_parallel + electron_pressure, 'p_perpendicular': p_perpendicular + electron_pressure, 'ion_density': ion_density, 'ion_p_parallel': p_parallel, 'ion_p_perpendicular': p_perpendicular, 'electron_density': electron_density, 'electron_pressure': electron_pressure, 'electrostatic_potential': None, 'relative_charge_residual': charge_residual, 'kinetic_moments': kinetic_moments})
    return state
__all__ = ['assemble_mirror_total_pressure']
