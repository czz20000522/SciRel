"""Assemble the explicit neutral Boltzmann RHS state used by the neutral-transport formulation diagnostics."""
from __future__ import annotations

import numpy as np

__all__ = ["assemble_neutral_boltzmann_rhs"]


def _finite_real_array(value, name):
    try:
        if isinstance(value, (list, tuple)) and any(
            isinstance(item, (bool, np.bool_)) for item in np.asarray(value, dtype=object).flat
        ):
            raise ValueError
        raw = np.asarray(value)
        if raw.dtype.kind not in "iuf":
            raise ValueError
        result = np.asarray(raw, dtype=float)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be a finite real array") from exc
    if not np.all(np.isfinite(result)):
        raise ValueError(f"{name} must be a finite real array")
    return result


def _assemble_collision_balance(arrays):
    """Form the signed local source balance before applying the speed scale."""
    return (
        arrays["coefficient_source_distribution"]
        + arrays["charge_exchange_source_sum"]
        - arrays["collision_frequency_s_inv"] * arrays["total_distribution"]
        + arrays["elastic_source_sum"]
        + arrays["wall_source_sum"]
    )


def assemble_neutral_boltzmann_rhs(
    thermal_speed_m_s,
    coefficient_source_distribution,
    charge_exchange_source_sum,
    collision_frequency_s_inv,
    total_distribution,
    elastic_source_sum,
    wall_source_sum,
):
    """Return ``Vth*(S + Beta_CX - alpha_c*f + OmegaM + Swall)``."""
    try:
        raw_speed = np.asarray(thermal_speed_m_s)
        if raw_speed.ndim != 0 or raw_speed.dtype.kind not in "iuf":
            raise ValueError
        vth = float(raw_speed)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("thermal_speed_m_s must be positive and finite") from exc
    if not np.isfinite(vth) or vth <= 0.0:
        raise ValueError("thermal_speed_m_s must be positive and finite")
    fields = {
        "coefficient_source_distribution": coefficient_source_distribution,
        "charge_exchange_source_sum": charge_exchange_source_sum,
        "collision_frequency_s_inv": collision_frequency_s_inv,
        "total_distribution": total_distribution,
        "elastic_source_sum": elastic_source_sum,
        "wall_source_sum": wall_source_sum,
    }
    arrays = {name: _finite_real_array(value, name) for name, value in fields.items()}
    reference_shape = arrays["total_distribution"].shape
    if len(reference_shape) != 3 or any(array.shape != reference_shape for array in arrays.values()):
        raise ValueError("all RHS fields must be finite three-dimensional arrays with one shape")
    with np.errstate(over="ignore", invalid="ignore"):
        rhs = vth * _assemble_collision_balance(arrays)
    if not np.all(np.isfinite(rhs)):
        raise ValueError("rhs must be finite")
    return {"rhs": rhs}
