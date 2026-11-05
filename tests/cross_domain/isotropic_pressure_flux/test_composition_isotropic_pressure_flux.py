from cross_domain._review_bindings import load_asset as _load_asset
from pathlib import Path

import numpy as np
import pytest

from scirel.equilibrium import isotropic_pressure_flux as composition


def _asset_loader(asset_ref):
    return _load_asset(asset_ref)


def _run_composition(inputs):
    return composition._run_composition(inputs)


# 验证：YAML 的 PFM 映射和 Picard 反馈边必须与入口图同步。
def test_yaml_declares_single_closure_aware_solver():
    contract = Path(__file__).with_name("composition.yaml").read_text(encoding="utf-8")
    assert "primary_pfm_node: N2" in contract
    assert "asset_ref: scirel.equilibrium.pressure_flux_state" in contract
    assert "asset_ref: scirel.equilibrium.compute-equilibrium" in contract
    assert "to_input: psi" in contract


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
    result = _run_composition(values)
    assert result["iterations"] == 1
    assert result["converged"]
    np.testing.assert_allclose(result["psi"], values["psi_vac"])
    assert result["plasma_currents"].shape == (3, 4)
    assert result["pressure_of_psi"]["extrapolation"] == "zeros"
    assert result["pressure_of_psi"]["degree"] == 3


# 验证：非零 dense plasma Green 矩阵使下一轮 spline 消费上一轮 psi，而不是反复消费 psi_vac。
def test_nonzero_green_changes_flux_through_sequential_feedback():
    values = _inputs(g_psi=1.0e-2 * np.eye(12), maxiter=2, tol=1.0e-30)
    result = _run_composition(values)
    assert result["iterations"] == 2
    assert result["failure_reason"] == "maxiter_reached"
    assert result["residual_history"].shape == (2,)
    assert np.any(np.abs(result["plasma_currents"]) > 0.0)
    assert not np.allclose(result["psi"], values["psi_vac"])


# 验证：plasma_mask 是源码 plas_clip 的显式名称；true cell 必须在 dP/dpsi 乘面积前被清零。
def test_plasma_mask_clips_the_pressure_derivative_before_current_assembly():
    values = _inputs(g_psi=np.eye(12), plasma_mask=np.ones((3, 4), dtype=bool))
    result = _run_composition(values)
    np.testing.assert_allclose(result["plasma_currents"], 0.0)
    np.testing.assert_allclose(result["psi"], values["psi_vac"])


# 验证：该图只接受 field-cell 到 field-point 的 dense方阵，不能误用 coil-to-probe Green cache。
def test_rejects_wrong_green_matrix_shape():
    with pytest.raises(ValueError, match="g_psi must have shape"):
        _run_composition(_inputs(g_psi=np.eye(4)))


def test_requires_all_yaml_required_picard_controls():
    for name in ("tol", "maxiter", "relax"):
        values = _inputs()
        values.pop(name)
        with pytest.raises(ValueError, match=f"{name} is required"):
            _run_composition(values)


def test_review_gate_validates_grid_before_zero_iteration_return():
    r_grid, z_grid = np.meshgrid(np.array([0.2, 0.4, 0.7]), np.array([-0.1, 0.0, 0.1]))
    with pytest.raises(ValueError, match="uniformly spaced tensor-product grids"):
        _run_composition(
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
    result = _run_composition(values)
    dr = values["r_grid"][0, 1] - values["r_grid"][0, 0]
    dz = values["z_grid"][1, 0] - values["z_grid"][0, 0]
    expected = -values["r_grid"] * (1.0 / 0.8) * dr * dz
    np.testing.assert_allclose(result["plasma_currents"], expected, rtol=2.0e-12, atol=2.0e-12)


def test_review_gate_rejects_fractional_picard_iteration_count():
    with pytest.raises(ValueError, match="maxiter must be an integer"):
        _run_composition(_inputs(maxiter=1.2))


def test_review_gate_zero_iteration_returns_an_independent_vacuum_flux_state():
    values = _inputs(maxiter=0)
    vacuum_flux = values["psi_vac"]

    result = _run_composition(values)

    assert result["psi"] is not vacuum_flux
    np.testing.assert_allclose(result["psi"], vacuum_flux)
    result["psi"][0, 0] += 1.0
    assert result["psi"][0, 0] != vacuum_flux[0, 0]
