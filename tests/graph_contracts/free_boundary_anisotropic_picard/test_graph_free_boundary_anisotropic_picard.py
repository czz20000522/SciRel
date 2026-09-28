from scirel.equilibrium.free_boundary_anisotropic_picard import solve_free_boundary_anisotropic_picard
import scirel
from _review_bindings import load_asset as _load_asset, load_graph as _load_graph, load_operator as _load_operator
from pathlib import Path

import numpy as np
import pytest



def _run(values):
    return solve_free_boundary_anisotropic_picard(values)


# 验证：YAML 的 N6 映射、显式 N4 closure port 和反馈边必须与可调用图同步。
def test_yaml_declares_picard_feedback_contract():
    contract = Path(__file__).with_name("task_graph.yaml").read_text(encoding="utf-8")
    assert "primary_pfm_node: N6" in contract
    assert "pressure_closure" in contract
    assert "scirel.kinetic.graphs.frank_egedal_pressure_closure" not in contract
    assert "to_input: psi_state" in contract


def _pressure_closure(state):
    psi = np.asarray(state["psi"], dtype=float)
    return {
        "p_parallel": 2.0 + psi,
        "p_perp": 1.0 + 0.5 * psi,
        "density": None,
        "electron_temperature": None,
    }


def _isotropic_limit_closure(state):
    psi = np.asarray(state["psi"], dtype=float)
    pressure = np.full_like(psi, 2.0)
    return {
        "p_parallel": pressure,
        "p_perp": pressure.copy(),
        "density": None,
        "electron_temperature": None,
    }


def _inputs(**overrides):
    r_grid, z_grid = np.meshgrid(np.array([0.2, 0.4, 0.6]), np.array([-0.1, 0.0, 0.1]))
    n_points = r_grid.size
    values = {
        "r_grid": r_grid,
        "z_grid": z_grid,
        "psi_vac": r_grid.copy(),
        "br_vac": np.zeros_like(r_grid),
        "bz_vac": np.ones_like(r_grid),
        "g_psi": np.zeros((n_points, n_points)),
        "pressure_closure": _pressure_closure,
        "params": {
            "p0": 1.0,
            "psi_axis": 0.0,
            "psi_edge": 1.0,
            "B0": 1.0,
            "mirror_ratio": 2.0,
            "legendre_degrees": [0.5],
            "source_coefficients": [1.0],
            "velocity_nodes": 4,
            "pitch_nodes": 4,
        },
        "tol": 1.0e-12,
        "maxiter": 1,
        "relax": 0.0,
    }
    values.update(overrides)
    return values


# 验证：零 Green 响应时仍执行一轮真实 pressure-current 状态链，但磁通保持真空值并收敛。
def test_zero_green_performs_one_iteration_without_changing_vacuum_flux():
    values = _inputs()
    result = _run(values)
    assert result["iterations"] == 1
    assert result["converged"]
    assert result["failure_reason"] is None
    np.testing.assert_allclose(result["psi"], values["psi_vac"])
    assert result["picard_current_state"].shape == (9,)
    assert result["profiles"]["p_parallel"].shape == (3, 3)


def test_isotropic_limit_has_zero_anisotropic_source_and_preserves_vacuum():
    values = _inputs(
        pressure_closure=_isotropic_limit_closure,
        g_psi=1.0e-2 * np.eye(9),
    )
    result = _run(values)
    np.testing.assert_allclose(result["profiles"]["p_parallel"], result["profiles"]["p_perp"])
    np.testing.assert_allclose(result["picard_current_state"], 0.0, atol=1.0e-12)
    np.testing.assert_allclose(result["psi"], values["psi_vac"])


# 验证：plasma Green 矩阵不是任意 array；field/source 轴都必须等于 N_Z*N_R。
def test_rejects_non_square_or_wrong_size_green_matrix():
    with pytest.raises(ValueError, match="g_psi must have shape"):
        _run(_inputs(g_psi=np.eye(3)))


# 验证：第 2 步消费第 1 步的真实 psi/current 输出；若没有反馈，psi 不会偏离真空状态。
def test_nonzero_green_requires_sequential_state_feedback():
    values = _inputs(g_psi=1.0e-2 * np.eye(9), maxiter=2, tol=1.0e-30)
    result = _run(values)
    assert result["iterations"] == 2
    assert result["residual_history"].shape == (2,)
    # This fixture reaches its fixed point on the second state handoff; the
    # assertion is about sequential feedback, not an artificial maxiter fail.
    assert result["converged"]
    assert result["failure_reason"] is None
    assert np.any(np.abs(result["picard_current_state"]) > 0.0)
    assert not np.allclose(result["psi"], values["psi_vac"])


# 验证：自洽 BR/BZ Green 响应是成对合同，单独提供一个会改变 B 的物理含义，必须拒绝。
def test_iteration_bound_returns_last_state_without_convergence():
    result = _run(_inputs(g_psi=1.0e-2 * np.eye(9), maxiter=1, tol=1.0e-30))
    assert result["iterations"] == 1
    assert not result["converged"]
    assert result["failure_reason"] == "maxiter_reached"
    assert result["residual"] == result["residual_history"][0] > 0.0
    np.testing.assert_allclose(result["profiles"]["p_parallel"], 2.0 + result["psi"])


def test_rejects_unpaired_magnetic_field_green_matrices():
    with pytest.raises(ValueError, match="g_br and g_bz must be provided together"):
        _run(_inputs(g_br=np.eye(9)))


# 验证：理想墙资产只修正 psi；即使墙分支开启，未提供 g_br/g_bz 时 BR/BZ 仍为真空场。
def test_boundary_branch_corrects_flux_only_and_keeps_vacuum_poloidal_field():
    values = _inputs(
        g_psi=np.eye(9),
        boundary_correction={
            "boundary_sample_matrix": np.eye(9),
            "green_boundary_to_boundary": np.eye(9),
            "green_boundary_to_field": np.eye(9),
        },
    )
    result = _run(values)
    np.testing.assert_allclose(result["psi"], 0.0)
    np.testing.assert_allclose(result["BR"], values["br_vac"])
    np.testing.assert_allclose(result["BZ"], values["bz_vac"])
    assert result["boundary_currents"].shape == (9,)


def test_requires_explicit_n4_pressure_closure_port():
    values = _inputs()
    values.pop("pressure_closure")
    with pytest.raises(ValueError, match="pressure_closure"):
        _run(values)


def test_requires_all_yaml_required_picard_controls():
    for name in ("params", "tol", "maxiter", "relax"):
        values = _inputs()
        values.pop(name)
        with pytest.raises(ValueError, match=f"{name} is required"):
            _run(values)


def test_zero_step_returns_declared_zero_feedback_state():
    result = _run(_inputs(maxiter=0))
    assert result["failure_reason"] == "maxiter_reached"
    assert result["iterations"] == 0
    assert np.isinf(result["residual"])
    assert result["residual_history"].size == 0
    np.testing.assert_allclose(result["picard_current_state"], 0.0)


def test_current_grid_validation_precedes_required_port_validation():
    values = _inputs(r_grid=np.ones((2, 2)))
    values.pop("pressure_closure")
    with pytest.raises(ValueError, match="equal-shape 2-D grids"):
        _run(values)


def test_review_gate_rejects_invalid_closure_fields_and_mask_shape():
    values = _inputs()

    def invalid_closure(state):
        shape = np.asarray(state["psi"]).shape
        return {
            "p_parallel": np.ones(shape),
            "p_perp": np.ones(shape),
            "density": -np.ones(shape),
            "electron_temperature": np.full(shape, np.nan),
        }

    with pytest.raises(ValueError, match="density.*finite nonnegative"):
        _run({**values, "pressure_closure": invalid_closure})

    values = _inputs()
    with pytest.raises(ValueError, match="plasma_mask.*same shape"):
        _run({**values, "plasma_mask": np.ones((2, 2), dtype=bool)})


def test_review_gate_terminal_outputs_share_the_returned_state():
    values = _inputs()
    result = _run(values)
    cell_area = (values["r_grid"][0, 1] - values["r_grid"][0, 0]) * (values["z_grid"][1, 0] - values["z_grid"][0, 0])
    np.testing.assert_allclose(result["plasma_currents"], result["j_phi"] * abs(cell_area))
    np.testing.assert_allclose(result["profiles"]["p_parallel"], 2.0 + result["psi"])


def test_review_gate_rejects_nonuniform_rz_axes_before_iteration():
    r_grid, z_grid = np.meshgrid(np.array([0.2, 0.4, 0.7]), np.array([-0.1, 0.0, 0.1]))
    with pytest.raises(ValueError, match="uniformly spaced"):
        _run(_inputs(r_grid=r_grid, z_grid=z_grid))


def test_review_gate_rejects_fractional_picard_iteration_count():
    with pytest.raises(ValueError, match="maxiter must be an integer"):
        _run(_inputs(maxiter=1.2))
