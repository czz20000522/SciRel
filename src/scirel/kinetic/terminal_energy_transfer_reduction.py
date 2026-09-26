"""Terminal molecular energy-transfer reduction for bounded N5."""
from __future__ import annotations

import numpy as np


H_MASS_KG = 1.6726231e-27


def reduce_terminal_molecular_energy_transfer(
    radial_velocity_normalized,
    axial_velocity_normalized,
    mass_ratio,
    thermal_speed_m_s,
    terminal_distribution,
    collision_rhs,
    cylindrical_weight,
    dvx,
    external_molecular_source_profile_m3_s,
):
    """Reduce caller-owned terminal distribution and Boltzmann RHS to QH2 rates."""
    radial_velocity = np.asarray(radial_velocity_normalized, dtype=float)
    axial_velocity = np.asarray(axial_velocity_normalized, dtype=float)
    mass = np.asarray(mass_ratio, dtype=float)
    thermal_speed = np.asarray(thermal_speed_m_s, dtype=float)
    distribution = np.asarray(terminal_distribution, dtype=float)
    rhs = np.asarray(collision_rhs, dtype=float)
    weight = np.asarray(cylindrical_weight, dtype=float)
    widths = np.asarray(dvx, dtype=float)
    external_source = np.asarray(external_molecular_source_profile_m3_s, dtype=float)
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
        and distribution.shape[0] == radial_velocity.size
        and distribution.shape[1] == axial_velocity.size
        and distribution.shape[2] > 0
        and rhs.shape == distribution.shape
        and weight.shape == (radial_velocity.size,)
        and widths.shape == (axial_velocity.size,)
        and external_source.shape == (distribution.shape[2],)
        and all(
            np.all(np.isfinite(value))
            for value in (radial_velocity, axial_velocity, distribution, rhs, weight, widths, external_source)
        )
        and np.all(radial_velocity >= 0.0)
        and np.all(distribution >= 0.0)
        and np.all(weight >= 0.0)
        and np.all(widths >= 0.0)
    )
    if not valid:
        raise ValueError(
            "terminal energy-transfer inputs must be finite, shape-compatible, and physically nonnegative"
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
        raise ValueError("terminal energy-transfer reduction requires strictly positive density")

    mean_velocity = particle_flux / density
    normalized_mean_velocity = mean_velocity / thermal
    random_velocity_squared = np.zeros_like(distribution)
    for i in range(radial_velocity.size):
        for k in range(nx):
            random_velocity_squared[i, :, k] = radial_velocity[i] ** 2 + (
                axial_velocity - normalized_mean_velocity[k]
            ) ** 2

    thermal_squared = thermal * thermal
    thermal_energy_transfer = np.zeros(nx, dtype=float)
    momentum_transfer = np.zeros(nx, dtype=float)
    loss_rate = np.zeros(nx, dtype=float)
    for k in range(nx):
        rhs_slice = rhs[:, :, k]
        thermal_energy_transfer[k] = 0.5 * molecule_mass * thermal_squared * np.sum(
            weight * ((random_velocity_squared[:, :, k] * rhs_slice) @ widths)
        )
        momentum_transfer[k] = molecule_mass * thermal * np.sum(
            weight
            * (rhs_slice @ (widths * (axial_velocity - normalized_mean_velocity[k])))
        )
        loss_rate[k] = -np.sum(weight * (rhs_slice @ widths)) + external_source[k]

    total_energy_transfer = (
        thermal_energy_transfer
        + momentum_transfer * mean_velocity
        - 0.5 * molecule_mass * (loss_rate - external_source) * mean_velocity * mean_velocity
    )
    outputs = (loss_rate, thermal_energy_transfer, momentum_transfer, total_energy_transfer)
    if not all(np.all(np.isfinite(value)) for value in outputs):
        raise ValueError("terminal energy-transfer reduction produced a non-finite profile")
    return {
        "loss_rate_profile_m3_s": loss_rate,
        "thermal_energy_transfer_rate_profile_w_m3": thermal_energy_transfer,
        "momentum_transfer_rate_profile_n_m2": momentum_transfer,
        "total_energy_transfer_rate_profile_w_m3": total_energy_transfer,
    }
