import numpy as np

from scirel._framework_compositions.kinetic_mirror_hall_equilibrium import (
    compose_kinetic_mirror_hall_equilibrium,
)
from scirel.equilibrium.kinetic_mirror_hall_equilibrium import (
    solve_kinetic_mirror_hall_equilibrium,
)


def test_composition_passes_current_state_into_kinetic_closure():
    seen = {}

    def kinetic_graph(payload):
        seen["kinetic"] = payload
        return {"p_parallel": payload["b_t"], "p_perpendicular": payload["psi"]}

    def hall_graph(payload):
        closure = payload["pressure_closure"]
        b_t = np.full((1, 2), 2.0)
        psi = np.full((1, 2), 3.0)
        return {"closure_state": closure(b_t, psi), "hall_keys": sorted(payload)}

    r_grid = np.array([[0.2, 0.4]])
    z_grid = np.array([[-0.1, -0.1]])
    result = compose_kinetic_mirror_hall_equilibrium(
        {
            "r_grid": r_grid,
            "z_grid": z_grid,
            "psi_vac": r_grid,
            "g_psi": np.zeros((2, 2)),
            "ion_mass_kg": 1.0,
            "ion_charge_c": 1.0,
            "kinetic_config": {"mass_kg": 1.0, "charge_c": 1.0},
        },
        kinetic_graph=kinetic_graph,
        hall_graph=hall_graph,
    )

    assert np.all(seen["kinetic"]["b_t"] == 2.0)
    assert np.all(seen["kinetic"]["psi"] == 3.0)
    assert result["closure_state"]["p_parallel"].shape == (1, 2)


def test_composition_rejects_missing_state():
    try:
        compose_kinetic_mirror_hall_equilibrium({})
    except ValueError as exc:
        assert "missing required composition inputs" in str(exc)
    else:
        raise AssertionError("missing state was accepted")


def test_public_graph_passes_current_field_to_bound_kinetic_closure():
    observed = {}

    def kinetic_graph(payload):
        observed["kinetic"] = payload
        return {"p_parallel": payload["b_t"], "p_perpendicular": payload["psi"]}

    def hall_graph(payload):
        observed["hall"] = payload
        return payload["pressure_closure"](
            np.full((1, 2), 2.0), np.full((1, 2), 3.0)
        )

    inputs = {
        "r_grid": np.array([[0.2, 0.4]]),
        "z_grid": np.array([[-0.1, -0.1]]),
        "psi_vac": np.array([[0.0, 0.1]]),
        "g_psi": np.zeros((2, 2)),
        "ion_mass_kg": 1.0,
        "ion_charge_c": 1.0,
        "kinetic_config": {"density_ref_m3": 1e18},
    }
    result = solve_kinetic_mirror_hall_equilibrium(
        inputs, kinetic_graph=kinetic_graph, hall_graph=hall_graph
    )

    assert "kinetic_config" not in observed["hall"]
    assert observed["kinetic"]["density_ref_m3"] == 1e18
    assert observed["kinetic"]["r_grid"] is inputs["r_grid"]
    np.testing.assert_array_equal(result["p_parallel"], [[2.0, 2.0]])
    np.testing.assert_array_equal(result["p_perpendicular"], [[3.0, 3.0]])
