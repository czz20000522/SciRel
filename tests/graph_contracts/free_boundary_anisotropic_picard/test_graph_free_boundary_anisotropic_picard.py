from scirel.equilibrium.free_boundary_anisotropic_picard import solve_free_boundary_anisotropic_picard
import scirel
from _review_bindings import load_asset as _load_asset, load_graph as _load_graph, load_operator as _load_operator
from pathlib import Path

import numpy as np
import pytest

from scirel.field.circular_filament_green import circular_filament_green_response
from scirel.field.dense_axisymmetric_green import dense_axisymmetric_green_response
from scirel.kinetic.frank_egedal_pressure_closure import solve_frank_egedal_pressure_closure



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


def test_per_radian_filament_green_pair_feeds_graph_without_wall_correction():
    r_grid, z_grid = np.meshgrid(np.linspace(0.1, 0.5, 7), np.linspace(-0.2, 0.2, 7))
    points = np.column_stack((r_grid.ravel(), z_grid.ravel()))
    sources = np.column_stack((points, np.ones(points.shape[0])))
    green = dense_axisymmetric_green_response(points, sources)
    vacuum_source = [0.7, 0.0, 1e6]
    vacuum = circular_filament_green_response([vacuum_source], points)
    active = np.zeros_like(r_grid, dtype=bool)
    source_index = (3, 4)
    active[source_index] = True

    def pressure_closure(state):
        pressure = 10.0 + 100.0 * state['psi']
        return {'p_parallel': pressure, 'p_perp': pressure,
                'density': None, 'electron_temperature': None}

    result = _run({
        'r_grid': r_grid, 'z_grid': z_grid,
        'psi_vac': vacuum['gpsi'].reshape(r_grid.shape),
        'br_vac': vacuum['gBR'].reshape(r_grid.shape),
        'bz_vac': vacuum['gBZ'].reshape(r_grid.shape),
        'g_psi': green['gpsi'], 'g_br': green['gBR'], 'g_bz': green['gBZ'],
        'plasma_mask': active, 'pressure_closure': pressure_closure,
        'params': {}, 'tol': 1e-12, 'maxiter': 1, 'relax': 0.0,
    })

    cell_current = result['picard_current_state'][np.ravel_multi_index(source_index, r_grid.shape)]
    assert abs(cell_current) > 1e-3
    target_index = (5, 1)
    target = points[np.ravel_multi_index(target_index, r_grid.shape)]
    plasma_source = [r_grid[source_index], z_grid[source_index], cell_current]
    direct = circular_filament_green_response([vacuum_source, plasma_source], [target])
    plasma = circular_filament_green_response([plasma_source], [target])
    assert abs(plasma['gpsi'][0]) > 1e-12
    np.testing.assert_allclose(result['psi'][target_index], direct['gpsi'][0], rtol=1e-10)
    np.testing.assert_allclose(result['BR'][target_index], direct['gBR'][0], rtol=1e-10)
    np.testing.assert_allclose(result['BZ'][target_index], direct['gBZ'][0], rtol=1e-10)
    for output, vacuum_key, plasma_key in (('psi', 'gpsi', 'gpsi'),
                                           ('BR', 'gBR', 'gBR'), ('BZ', 'gBZ', 'gBZ')):
        increment = result[output][target_index] - vacuum[vacuum_key].reshape(r_grid.shape)[target_index]
        np.testing.assert_allclose(increment, plasma[plasma_key][0], rtol=1e-8, atol=1e-15)


def test_frank_egedal_closure_feeds_per_radian_free_boundary_step():
    r_grid, z_grid = np.meshgrid(np.linspace(0.1, 0.5, 7), np.linspace(-0.2, 0.2, 7))
    points = np.column_stack((r_grid.ravel(), z_grid.ravel()))
    sources = np.column_stack((points, np.ones(points.shape[0])))
    green = dense_axisymmetric_green_response(points, sources)
    vacuum_source = [0.7, 0.0, 1e6]
    vacuum = circular_filament_green_response([vacuum_source], points)
    psi_vac = vacuum["gpsi"].reshape(r_grid.shape)
    active = np.zeros_like(r_grid, dtype=bool)
    source_index = (3, 4)
    active[source_index] = True

    result = solve_free_boundary_anisotropic_picard(
        r_grid=r_grid,
        z_grid=z_grid,
        psi_vac=psi_vac,
        br_vac=vacuum["gBR"].reshape(r_grid.shape),
        bz_vac=vacuum["gBZ"].reshape(r_grid.shape),
        g_psi=green["gpsi"],
        g_br=green["gBR"],
        g_bz=green["gBZ"],
        plasma_mask=active,
        pressure_closure=solve_frank_egedal_pressure_closure,
        params={
            "p0": 100.0,
            "psi_axis": float(np.min(psi_vac)),
            "psi_edge": float(np.max(psi_vac)),
            "mirror_ratio": 2.0,
            "legendre_degrees": [0.5],
            "source_coefficients": [1.0],
            "velocity_nodes": 4,
            "pitch_nodes": 4,
        },
        tol=1e-12,
        maxiter=1,
        relax=0.0,
    )

    cell_current = result["picard_current_state"][np.ravel_multi_index(source_index, r_grid.shape)]
    assert abs(cell_current) > 1e-6
    target_index = (5, 1)
    target = points[np.ravel_multi_index(target_index, r_grid.shape)]
    plasma_source = [r_grid[source_index], z_grid[source_index], cell_current]
    direct = circular_filament_green_response([vacuum_source, plasma_source], [target])
    for field, key in (("psi", "gpsi"), ("BR", "gBR"), ("BZ", "gBZ")):
        np.testing.assert_allclose(result[field][target_index], direct[key][0], rtol=1e-10)

    terminal_closure = solve_frank_egedal_pressure_closure(
        psi=result["psi"], B=result["B"], params=result["parameters"]
    )
    for field in ("p_parallel", "p_perp"):
        np.testing.assert_allclose(result["profiles"][field], terminal_closure[field])


# 验证：自洽 BR/BZ Green 响应是成对合同，单独提供一个会改变 B 的物理含义，必须拒绝。
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
    for name in ("r_grid", "z_grid", "params", "tol", "maxiter", "relax"):
        values = _inputs()
        values.pop(name)
        with pytest.raises(ValueError, match=f"{name} is required"):
            _run(values)


def test_zero_step_returns_declared_zero_feedback_state():
    result = _run(_inputs(maxiter=0))
    assert result["failure_reason"] == "maxiter_reached"
    assert result["iterations"] == 0
    np.testing.assert_allclose(result["picard_current_state"], 0.0)

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
