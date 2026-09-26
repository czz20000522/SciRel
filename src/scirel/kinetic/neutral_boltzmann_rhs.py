"""Assemble the explicit neutral Boltzmann RHS state used by KN1DPy diagnostics."""
from __future__ import annotations

import numpy as np


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
    vth = float(thermal_speed_m_s)
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
    arrays = {name: np.asarray(value, dtype=float) for name, value in fields.items()}
    reference_shape = arrays["total_distribution"].shape
    if len(reference_shape) != 3 or any(array.shape != reference_shape for array in arrays.values()):
        raise ValueError("all RHS fields must be finite three-dimensional arrays with one shape")
    if any(not np.all(np.isfinite(array)) for array in arrays.values()):
        raise ValueError("all RHS fields must be finite")
    return {
        "rhs": vth
        * (
            arrays["coefficient_source_distribution"]
            + arrays["charge_exchange_source_sum"]
            - arrays["collision_frequency_s_inv"] * arrays["total_distribution"]
            + arrays["elastic_source_sum"]
            + arrays["wall_source_sum"]
        )
    }


