"""Final gas, electron and hot-ion pressure assembly."""
import numpy as np

def assemble_frank_egedal_pressure(psi, radial_shape, hot_parallel_shape, hot_perpendicular_shape, hot_density_shape, params):
    """Assemble the source-order Frank--Egedal output fields."""
    psi = np.asarray(psi, dtype=float)
    if psi.ndim != 2 or not np.all(np.isfinite(psi)):
        raise ValueError('psi must be a finite two-dimensional [Z,R] grid')
    if not isinstance(params, dict):
        raise ValueError('params must be a mapping')
    fields = [np.asarray(value, dtype=float) for value in (radial_shape, hot_parallel_shape, hot_perpendicular_shape, hot_density_shape)]
    if psi.ndim != 2 or any((value.shape != psi.shape or not np.all(np.isfinite(value)) for value in fields)):
        raise ValueError('pressure assembly requires same-shape finite two-dimensional fields')
    radial, hot_parallel, hot_perpendicular, hot_density = fields
    hot_pressure_scale = float(params.get('hot_pressure_scale', params.get('p0', 1.0)))
    gas_dynamic_pressure = float(params.get('gas_dynamic_pressure', 0.0))
    if not np.isfinite(hot_pressure_scale) or hot_pressure_scale < 0.0 or (not np.isfinite(gas_dynamic_pressure)) or (gas_dynamic_pressure < 0.0):
        raise ValueError('pressure scales must be finite and nonnegative')
    gas_dynamic_density = params.get('gas_dynamic_density', params.get('background_density'))
    hot_density_scale = params.get('hot_density_scale')
    electron_temperature_value = params.get('electron_temperature')
    p_gd = gas_dynamic_pressure * radial
    density = np.zeros_like(psi, dtype=float)
    if gas_dynamic_density is not None:
        gas_dynamic_density = float(gas_dynamic_density)
        if not np.isfinite(gas_dynamic_density) or gas_dynamic_density < 0.0:
            raise ValueError('gas_dynamic_density must be finite and nonnegative')
        density += gas_dynamic_density * radial
    if hot_density_scale is not None:
        hot_density_scale = float(hot_density_scale)
        if not np.isfinite(hot_density_scale) or hot_density_scale < 0.0:
            raise ValueError('hot_density_scale must be finite and nonnegative')
        density += hot_density_scale * radial * hot_density
    if electron_temperature_value is not None:
        electron_temperature_value = float(electron_temperature_value)
        if not np.isfinite(electron_temperature_value) or electron_temperature_value < 0.0:
            raise ValueError('electron_temperature must be finite and nonnegative')
    electron_temperature = None if electron_temperature_value is None else np.full_like(psi, electron_temperature_value, dtype=float)
    electron_pressure = 0.0 if electron_temperature is None else density * electron_temperature
    return {'p_parallel': p_gd + electron_pressure + hot_pressure_scale * radial * hot_parallel, 'p_perp': p_gd + electron_pressure + hot_pressure_scale * radial * hot_perpendicular, 'density': None if gas_dynamic_density is None and hot_density_scale is None else density, 'electron_temperature': electron_temperature}
__all__ = ['assemble_frank_egedal_pressure']
