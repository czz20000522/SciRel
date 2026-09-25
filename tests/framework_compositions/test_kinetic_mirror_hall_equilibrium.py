import numpy as np

from scirel._framework_compositions.kinetic_mirror_hall_equilibrium import (
    compose_kinetic_mirror_hall_equilibrium,
)
from scirel.equilibrium.kinetic_mirror_hall_equilibrium import (
    solve_kinetic_mirror_hall_equilibrium,
)
from scirel.field.circular_filament_green import circular_filament_green_response
from scirel.field.mirror_plasma_green import build_mirror_plasma_flux_green
from scirel.field.poloidal_field_from_flux import poloidal_field_from_flux


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


def test_real_nested_graphs_close_a_manufactured_radial_profile_with_feedback():
    charge_c = 1.602176634e-19
    mass_kg = 1.67262192595e-27
    r_grid, z_grid = np.meshgrid(
        np.linspace(0.0, 0.4, 7), np.linspace(-1.0, 1.0, 7)
    )
    vacuum_flux = 0.5 * r_grid**2
    np.testing.assert_allclose(
        poloidal_field_from_flux(r_grid, z_grid, vacuum_flux)["B_Z"][:, 1:-1],
        1.0,
        rtol=1e-14,
    )
    kinetic_config = {
        "mass_kg": mass_kg,
        "charge_c": charge_c,
        "density_ref_m3": lambda psi: 1e18 * (1.0 - 0.2 * psi / vacuum_flux.max()),
        "temperature_parallel_j": 1000.0 * charge_c,
        "temperature_perpendicular_ref_j": 2000.0 * charge_c,
        "electron_temperature_j": 500.0 * charge_c,
        "reference_z": 0.0,
        "plug_left_z": -1.0,
        "plug_right_z": 1.0,
        "loss_cone_refill": 0.05,
        "quadrature_order": 24,
        "plug_potential_mode": "prescribed",
    }
    result = solve_kinetic_mirror_hall_equilibrium(
        {
            "r_grid": r_grid,
            "z_grid": z_grid,
            "psi_vac": vacuum_flux,
            "g_psi": np.eye(r_grid.size) * 1e-8,
            "ion_mass_kg": mass_kg,
            "ion_charge_c": charge_c,
            "kinetic_config": kinetic_config,
            "maxiter": 25,
            "tol": 1e-12,
        }
    )

    assert result["converged"] and 1 < result["iterations"] <= 25
    assert result["compatibility_messages"] == []
    assert np.max(np.abs(result["psi"] - vacuum_flux)) > 1e-9
    assert np.max(np.abs(result["J_phi"][:, 1:])) > 1.0
    assert np.all(np.diff(result["p_parallel"], axis=1) < 0.0)
    assert np.max(np.abs(result["closure_state"]["relative_charge_residual"])) < 1e-9
    np.testing.assert_array_equal(result["p_parallel"], result["closure_state"]["p_parallel"])


def test_real_nested_hall_graphs_with_filament_vacuum_and_mirror_green():
    charge_c = 1.602176634e-19
    mass_kg = 1.67262192595e-27
    r_grid, z_grid = np.meshgrid(
        np.linspace(0.0, 0.4, 17), np.linspace(-1.0, 1.0, 17)
    )
    points = np.column_stack((r_grid.ravel(), z_grid.ravel()))
    vacuum_sources = [[0.7, -1.3, 1e6], [0.7, 1.3, 1e6]]
    vacuum_flux = circular_filament_green_response(vacuum_sources, points)["gpsi"].reshape(r_grid.shape)
    green = build_mirror_plasma_flux_green(r_grid, z_grid)["g_psi"]
    source_index = (8, 12)
    active = np.zeros_like(r_grid, dtype=bool)
    active[source_index] = True

    inputs = {
        "r_grid": r_grid,
        "z_grid": z_grid,
        "psi_vac": vacuum_flux,
        "g_psi": green,
        "ion_mass_kg": mass_kg,
        "ion_charge_c": charge_c,
        "kinetic_config": {
            "mass_kg": mass_kg,
            "charge_c": charge_c,
            "density_ref_m3": lambda psi: 1e18 * (1.0 - 0.2 * psi / vacuum_flux.max()),
            "temperature_parallel_j": 1000.0 * charge_c,
            "temperature_perpendicular_ref_j": 2000.0 * charge_c,
            "electron_temperature_j": 500.0 * charge_c,
            "reference_z": 0.0,
            "plug_left_z": -1.0,
            "plug_right_z": 1.0,
            "loss_cone_refill": 0.05,
            "quadrature_order": 24,
            "plug_potential_mode": "prescribed",
        },
        "plasma_mask": active,
        "maxiter": 8,
        "tol": 1e-10,
        "relax": 0.0,
    }
    result = solve_kinetic_mirror_hall_equilibrium(inputs)
    without_hall = solve_kinetic_mirror_hall_equilibrium(
        {**inputs, "hall_multiplier": 0.0}
    )

    assert result["converged"] and 1 < result["iterations"] <= 8
    assert result["compatibility_messages"] == []
    assert without_hall["compatibility_messages"] == []
    assert abs(result["hall_state"]["hall_electric_field_R"][source_index]) > 1.0
    np.testing.assert_allclose(
        without_hall["hall_state"]["hall_electric_field_R"][source_index],
        0.0,
        atol=1e-9,
    )
    assert abs(result["J_phi"][source_index]) > 1.0
    cell_current = result["plasma_cell_currents"][source_index]
    assert abs(cell_current) > 1e-3
    target_index = (12, 4)
    target = points[np.ravel_multi_index(target_index, r_grid.shape)]
    plasma_source = [r_grid[source_index], z_grid[source_index], cell_current]
    direct = circular_filament_green_response([*vacuum_sources, plasma_source], [target])
    plasma_flux = circular_filament_green_response([plasma_source], [target])["gpsi"][0]
    np.testing.assert_allclose(
        result["psi"][target_index] - vacuum_flux[target_index],
        plasma_flux,
        rtol=1e-7,
        atol=1e-15,
    )
    np.testing.assert_allclose(result["B_R"][target_index], direct["gBR"][0], rtol=0.02)
    np.testing.assert_allclose(result["B_Z"][target_index], direct["gBZ"][0], rtol=0.02)
    assert np.max(np.abs(result["closure_state"]["relative_charge_residual"])) < 1e-9
