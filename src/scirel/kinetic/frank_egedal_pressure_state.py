"""Final gas, electron and hot-ion pressure assembly."""

import numpy as np


def assemble_frank_egedal_pressure(psi, radial_shape, hot_parallel_shape, hot_perpendicular_shape, hot_density_shape, params):
    """Assemble the source-order Frank--Egedal output fields."""
    psi = np.asarray(psi, dtype=float)
    fields = [np.asarray(value, dtype=float) for value in (radial_shape, hot_parallel_shape, hot_perpendicular_shape, hot_density_shape)]
    if psi.ndim != 2 or psi.size == 0 or not np.all(np.isfinite(psi)) or any(value.shape != psi.shape or not np.all(np.isfinite(value)) or np.any(value < 0.0) for value in fields):
        raise ValueError("pressure assembly requires same-shape finite two-dimensional fields")
    if not isinstance(params, dict):
        raise ValueError("params must be a mapping")
    radial, hot_parallel, hot_perpendicular, hot_density = fields
    hot_pressure_scale = float(params.get("hot_pressure_scale", params.get("p0", 1.0)))
    gas_dynamic_pressure = float(params.get("gas_dynamic_pressure", 0.0))
    gas_dynamic_density = params.get("gas_dynamic_density", params.get("background_density"))
    hot_density_scale = params.get("hot_density_scale")
    electron_temperature_value = params.get("electron_temperature")
    scales = [hot_pressure_scale, gas_dynamic_pressure, gas_dynamic_density, hot_density_scale, electron_temperature_value]
    if any(not np.isfinite(float(value)) or float(value) < 0.0 for value in scales if value is not None):
        raise ValueError("pressure, density and temperature scales must be finite and nonnegative")
    p_gd = gas_dynamic_pressure * radial
    density = np.zeros_like(psi, dtype=float)
    if gas_dynamic_density is not None:
        density += float(gas_dynamic_density) * radial
    if hot_density_scale is not None:
        density += float(hot_density_scale) * radial * hot_density
    electron_temperature = None if electron_temperature_value is None else np.full_like(psi, float(electron_temperature_value), dtype=float)
    electron_pressure = 0.0 if electron_temperature is None else density * electron_temperature
    result = {
        "p_parallel": p_gd + electron_pressure + hot_pressure_scale * radial * hot_parallel,
        "p_perp": p_gd + electron_pressure + hot_pressure_scale * radial * hot_perpendicular,
        "density": None if gas_dynamic_density is None and hot_density_scale is None else density,
        "electron_temperature": electron_temperature,
    }
    if any(not np.all(np.isfinite(value)) for value in result.values() if value is not None):
        raise ValueError("pressure assembly produced non-finite fields")
    return result

__all__ = ['assemble_frank_egedal_pressure']
