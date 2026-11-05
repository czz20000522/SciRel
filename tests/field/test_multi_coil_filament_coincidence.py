"""Reject singular coincidences before multi-coil Green evaluation."""

import numpy as np
import pytest

from scirel.field import solve_multi_coil_vacuum_field


def _coincident_inputs(*, weight=1.0):
    r_grid, z_grid = np.meshgrid([0.45, 0.5], [0.0, 0.5])
    return {
        "r_grid": r_grid,
        "z_grid": z_grid,
        "rectangular_coils": [
            {
                "r0_m": 0.45,
                "z0_m": 0.0,
                "nr": 1,
                "nz": 1,
                "dr_m": 0.04,
                "dz_m": 0.05,
                "current_a": 1000.0,
                "weights": np.array([weight]),
            }
        ],
    }


def test_active_filament_coincident_with_target_node_fails_closed():
    with pytest.raises(ValueError, match="coincident"):
        solve_multi_coil_vacuum_field(_coincident_inputs())


def test_zero_weight_filament_coincidence_is_inactive():
    result = solve_multi_coil_vacuum_field(_coincident_inputs(weight=0.0))

    np.testing.assert_array_equal(result["psi_vac"], 0.0)
    np.testing.assert_array_equal(result["b_r_vac"], 0.0)
    np.testing.assert_array_equal(result["b_z_vac"], 0.0)
