"""Terminal H2 loss, momentum and energy transfer from a caller-owned RHS.

The signed collision RHS and external molecular source are supplied explicitly.
This relation does not assemble the Boltzmann RHS or advance a terminal state.
"""

from __future__ import annotations

import numpy as np

__all__ = ["reduce_terminal_molecular_energy_transfer"]

H_MASS_KG = 1.6726231e-27


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
    """Return terminal H2 loss, thermal, momentum and total transfer profiles."""
    radial_velocity = _real_numeric("radial_velocity_normalized", radial_velocity_normalized)
    axial_velocity = _real_numeric("axial_velocity_normalized", axial_velocity_normalized)
    mass = _real_numeric("mass_ratio", mass_ratio)
    thermal_speed = _real_numeric("thermal_speed_m_s", thermal_speed_m_s)
    distribution = _real_numeric("terminal_distribution", terminal_distribution)
    rhs = _real_numeric("collision_rhs", collision_rhs)
    weight = _real_numeric("cylindrical_weight", cylindrical_weight)
    widths = _real_numeric("dvx", dvx)
    external_source = _real_numeric(
        "external_molecular_source_profile_m3_s", external_molecular_source_profile_m3_s
    )
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
    slices = distribution.transpose(2, 0, 1)
    density = np.sum(np.matmul(slices, widths) * weight[None, :], axis=1)
    particle_flux = thermal * np.sum(
        np.matmul(slices, axial_velocity * widths) * weight[None, :], axis=1
    )
    if not np.all(np.isfinite(density)) or np.any(density <= 0.0):
        raise ValueError("terminal energy-transfer reduction requires strictly positive density")

    mean_velocity = particle_flux / density
    normalized_mean_velocity = mean_velocity / thermal
    # Build the centered random-speed field in one NumPy pass.  The previous
    # nested Python loops assigned each radial/spatial slice separately even
    # though the expression is an outer broadcast.  Broadcasting keeps the
    # same elementwise arithmetic and leaves the per-slice reduction order
    # below unchanged.
    random_velocity_squared = radial_velocity[:, None, None] ** 2 + (
        axial_velocity[None, :, None] - normalized_mean_velocity[None, None, :]
    ) ** 2

    thermal_squared = thermal * thermal
    rhs_slices = rhs.transpose(2, 0, 1)
    random_rhs = random_velocity_squared.transpose(2, 0, 1) * rhs_slices
    thermal_energy_transfer = 0.5 * molecule_mass * thermal_squared * np.sum(
        np.matmul(random_rhs, widths) * weight[None, :], axis=1
    )
    centered_axial = axial_velocity[None, :] - normalized_mean_velocity[:, None]
    momentum_transfer = molecule_mass * thermal * np.sum(
        np.matmul(rhs_slices, (centered_axial * widths[None, :])[..., None]).squeeze(-1)
        * weight[None, :], axis=1,
    )
    loss_rate = -np.sum(np.matmul(rhs_slices, widths) * weight[None, :], axis=1) + external_source

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
