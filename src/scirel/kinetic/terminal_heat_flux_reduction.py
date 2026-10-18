"""Terminal H2 random and total heat flux on an explicit thermal-speed carrier.

The random-flux field overlaps ``axisymmetric_neutral_moments`` on positive
quadrature weights. This terminal relation also returns total heat flux and
allows zero quadrature cells when each spatial slice has positive density.
"""

from __future__ import annotations

import numpy as np

__all__ = ["reduce_terminal_molecular_heat_flux"]

H_MASS_KG = 1.6726231e-27
Q_COULOMB = 1.602177e-19


def _real_numeric(name, value):
    try:
        if not isinstance(value, np.ndarray) and any(
            isinstance(item, (bool, np.bool_))
            for item in np.asarray(value, dtype=object).flat
        ):
            raise ValueError
        raw = np.asarray(value)
        if raw.dtype.kind not in "iuf":
            raise ValueError
        return np.asarray(raw, dtype=float)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must contain real numeric values") from exc


def reduce_terminal_molecular_heat_flux(
    radial_velocity_normalized,
    axial_velocity_normalized,
    mass_ratio,
    thermal_speed_m_s,
    terminal_distribution,
    cylindrical_weight,
    dvx,
):
    """Return terminal H2 random and total heat flux, each with shape (nx,)."""
    radial_velocity = _real_numeric("radial_velocity_normalized", radial_velocity_normalized)
    axial_velocity = _real_numeric("axial_velocity_normalized", axial_velocity_normalized)
    mass = _real_numeric("mass_ratio", mass_ratio)
    thermal_speed = _real_numeric("thermal_speed_m_s", thermal_speed_m_s)
    distribution = _real_numeric("terminal_distribution", terminal_distribution)
    weight = _real_numeric("cylindrical_weight", cylindrical_weight)
    widths = _real_numeric("dvx", dvx)
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
    # This is an outer broadcast; keep the per-slice reduction order below
    # unchanged while avoiding Python loops over radial and spatial cells.
    random_velocity_squared = radial_velocity[:, None, None] ** 2 + (
        axial_velocity[None, :, None] - normalized_mean_velocity[None, None, :]
    ) ** 2

    pressure = np.zeros(nx, dtype=float)
    longitudinal_stress = np.zeros(nx, dtype=float)
    random_heat_flux = np.zeros(nx, dtype=float)
    thermal_squared = thermal * thermal
    thermal_cubed = thermal_squared * thermal
    for k in range(nx):
        distribution_slice = distribution[:, :, k]
        random_slice = random_velocity_squared[:, :, k] * distribution_slice
        centered_axial = axial_velocity - normalized_mean_velocity[k]
        weighted_random_second = np.sum(
            weight * (random_slice @ widths)
        )
        pressure[k] = molecule_mass * thermal_squared * weighted_random_second / (
            3.0 * Q_COULOMB
        )
        weighted_axial_second = np.sum(
            weight
            * (
                distribution_slice
                @ (widths * centered_axial**2)
            )
        )
        longitudinal_stress[k] = (
            molecule_mass * thermal_squared * weighted_axial_second / Q_COULOMB
        ) - pressure[k]
        random_heat_flux[k] = 0.5 * molecule_mass * thermal_cubed * np.sum(
            weight
            * (
                random_slice @ (widths * centered_axial)
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
