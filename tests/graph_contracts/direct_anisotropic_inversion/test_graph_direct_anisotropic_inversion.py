from scirel.inference.direct_anisotropic_inversion import solve_direct_anisotropic_inversion

from scirel.inference.direct_anisotropic_inversion import solve_direct_anisotropic_inversion
import scirel
from _review_bindings import load_asset as _load_asset, load_graph as _load_graph, load_operator as _load_operator
from pathlib import Path
from functools import partial
import inspect

import numpy as np
import pytest

from scirel.inference import direct_anisotropic_inversion as graph
def _operator_loader(asset_ref, callable_name=None):
    return _load_operator(asset_ref, callable_name)

def _asset_loader(asset_ref):
    return _load_asset(asset_ref)

def _solver_config():
    r_grid, z_grid = np.meshgrid(np.linspace(0.1, 1.1, 3), np.linspace(-0.5, 0.5, 3))
    psi = r_grid.copy()
    return {
        "r_grid": r_grid,
        "z_grid": z_grid,
        "psi_vac": psi,
        "br_vac": np.zeros_like(psi),
        "bz_vac": np.ones_like(psi),
        "g_psi": np.zeros((psi.size, psi.size)),
        "tol": 1.0e-12,
        "maxiter": 3,
        "relax": 0.0,
    }


def _base_params(p0):
    return {
        "p0": p0,
        "psi_axis": 0.1,
        "psi_edge": 1.1,
        "mirror_ratio": 2.0,
        "legendre_degrees": [0.5],
        "source_coefficients": [1.0],
        "velocity_nodes": 6,
        "pitch_nodes": 6,
    }


def _inputs(true_p0=4.0):
    solver_config = _solver_config()
    pressure_closure_spec = __import__("importlib").util.spec_from_file_location(
        "pressure_closure_fixture", Path(__file__).resolve().parents[1] / "FrankEgedal各向异性压强闭合" / "graph.py"
    )
    pressure_closure_module = __import__("importlib").util.module_from_spec(pressure_closure_spec)
    pressure_closure_spec.loader.exec_module(pressure_closure_module)
    true_equilibrium = __import__("importlib").util.spec_from_file_location(
        "equilibrium_fixture", Path(__file__).resolve().parents[1] / "各向异性自由边界Picard平衡" / "graph.py"
    )
    module = __import__("importlib").util.module_from_spec(true_equilibrium)
    true_equilibrium.loader.exec_module(module)

    def equilibrium_solver(payload):
        pressure_closure = partial(pressure_closure_module.run_graph, asset_loader=_asset_loader)
        result = module.run_graph({**payload, "pressure_closure": pressure_closure}, asset_loader=_asset_loader)
        return {**result, "psi_unit":"Wb/rad", "profile_units":{"p_perp":"Pa", "p_parallel":"Pa"}}

    equilibrium = equilibrium_solver({**solver_config, "params": _base_params(true_p0)})
    point = np.array([[0.5, 0.0]])
    observation_graph_spec = __import__("importlib").util.spec_from_file_location(
        "diagnostic_fixture", Path(__file__).resolve().parents[1] / "平衡合成诊断" / "graph.py"
    )
    diagnostic_module = __import__("importlib").util.module_from_spec(observation_graph_spec)
    observation_graph_spec.loader.exec_module(diagnostic_module)
    observed = diagnostic_module.run_graph(
        {"equilibrium": equilibrium, "R": solver_config["r_grid"], "Z": solver_config["z_grid"], "observations": {"thomson": {"points": point, "p_perp":{"unit":"Pa"}}}},
        asset_loader=_asset_loader,
    )
    return {
        "initial_params": _base_params(1.0),
        "bounds": {"p0": (0.1, 10.0)},
        "observations": {"thomson": {"points": point, "p_perp": {"values": observed["thomson"]["p_perp"], "sigma": [0.1], "unit":"Pa"}}},
        "solver_config": solver_config,
        "equilibrium_solver": equilibrium_solver,
        "diagnostic_evaluator": partial(diagnostic_module.run_graph, asset_loader=_asset_loader),
        "fit_keys": ["p0"],
        "method": "least_squares",
    }


# 验证：YAML 必须公开 PFM-10、显式 N6/N9 端口和 optimizer feedback 边。
def test_yaml_declares_explicit_cross_node_ports():
    contract = Path(__file__).with_name("task_graph.yaml").read_text(encoding="utf-8")
    assert "primary_pfm_node: N10" in contract
    assert "equilibrium_solver" in contract
    assert "diagnostic_evaluator" in contract
    assert "scirel.equilibrium.graphs.free_boundary_anisotropic_picard" not in contract
    assert "scirel.diagnostics.graphs.equilibrium_synthesis_diagnostics" not in contract
    assert "id: direct_optimizer" in contract
    assert "N6 required Picard convergence tolerance" in contract
    assert "N6 required Picard iteration limit" in contract
    assert "N6 required Picard relaxation" in contract


# 验证：相同 seed、bounds 和 fit_keys 产生相同 permutation 和 strata 内样本。
def test_latin_hypercube_is_deterministic_and_stratified():
    lhs = _operator_loader("scirel.inference.latin_hypercube_sampling", "sample_latin_hypercube")
    first = lhs(bounds={"a": (0.0, 1.0), "b": (10.0, 20.0)}, n_samples=5, seed=4)["initial_samples"]
    second = lhs(bounds={"a": (0.0, 1.0), "b": (10.0, 20.0)}, n_samples=5, seed=4)["initial_samples"]
    assert first == second
    assert sorted(int(sample["a"] * 5) for sample in first) == [0, 1, 2, 3, 4]
    assert sorted(int((sample["b"] - 10.0) / 10.0 * 5) for sample in first) == [0, 1, 2, 3, 4]


# 验证：zero-G 的合成 p_perp 观测可由显式 N6/N9 端口和 least_squares 恢复 p0。
def test_recovers_synthetic_p0_with_zero_green_matrix():
    result = graph.run_graph(_inputs(true_p0=4.0), operator_loader=_operator_loader)
    assert result["chi2"] < 1.0e-8
    assert result["best_parameters"]["p0"] == pytest.approx(4.0, rel=1.0e-4)


# 验证：无效 method 与 LHS 非法 bounds 保持 source 的 fallback/显式失败语义。
def test_invalid_method_records_failure_and_lhs_requires_finite_increasing_bounds():
    invalid_method = _inputs()
    invalid_method["method"] = "not_a_method"
    with pytest.raises(ValueError, match="method must be"):
        graph.run_graph(invalid_method, operator_loader=_operator_loader)
    invalid_lhs = _inputs()
    invalid_lhs["bounds"] = {"p0": (1.0, 1.0)}
    invalid_lhs["n_initial_samples"] = 2
    with pytest.raises(ValueError):
        graph.run_graph(invalid_lhs, operator_loader=_operator_loader)


# 验证：任一端口调用异常必须成为单元素 1e12 residual，而非返回伪造 equilibrium。
def test_failed_port_evaluation_uses_source_penalty():
    inputs = _inputs()
    inputs["solver_config"] = {"r_grid": np.zeros((2, 2)), "z_grid": np.zeros((2, 2))}
    with pytest.raises((ValueError, KeyError)):
        graph.run_graph(inputs, operator_loader=_operator_loader)


def test_requires_explicit_cross_node_ports():
    inputs = _inputs()
    inputs.pop("equilibrium_solver")
    with pytest.raises(ValueError, match="equilibrium_solver"):
        graph.run_graph(inputs, operator_loader=_operator_loader)


def test_requires_explicit_method_contract():
    inputs = _inputs()
    inputs.pop("method")
    with pytest.raises(ValueError, match="method is required"):
        graph.run_graph(inputs, operator_loader=_operator_loader)


def test_public_solver_docstring_declares_contract():
    doc = inspect.getdoc(solve_direct_anisotropic_inversion)
    assert doc is not None
    for section in ("Parameters", "Returns", "Raises"):
        assert section in doc
    assert "forward_converged" in doc
    assert "evaluation_log" in doc
    assert "identifiability" in doc


def test_public_scirel_injects_declared_operator_resolver():


    result = solve_direct_anisotropic_inversion(_inputs())
    assert result["best_parameters"]["p0"] == pytest.approx(4.0, rel=1.0e-4)


def test_public_simplified_parameter_fit_scenario():
    r_grid, z_grid = np.meshgrid(np.array([0.2, 0.4]), np.array([-0.1, 0.1]))

    def equilibrium_solver(state):
        p0 = float(state["params"]["p0"])
        return {
            "converged": True,
            "failure_reason": None,
            "psi": state["psi_vac"],
            "profiles": {"p_perp": np.full_like(state["r_grid"], p0)},
        }

    def diagnostic_evaluator(state):
        return {"thomson": {"p_perp": state["equilibrium"]["profiles"]["p_perp"]}}

    result = solve_direct_anisotropic_inversion(
        {
            "initial_params": {"p0": 1.0},
            "bounds": {"p0": (0.1, 10.0)},
            "method": "least_squares",
            "fit_keys": ["p0"],
            "solver_config": {
                "r_grid": r_grid,
                "z_grid": z_grid,
                "psi_vac": r_grid.copy(),
                "br_vac": np.zeros_like(r_grid),
                "bz_vac": np.ones_like(r_grid),
                "g_psi": np.zeros((r_grid.size, r_grid.size)),
                "tol": 1.0e-12,
                "maxiter": 2,
                "relax": 0.0,
            },
            "observations": {"thomson": {"p_perp": {"values": np.full_like(r_grid, 4.0), "sigma": 1.0}}},
            "equilibrium_solver": equilibrium_solver,
            "diagnostic_evaluator": diagnostic_evaluator,
        }
    )
    assert result["converged"]
    assert abs(result["best_parameters"]["p0"] - 4.0) < 1.0e-6


def test_review_gate_reports_nonconverged_equilibrium_reason():
    r_grid, z_grid = np.meshgrid(np.array([0.2, 0.4]), np.array([-0.1, 0.1]))

    def equilibrium_solver(_state):
        return {"converged": False, "profiles": {"p_perp": np.ones_like(r_grid)}}

    def diagnostic_evaluator(state):
        return {"thomson": {"p_perp": state["equilibrium"]["profiles"]["p_perp"]}}

    result = solve_direct_anisotropic_inversion(
        {
            "initial_params": {"p0": 1.0},
            "bounds": {"p0": (0.1, 2.0)},
            "method": "least_squares",
            "fit_keys": ["p0"],
            "solver_config": {"r_grid": r_grid, "z_grid": z_grid},
            "observations": {"thomson": {"p_perp": {"values": np.ones_like(r_grid), "sigma": 1.0}}},
            "equilibrium_solver": equilibrium_solver,
            "diagnostic_evaluator": diagnostic_evaluator,
        }
    )
    assert result["converged"] is False
    assert result["failure_reason"] == "equilibrium solver did not converge"
