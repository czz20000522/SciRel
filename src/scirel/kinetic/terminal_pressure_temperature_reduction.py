"""Terminal H2 pressure and temperature on an explicit thermal-speed carrier.

This two-moment diagnostic retains the saved terminal interface and accepts
zero quadrature cells when each spatial slice has positive density. The
positive-weight relation overlaps the pressure and temperature fields of
``axisymmetric_neutral_moments`` without requiring its higher moments.
"""

from __future__ import annotations

import numpy as np

__all__ = ["reduce_terminal_molecular_pressure_temperature"]

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


def reduce_terminal_molecular_pressure_temperature(
    vr,
    vx,
    mass_ratio,
    thermal_speed_m_s,
    terminal_distribution,
    cylindrical_weight,
    dvx,
):
    """Return terminal H2 pressure and temperature, each with shape (nx,)."""
    radial_velocity = _real_numeric("vr", vr)
    velocity = _real_numeric("vx", vx)
    mass = _real_numeric("mass_ratio", mass_ratio)
    thermal_speed = _real_numeric("thermal_speed_m_s", thermal_speed_m_s)
    distribution = _real_numeric("terminal_distribution", terminal_distribution)
    weight = _real_numeric("cylindrical_weight", cylindrical_weight)
    widths = _real_numeric("dvx", dvx)
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
