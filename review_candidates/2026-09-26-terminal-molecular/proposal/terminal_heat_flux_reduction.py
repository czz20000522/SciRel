"""Terminal molecular random and total heat-flux reduction for bounded N5."""
from __future__ import annotations

import numpy as np


H_MASS_KG = 1.6726231e-27
Q_COULOMB = 1.602177e-19


def reduce_terminal_molecular_heat_flux(
    radial_velocity_normalized,
    axial_velocity_normalized,
    mass_ratio,
    thermal_speed_m_s,
    terminal_distribution,
    cylindrical_weight,
    dvx,
):
    """Reduce terminal fH2 into source-defined qxH2 and qxH2_total profiles."""
    radial_velocity = np.asarray(radial_velocity_normalized, dtype=float)
    axial_velocity = np.asarray(axial_velocity_normalized, dtype=float)
    mass = np.asarray(mass_ratio, dtype=float)
    thermal_speed = np.asarray(thermal_speed_m_s, dtype=float)
    distribution = np.asarray(terminal_distribution, dtype=float)
    weight = np.asarray(cylindrical_weight, dtype=float)
    widths = np.asarray(dvx, dtype=float)
    valid = (
        radial_velocity.ndim == 1
        and radial_velocity.size > 0
        and axial_velocity.ndim == 1
        and axial_velocity.size > 0
        and mass.ndim == 0
        and np.isfinite(mass)
        and float(mass) > 0.0
        and thermal_speed.ndim == 0
        and np.isfinite(thermal_speed)
        and float(thermal_speed) > 0.0
        and distribution.ndim == 3
        and distribution.shape == (
            radial_velocity.size,
            axial_velocity.size,
            distribution.shape[2],
        )
        and distribution.shape[2] > 0
        and weight.shape == (radial_velocity.size,)
        and widths.shape == (axial_velocity.size,)
        and all(
            np.all(np.isfinite(value))
            for value in (radial_velocity, axial_velocity, distribution, weight, widths)
        )
        and np.all(radial_velocity >= 0.0)
        and np.all(distribution >= 0.0)
        and np.all(weight >= 0.0)
        and np.all(widths >= 0.0)
    )
    if not valid:
        raise ValueError(
            "terminal heat-flux inputs must be finite, shape-compatible, and physically nonnegative"
        )

    nx = distribution.shape[2]
    thermal = float(thermal_speed)
    molecule_mass = 2.0 * float(mass) * H_MASS_KG
    density = np.zeros(nx, dtype=float)
    particle_flux = np.zeros(nx, dtype=float)
    for k in range(nx):
        density[k] = np.sum(weight * (distribution[:, :, k] @ widths))
        particle_flux[k] = thermal * np.sum(
            weight * (distribution[:, :, k] @ (axial_velocity * widths))
        )
    if not np.all(np.isfinite(density)) or np.any(density <= 0.0):
        raise ValueError("terminal heat-flux reduction requires strictly positive density")

    mean_velocity = particle_flux / density
    normalized_mean_velocity = mean_velocity / thermal
    random_velocity_squared = np.zeros_like(distribution)
    for i in range(radial_velocity.size):
        for k in range(nx):
            random_velocity_squared[i, :, k] = radial_velocity[i] ** 2 + (
                axial_velocity - normalized_mean_velocity[k]
            ) ** 2

    pressure = np.zeros(nx, dtype=float)
    longitudinal_stress = np.zeros(nx, dtype=float)
    random_heat_flux = np.zeros(nx, dtype=float)
    thermal_squared = thermal * thermal
    thermal_cubed = thermal_squared * thermal
    for k in range(nx):
        weighted_random_second = np.sum(
            weight * ((random_velocity_squared[:, :, k] * distribution[:, :, k]) @ widths)
        )
        pressure[k] = molecule_mass * thermal_squared * weighted_random_second / (
            3.0 * Q_COULOMB
        )
        weighted_axial_second = np.sum(
            weight
            * (
                distribution[:, :, k]
                @ (widths * (axial_velocity - normalized_mean_velocity[k]) ** 2)
            )
        )
        longitudinal_stress[k] = (
            molecule_mass * thermal_squared * weighted_axial_second / Q_COULOMB
        ) - pressure[k]
        random_heat_flux[k] = 0.5 * molecule_mass * thermal_cubed * np.sum(
            weight
            * (
                (random_velocity_squared[:, :, k] * distribution[:, :, k])
                @ (widths * (axial_velocity - normalized_mean_velocity[k]))
            )
        )

    total_heat_flux = (
        (0.5 * density * molecule_mass * mean_velocity * mean_velocity + 2.5 * pressure * Q_COULOMB)
        * mean_velocity
        + Q_COULOMB * longitudinal_stress * mean_velocity
        + random_heat_flux
    )
    outputs = (random_heat_flux, total_heat_flux)
    if not all(np.all(np.isfinite(value)) for value in outputs):
        raise ValueError("terminal heat-flux reduction produced a non-finite profile")
    return {
        "random_heat_flux_profile_w_m2": random_heat_flux,
        "total_heat_flux_profile_w_m2": total_heat_flux,
    }
