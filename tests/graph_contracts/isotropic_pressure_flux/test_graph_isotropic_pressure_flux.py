from scirel.equilibrium.isotropic_pressure_flux import solve_isotropic_pressure_flux
import scirel
from _review_bindings import load_asset as _load_asset, load_graph as _load_graph, load_operator as _load_operator
import importlib.util
from pathlib import Path

import numpy as np
import pytest

from scirel.equilibrium import isotropic_pressure_flux as graph
from scirel.field.circular_filament_green import circular_filament_green_response
from scirel.field.dense_axisymmetric_green import dense_axisymmetric_green_response


def _asset_loader(asset_ref):
    return _load_asset(asset_ref)

def _run_graph(inputs):
    return graph.run_graph(inputs, asset_loader=_asset_loader)


# 验证：YAML 的 PFM 映射和 Picard 反馈边必须与入口图同步。
def test_yaml_declares_historical_picard_contract():
    contract = Path(__file__).with_name("task_graph.yaml").read_text(encoding="utf-8")
    assert "primary_pfm_node: N2" in contract
    assert "asset_ref: scirel.equilibrium.pressure_flux_state" in contract
    assert "asset_ref: scirel.equilibrium.isotropic_picard_step" in contract
    assert "to_input: psi_state" in contract


def _pressure_of_radius(radius):
    return max(1.0 - radius / 0.8, 0.0)


def _inputs(**overrides):
    r_grid, z_grid = np.meshgrid(np.linspace(0.2, 0.8, 4), np.array([-0.1, 0.0, 0.1]))
    n_points = r_grid.size
    values = {
        "r_grid": r_grid,
        "z_grid": z_grid,
        "pressure_of_radius": _pressure_of_radius,
        "psi_vac": r_grid.copy(),
        "g_psi": np.zeros((n_points, n_points)),
        "tol": 1.0e-12,
        "maxiter": 1,
        "relax": 0.0,
    }
    values.update(overrides)
    return values


# 验证：G=0 时仍完成一次 source P(psi)->I 链，但 psi 保持真空磁通并形成可重建样条表示。
def test_zero_green_keeps_vacuum_flux_and_returns_pressure_representation():
    values = _inputs()
    result = _run_graph(values)
    assert result["iterations"] == 1
    assert result["converged"]
    np.testing.assert_allclose(result["psi"], values["psi_vac"])
    assert result["plasma_currents"].shape == (3, 4)
    assert result["pressure_of_psi"]["extrapolation"] == "zeros"
    assert result["pressure_of_psi"]["degree"] == 3


# 验证：非零 dense plasma Green 矩阵使下一轮 spline 消费上一轮 psi，而不是反复消费 psi_vac。
def test_nonzero_green_changes_flux_through_sequential_feedback():
    values = _inputs(g_psi=1.0e-2 * np.eye(12), maxiter=2, tol=1.0e-30)
    result = _run_graph(values)
    assert result["iterations"] == 2
    assert result["failure_reason"] == "maxiter_reached"
    assert result["residual_history"].shape == (2,)
    assert np.any(np.abs(result["plasma_currents"]) > 0.0)
    assert not np.allclose(result["psi"], values["psi_vac"])


def test_per_radian_pressure_current_and_filament_flux_in_one_graph_step():
    r_grid, z_grid = np.meshgrid(np.linspace(0.2, 0.8, 7), np.linspace(-0.3, 0.3, 7))
    points = np.column_stack((r_grid.ravel(), z_grid.ravel()))
    green = dense_axisymmetric_green_response(points, np.column_stack((points, np.ones(points.shape[0]))))
    psi_vac = 0.5 * r_grid ** 2
    source_index = (3, 3)
    target_index = (5, 1)
    mask = np.ones_like(r_grid, dtype=bool)
    mask[source_index] = False

    def pressure_of_radius(radius):
        return max(1000.0 * (0.8 - radius), 0.0)

    inputs = {
        "r_grid": r_grid, "z_grid": z_grid,
        "pressure_of_radius": pressure_of_radius,
        "psi_vac": psi_vac, "g_psi": green["gpsi"], "plasma_mask": mask,
        "tol": 1e-12, "maxiter": 1, "relax": 0.0,
    }
    result = _run_graph(inputs)

    current = result["plasma_currents"][source_index]
    assert abs(current) > 1.0
    assert np.count_nonzero(result["plasma_currents"]) == 1
    target = points[np.ravel_multi_index(target_index, r_grid.shape)]
    direct = circular_filament_green_response(
        [[r_grid[source_index], z_grid[source_index], current]], [target]
    )
    assert abs(direct["gpsi"][0]) > 1e-9
    np.testing.assert_allclose(
        result["psi"][target_index] - psi_vac[target_index],
        direct["gpsi"][0], rtol=1e-9, atol=1e-15,
    )

    linked = _run_graph({
        **inputs, "psi_vac": 2.0 * np.pi * psi_vac,
        "g_psi": 2.0 * np.pi * green["gpsi"],
    })
    np.testing.assert_allclose(
        linked["plasma_currents"][source_index], current / (2.0 * np.pi), rtol=1e-9,
    )
    linked_increment = linked["psi"][target_index] - 2.0 * np.pi * psi_vac[target_index]
    np.testing.assert_allclose(linked_increment, direct["gpsi"][0], rtol=1e-9, atol=1e-15)
    assert not np.isclose(linked_increment, 2.0 * np.pi * direct["gpsi"][0], rtol=0.1, atol=0.0)


# 验证：plasma_mask 是源码 plas_clip 的显式名称；true cell 必须在 dP/dpsi 乘面积前被清零。
def test_plasma_mask_clips_the_pressure_derivative_before_current_assembly():
    values = _inputs(g_psi=np.eye(12), plasma_mask=np.ones((3, 4), dtype=bool))
    result = _run_graph(values)
    np.testing.assert_allclose(result["plasma_currents"], 0.0)
    np.testing.assert_allclose(result["psi"], values["psi_vac"])


# 验证：该图只接受 field-cell 到 field-point 的 dense方阵，不能误用 coil-to-probe Green cache。
def test_rejects_wrong_green_matrix_shape():
    with pytest.raises(ValueError, match="g_psi must have shape"):
        _run_graph(_inputs(g_psi=np.eye(4)))


def test_requires_all_yaml_required_picard_controls():
    for name in ("tol", "maxiter", "relax"):
        values = _inputs()
        values.pop(name)
        with pytest.raises(ValueError, match=f"{name} is required"):
            _run_graph(values)


def test_review_gate_validates_grid_before_zero_iteration_return():
    r_grid, z_grid = np.meshgrid(np.array([0.2, 0.4, 0.7]), np.array([-0.1, 0.0, 0.1]))
    with pytest.raises(ValueError, match="uniformly spaced tensor-product grids"):
        _run_graph(
            _inputs(
                r_grid=r_grid,
                z_grid=z_grid,
                psi_vac=r_grid.copy(),
                g_psi=np.zeros((r_grid.size, r_grid.size)),
                maxiter=0,
            )
        )

def test_review_gate_linear_pressure_flux_produces_analytic_cell_current():
    values = _inputs()
    result = _run_graph(values)
    dr = values["r_grid"][0, 1] - values["r_grid"][0, 0]
    dz = values["z_grid"][1, 0] - values["z_grid"][0, 0]
    expected = -values["r_grid"] * (1.0 / 0.8) * dr * dz
    np.testing.assert_allclose(result["plasma_currents"], expected, rtol=2.0e-12, atol=2.0e-12)


def test_review_gate_rejects_fractional_picard_iteration_count():
    with pytest.raises(ValueError, match="maxiter must be an integer"):
        _run_graph(_inputs(maxiter=1.2))


def test_review_gate_zero_iteration_returns_an_independent_vacuum_flux_state():
    values = _inputs(maxiter=0)
    vacuum_flux = values["psi_vac"]

    result = _run_graph(values)

    assert result["psi"] is not vacuum_flux
    np.testing.assert_allclose(result["psi"], vacuum_flux)
    result["psi"][0, 0] += 1.0
    assert result["psi"][0, 0] != vacuum_flux[0, 0]
