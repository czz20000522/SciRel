import numpy as np

from scirel.equilibrium.kinetic_mirror_hall_equilibrium import (
    solve_kinetic_mirror_hall_equilibrium,
)
from scirel.inference.anisotropic_trial_evaluation import evaluate_anisotropic_trial


def test_anisotropic_trial_uses_caller_owned_ports_and_penalizes_failures():
    config = {"r_grid": np.zeros((1, 1)), "z_grid": np.zeros((1, 1))}
    result = evaluate_anisotropic_trial(
        params={"p0": 2.0},
        observations={"x": 1},
        solver_config=config,
        equilibrium_solver=lambda _: {"converged": True, "failure_reason": None},
        diagnostic_evaluator=lambda _: {"x": [3.0]},
        residual_reducer=lambda **_: {"residual_vector": [2.0], "chi2": 4.0},
    )
    assert result["chi2"] == 4.0
    assert result["failure_reason"] is None

    failed = evaluate_anisotropic_trial(
        params={},
        observations={},
        solver_config=config,
        equilibrium_solver=lambda _: (_ for _ in ()).throw(ValueError("bad port")),
        diagnostic_evaluator=lambda _: None,
        residual_reducer=lambda **_: None,
    )
    np.testing.assert_allclose(failed["residuals"], [1.0e12])
    assert failed["chi2"] == 1.0e24


def test_kinetic_mirror_hall_graph_binds_nested_graphs_through_pressure_closure():
    calls = []

    def kinetic_graph(inputs):
        calls.append(("kinetic", inputs["b_t"], inputs["psi"]))
        return {"p_parallel": np.array([[2.0]]), "p_perpendicular": np.array([[3.0]])}

    def hall_graph(inputs):
        calls.append(("hall", inputs["psi_vac"]))
        closure = inputs["pressure_closure"](np.array([[1.5]]), np.array([[0.25]]))
        return {"converged": True, "closure_state": closure}

    result = solve_kinetic_mirror_hall_equilibrium(
        {
            "r_grid": np.array([[0.1]]),
            "z_grid": np.array([[0.0]]),
            "psi_vac": np.array([[0.2]]),
            "g_psi": np.zeros((1, 1)),
            "ion_mass_kg": 1.0,
            "ion_charge_c": 1.0,
            "kinetic_config": {"density_ref_m3": 1.0},
        },
        kinetic_graph=kinetic_graph,
        hall_graph=hall_graph,
    )

    assert result["converged"]
    assert result["closure_state"]["p_parallel"][0, 0] == 2.0
    assert [item[0] for item in calls] == ["hall", "kinetic"]
