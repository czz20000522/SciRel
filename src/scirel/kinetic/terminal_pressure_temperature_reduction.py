"""Terminal molecular pressure and temperature reduction for bounded N5."""
from __future__ import annotations

import numpy as np


H_MASS_KG = 1.6726231e-27
Q_COULOMB = 1.602177e-19


def reduce_terminal_molecular_pressure_temperature(
    vr,
    vx,
    mass_ratio,
    thermal_speed_m_s,
    terminal_distribution,
    cylindrical_weight,
    dvx,
):
    """Reduce terminal fH2 into source-defined pH2 and TH2 profiles."""
    radial_velocity = np.asarray(vr, dtype=float)
    velocity = np.asarray(vx, dtype=float)
    mass = np.asarray(mass_ratio, dtype=float)
    thermal_speed = np.asarray(thermal_speed_m_s, dtype=float)
    distribution = np.asarray(terminal_distribution, dtype=float)
    weight = np.asarray(cylindrical_weight, dtype=float)
    widths = np.asarray(dvx, dtype=float)
    valid = (
        radial_velocity.ndim == 1
        and radial_velocity.size > 0
        and velocity.ndim == 1
        and velocity.size > 0
        and mass.ndim == 0
        and np.isfinite(mass)
        and float(mass) > 0.0
        and thermal_speed.ndim == 0
        and np.isfinite(thermal_speed)
        and float(thermal_speed) > 0.0
        and distribution.ndim == 3
        and distribution.shape[0] > 0
        and distribution.shape[1] > 0
        and distribution.shape[2] > 0
        and distribution.shape == (radial_velocity.size, velocity.size, distribution.shape[2])
        and weight.shape == (radial_velocity.size,)
        and widths.shape == (velocity.size,)
        and all(
            np.all(np.isfinite(value))
            for value in (radial_velocity, velocity, distribution, weight, widths)
        )
        and np.all(radial_velocity >= 0.0)
        and np.all(distribution >= 0.0)
        and np.all(weight >= 0.0)
        and np.all(widths >= 0.0)
    )
    if not valid:
        raise ValueError(
            "terminal pressure inputs must be finite, shape-compatible, and physically nonnegative"
        )

    nx = distribution.shape[2]
    density = np.zeros(nx, dtype=float)
    flux = np.zeros(nx, dtype=float)
    for k in range(nx):
        density[k] = np.sum(weight * (distribution[:, :, k] @ widths))
        flux[k] = float(thermal_speed) * np.sum(
            weight * (distribution[:, :, k] @ (velocity * widths))
        )
    if not np.all(np.isfinite(density)) or np.any(density <= 0.0):
        raise ValueError("terminal pressure reduction requires strictly positive density")

    mean_velocity = flux / density
    normalized_mean_velocity = mean_velocity / float(thermal_speed)
    random_velocity_squared = np.zeros_like(distribution)
    for i in range(radial_velocity.size):
        for k in range(nx):
            random_velocity_squared[i, :, k] = radial_velocity[i] ** 2 + (
                velocity - normalized_mean_velocity[k]
            ) ** 2

    pressure = np.zeros(nx, dtype=float)
    thermal_speed_squared = float(thermal_speed) * float(thermal_speed)
    for k in range(nx):
        pressure[k] = (
            (2.0 * float(mass) * H_MASS_KG)
            * thermal_speed_squared
            * np.sum(
                weight
                * ((random_velocity_squared[:, :, k] * distribution[:, :, k]) @ widths)
            )
            / (3.0 * Q_COULOMB)
        )
    if not np.all(np.isfinite(pressure)) or np.any(pressure < 0.0):
        raise ValueError("terminal pressure reduction produced an invalid pressure profile")
    temperature = pressure / density
    if not np.all(np.isfinite(temperature)) or np.any(temperature < 0.0):
        raise ValueError("terminal pressure reduction produced an invalid temperature profile")
    return {
        "pressure_profile_ev_m3": pressure,
        "temperature_profile_ev": temperature,
    }
