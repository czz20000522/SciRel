"""Terminal H2 total-energy conservation error from caller-owned profiles."""

from __future__ import annotations

import numpy as np

__all__ = ["reduce_qh2_total_conservation_diagnostic"]


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


def reduce_qh2_total_conservation_diagnostic(
    axial_position_m,
    total_heat_flux_profile_w_m2,
    total_energy_transfer_rate_profile_w_m3,
):
    """Return source-defined normalized energy-balance error at axial nodes."""
    position = _real_numeric("axial_position_m", axial_position_m)
    total_heat_flux = _real_numeric(
        "total_heat_flux_profile_w_m2", total_heat_flux_profile_w_m2
    )
    total_energy_transfer = _real_numeric(
        "total_energy_transfer_rate_profile_w_m3",
        total_energy_transfer_rate_profile_w_m3,
    )
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
    if not np.isfinite(normalization):
        raise ValueError("QH2_total diagnostic produced a non-finite normalization")
    if normalization <= 0.0:
        raise ValueError("QH2_total diagnostic requires a strictly positive global normalization")
    error = np.abs(q1 - q2) / normalization
    if not np.all(np.isfinite(error)):
        raise ValueError("QH2_total diagnostic produced a non-finite profile")
    return {"total_energy_conservation_error_profile_dimensionless": error}
