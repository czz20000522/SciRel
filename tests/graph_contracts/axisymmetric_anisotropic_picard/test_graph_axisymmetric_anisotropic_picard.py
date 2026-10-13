from scirel.equilibrium.axisymmetric_anisotropic_picard import solve_axisymmetric_anisotropic_picard
import scirel
from _review_bindings import load_asset as _load_asset, load_graph as _load_graph, load_operator as _load_operator
from pathlib import Path

import numpy as np
import pytest



def _run(values):
    return solve_axisymmetric_anisotropic_picard(values)


def _closure(b, psi):
    return {"p_parallel": 1.0 + 0.1 * psi, "p_perpendicular": 1.0 + 0.2 * psi, "closure_marker": float(np.mean(b))}


def _scalar_closure(b, psi):
    return {"p_parallel": 7.0, "p_perpendicular": 5.0, "closure_marker": float(np.mean(b))}


def _inputs(**overrides):
    r_grid, z_grid = np.meshgrid(np.linspace(0.0, 0.4, 5), np.linspace(-0.3, 0.3, 5))
    values = {"r_grid": r_grid, "z_grid": z_grid, "psi_vac": 0.5 * r_grid**2, "g_psi": 1.0e-3 * np.eye(r_grid.size), "pressure_closure": _closure, "maxiter": 2, "tol": 1.0e-30, "relax": 0.2, "strict_compatibility": False}
    values.update(overrides)
    return values


def test_yaml_declares_current_n6_source_order_and_leaf_assets():
    contract = Path(__file__).with_name("task_graph.yaml").read_text(encoding="utf-8")
    assert "primary_pfm_node: N6" in contract
    assert "compute_anisotropic_force_balance" in contract
    assert "update_axisymmetric_picard_flux" in contract
    assert "declared-order relative psi change" in contract


def test_feedback_rederives_final_field_and_reevaluates_closure_at_returned_psi():
    values = _inputs()
    result = _run(values)
    field = _load_asset("scirel.field.poloidal_field_from_flux")(values["r_grid"], values["z_grid"], result["psi"])
    np.testing.assert_allclose(result["B_R"], field["B_R"])
    np.testing.assert_allclose(result["B_Z"], field["B_Z"])
    np.testing.assert_allclose(result["p_parallel"], 1.0 + 0.1 * result["psi"])
    assert result["iterations"] == 2
    assert len(result["iteration_history"]) == 2


def test_dynamic_mask_is_applied_before_green_feedback():
    values = _inputs(plasma_mask=lambda b, psi: np.zeros_like(psi, dtype=bool), maxiter=1)
    result = _run(values)
    np.testing.assert_allclose(result["J_phi"], 0.0)
    np.testing.assert_allclose(result["psi"], values["psi_vac"])
    assert result["converged"]


def test_scalar_pressure_broadcast_preserves_pa_value():
    result = _run(_inputs(pressure_closure=_scalar_closure, maxiter=1))
    np.testing.assert_array_equal(result["p_parallel"], np.full_like(result["psi"], 7.0))
    np.testing.assert_array_equal(result["p_perpendicular"], np.full_like(result["psi"], 5.0))


def test_non_grid_pressure_shape_fails_closed():
    def bad_closure(b, psi):
        return {"p_parallel": np.ones((2, 2)), "p_perpendicular": 5.0}

    with pytest.raises(ValueError, match="pressure fields"):
        _run(_inputs(pressure_closure=bad_closure, maxiter=1))


def test_missing_closure_and_invalid_relax_fail_closed():
    values = _inputs()
    values.pop("pressure_closure")
    with pytest.raises(ValueError, match="pressure_closure"):
        _run(values)
    with pytest.raises(ValueError, match="Picard controls"):
        _run(_inputs(relax=1.0))

def test_review_gate_uniform_bz_linear_isotropic_pressure_has_analytic_current():
    r_grid, z_grid = np.meshgrid(np.linspace(0.2, 0.6, 5), np.linspace(-0.2, 0.2, 5))

    def linear_isotropic_pressure(_b, _psi):
        pressure = 3.0 + r_grid
        return {"p_parallel": pressure, "p_perpendicular": pressure}

    result = _run({
        "r_grid": r_grid,
        "z_grid": z_grid,
        "psi_vac": r_grid**2,
        "g_psi": np.zeros((r_grid.size, r_grid.size)),
        "pressure_closure": linear_isotropic_pressure,
        "maxiter": 1,
        "tol": 1.0e-12,
        "relax": 0.0,
        "strict_compatibility": True,
    })
    np.testing.assert_allclose(result["B_Z"], 2.0, rtol=0.0, atol=2.0e-14)
    np.testing.assert_allclose(result["J_phi"], 0.5, rtol=2.0e-13, atol=2.0e-13)
    # Constant J=.5 integrates over the declared rectangle [.2,.6]x[-.2,.2].
    weights = np.outer([.05, .1, .1, .1, .05], [.05, .1, .1, .1, .05])
    np.testing.assert_allclose(result["plasma_cell_currents"], .5 * weights)
    np.testing.assert_allclose(np.sum(result["plasma_cell_currents"]), .08)


def test_review_gate_firehose_and_parallel_compatibility_fail_closed():
    r_grid, z_grid = np.meshgrid(np.linspace(0.2, 0.6, 5), np.linspace(-0.2, 0.2, 5))
    base = {
        "r_grid": r_grid,
        "z_grid": z_grid,
        "psi_vac": r_grid**2,
        "g_psi": np.zeros((r_grid.size, r_grid.size)),
        "maxiter": 1,
        "tol": 1.0e-12,
        "relax": 0.0,
    }
    with pytest.raises(FloatingPointError, match="firehose"):
        _run({**base, "pressure_closure": lambda _b, _psi: {"p_parallel": 1.0e8, "p_perpendicular": 1.0}})
    with pytest.raises(ValueError, match="unbalanced parallel"):
        _run({
            **base,
            "pressure_closure": lambda _b, _psi: {
                "p_parallel": 3.0 + z_grid,
                "p_perpendicular": 3.0 + z_grid,
            },
            "minimum_firehose_margin": -1.0,
            "compatibility_tol": 0.0,
            "strict_compatibility": True,
        })


def test_review_gate_rechecks_minimum_field_after_terminal_update():
    from scirel.equilibrium import axisymmetric_anisotropic_picard as graph

    calls = {"field": 0, "closure": 0}

    def closure(b, psi):
        calls["closure"] += 1
        return _closure(b, psi)

    def loader(reference):
        asset = _load_asset(reference)
        if reference != "scirel.field.poloidal_field_from_flux":
            return asset

        def field(*args, **kwargs):
            result = asset(*args, **kwargs)
            calls["field"] += 1
            if calls["field"] >= 2:
                result = dict(result)
                result["B"] = np.zeros_like(result["B"])
            return result

        return field

    with pytest.raises(FloatingPointError, match="returned terminal state"):
        graph.run_graph(_inputs(maxiter=1, minimum_field=1.0e-6, pressure_closure=closure), asset_loader=loader)
    assert calls["field"] >= 2
    assert calls["closure"] == 2


def test_review_gate_rejects_nonfinite_and_coerced_control_values():
    with pytest.raises(ValueError, match="tol must be a finite scalar"):
        _run(_inputs(tol=np.nan))
    with pytest.raises(ValueError, match="maxiter must be an integer"):
        _run(_inputs(maxiter=1.2))
    with pytest.raises(ValueError, match="strict_compatibility must be a boolean"):
        _run(_inputs(strict_compatibility=0))
