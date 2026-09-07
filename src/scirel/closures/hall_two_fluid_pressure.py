"""Build the explicit two-fluid state consumed by reduced Hall drift closure."""
import numpy as np

def _profile(value, magnetic_field, psi, name):
    raw = value(magnetic_field, psi) if callable(value) else value
    try:
        result = np.broadcast_to(np.asarray(raw, dtype=float), magnetic_field.shape)
    except ValueError as exc:
        raise ValueError(f"Hall profile '{name}' does not match the R-Z grid") from exc
    if not np.all(np.isfinite(result)):
        raise FloatingPointError(f"Hall profile '{name}' contains NaN or infinity")
    return np.asarray(result)

def close_hall_two_fluid_pressure(magnetic_field, psi, pressure_law, ion_density_m3, electron_pressure_pa, electrostatic_potential_v, ion_p_parallel_pa=None, ion_p_perpendicular_pa=None, electron_p_parallel_pa=None, electron_p_perpendicular_pa=None):
    """Return source-compatible total, ion, electron pressure, density, and potential state."""
    b_t, flux = np.broadcast_arrays(np.asarray(magnetic_field, dtype=float), np.asarray(psi, dtype=float))
    if not np.all(np.isfinite(b_t)) or not np.all(np.isfinite(flux)):
        raise ValueError('magnetic_field and psi must be finite')
    if not callable(pressure_law):
        raise TypeError('pressure_law must be callable')
    pressure = pressure_law(b_t, flux)
    if not isinstance(pressure, dict):
        raise TypeError('pressure_law must return a dictionary')
    try:
        parallel = _profile(pressure['p_parallel'], b_t, flux, 'p_parallel')
        perpendicular = _profile(pressure['p_perpendicular'], b_t, flux, 'p_perpendicular')
    except KeyError as exc:
        raise KeyError('pressure_law must return p_parallel and p_perpendicular') from exc
    density = _profile(ion_density_m3, b_t, flux, 'ion_density')
    electron_pressure = _profile(electron_pressure_pa, b_t, flux, 'electron_pressure')
    electron_parallel = _profile(electron_pressure if electron_p_parallel_pa is None else electron_p_parallel_pa, b_t, flux, 'electron_p_parallel')
    electron_perpendicular = _profile(electron_pressure if electron_p_perpendicular_pa is None else electron_p_perpendicular_pa, b_t, flux, 'electron_p_perpendicular')
    potential = _profile(electrostatic_potential_v, b_t, flux, 'electrostatic_potential')
    ion_parallel = parallel - electron_parallel if ion_p_parallel_pa is None else _profile(ion_p_parallel_pa, b_t, flux, 'ion_p_parallel')
    ion_perpendicular = perpendicular - electron_perpendicular if ion_p_perpendicular_pa is None else _profile(ion_p_perpendicular_pa, b_t, flux, 'ion_p_perpendicular')
    if any((np.any(value < 0.0) for value in (density, electron_pressure, electron_parallel, electron_perpendicular, ion_parallel, ion_perpendicular))):
        raise ValueError('Hall fluid closure returned a negative moment')
    return {'p_parallel': parallel, 'p_perpendicular': perpendicular, 'ion_density': density, 'electron_density': density, 'electron_pressure': electron_pressure, 'electron_p_parallel': electron_parallel, 'electron_p_perpendicular': electron_perpendicular, 'electrostatic_potential': potential, 'ion_p_parallel': ion_parallel, 'ion_p_perpendicular': ion_perpendicular}
__all__ = ['close_hall_two_fluid_pressure']
