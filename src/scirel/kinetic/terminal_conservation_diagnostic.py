"""Bounded source-defined QH2_total conservation diagnostic."""
from __future__ import annotations

import numpy as np


def reduce_qh2_total_conservation_diagnostic(
    axial_position_m,
    total_heat_flux_profile_w_m2,
    total_energy_transfer_rate_profile_w_m3,
):
    """Reduce caller-owned qxH2_total and QH2_total profiles to source error."""
    position = np.asarray(axial_position_m, dtype=float)
    total_heat_flux = np.asarray(total_heat_flux_profile_w_m2, dtype=float)
    total_energy_transfer = np.asarray(total_energy_transfer_rate_profile_w_m3, dtype=float)
    valid = (
        position.ndim == 1
        and position.size >= 2
        and total_heat_flux.shape == position.shape
        and total_energy_transfer.shape == position.shape
        and np.all(np.isfinite(position))
        and np.all(np.isfinite(total_heat_flux))
        and np.all(np.isfinite(total_energy_transfer))
        and np.all(np.isfinite(np.diff(position)))
        and np.all(np.diff(position) != 0.0)
    )
    if not valid:
        raise ValueError(
            "QH2_total diagnostic requires finite one-dimensional profiles and nonzero axial spacing"
        )

    q1 = np.zeros_like(position)
    q2 = np.zeros_like(position)
    q1[:-1] = np.diff(total_heat_flux) / np.diff(position)
    q2[:-1] = 0.5 * (total_energy_transfer[1:] + total_energy_transfer[:-1])
    normalization = np.max(np.abs(np.asarray([q1, q2])))
    if not np.isfinite(normalization) or normalization <= 0.0:
        raise ValueError("QH2_total diagnostic requires a strictly positive global normalization")
    error = np.abs(q1 - q2) / normalization
    if not np.all(np.isfinite(error)):
        raise ValueError("QH2_total diagnostic produced a non-finite profile")
    return {"total_energy_conservation_error_profile_dimensionless": error}
