"""Terminal molecular flux and axial mean-velocity reduction for bounded N5."""
from __future__ import annotations

import numpy as np


def reduce_terminal_molecular_flux_velocity(
    vx,
    thermal_speed_m_s,
    terminal_distribution,
    cylindrical_weight,
    dvx,
):
    """Reduce a terminal fH2 distribution into GammaxH2 and VxH2 profiles."""
    velocity = np.asarray(vx, dtype=float)
    thermal_speed = np.asarray(thermal_speed_m_s, dtype=float)
    distribution = np.asarray(terminal_distribution, dtype=float)
    weight = np.asarray(cylindrical_weight, dtype=float)
    widths = np.asarray(dvx, dtype=float)
    valid = (
        velocity.ndim == 1
        and velocity.size > 0
        and thermal_speed.ndim == 0
        and np.isfinite(thermal_speed)
        and float(thermal_speed) > 0.0
        and distribution.ndim == 3
        and distribution.shape[0] > 0
        and distribution.shape[1] > 0
        and distribution.shape[2] > 0
        and velocity.shape == (distribution.shape[1],)
        and weight.shape == (distribution.shape[0],)
        and widths.shape == (distribution.shape[1],)
        and all(
            np.all(np.isfinite(value))
            for value in (velocity, distribution, weight, widths)
        )
        and np.all(distribution >= 0.0)
        and np.all(weight >= 0.0)
        and np.all(widths >= 0.0)
    )
    if not valid:
        raise ValueError(
            "terminal flux inputs must be finite, shape-compatible, and physically nonnegative"
        )

    density = np.zeros(distribution.shape[2], dtype=float)
    flux = np.zeros(distribution.shape[2], dtype=float)
    for k in range(distribution.shape[2]):
        density[k] = np.sum(weight * (distribution[:, :, k] @ widths))
        flux[k] = float(thermal_speed) * np.sum(
            weight * (distribution[:, :, k] @ (velocity * widths))
        )
    if not np.all(np.isfinite(density)) or np.any(density <= 0.0):
        raise ValueError("terminal flux reduction requires strictly positive density")
    if not np.all(np.isfinite(flux)):
        raise ValueError("terminal flux reduction produced a nonfinite flux profile")
    mean_velocity = flux / density
    if not np.all(np.isfinite(mean_velocity)):
        raise ValueError("terminal flux reduction produced a nonfinite mean velocity profile")
    return {
        "flux_profile_m2_s": flux,
        "mean_velocity_profile_m_s": mean_velocity,
    }
