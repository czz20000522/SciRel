from scirel.field.multi_coil_vacuum_field import solve_multi_coil_vacuum_field
import scirel
from _review_bindings import load_asset as _load_asset, load_graph as _load_graph, load_operator as _load_operator
import numpy as np
import pytest

from scirel.field.multi_coil_vacuum_field import run_graph
def _assets(asset_ref):
    return _load_asset(asset_ref)

def _inputs(current=1000.0):
    r_grid, z_grid = np.meshgrid(np.linspace(0.0, 0.3, 5), np.linspace(-0.2, 0.2, 4))
    return {
        "r_grid": r_grid,
        "z_grid": z_grid,
        "rectangular_coils": [{"r0_m": 0.45, "z0_m": 0.0, "nr": 2, "nz": 2, "dr_m": 0.04, "dz_m": 0.05, "current_a": current}],
    }


def test_explicit_coil_current_scales_vacuum_field_linearly():
    one = run_graph(_inputs(), asset_loader=_assets)
    two = run_graph(_inputs(2000.0), asset_loader=_assets)
    for name in ("psi_vac", "b_r_vac", "b_z_vac"):
        np.testing.assert_allclose(two[name], 2.0 * one[name], rtol=2.0e-14, atol=1.0e-300)
    assert one["filaments"].shape == (4, 3)
    np.testing.assert_allclose(one["filaments"][:, 2], 1.0)


def test_current_is_one_set_drive_not_sum_divided_filament_current():
    result = run_graph(_inputs(1000.0), asset_loader=_assets)
    geometry = _assets("scirel.field.rectangular_coil_filaments")
    green = _assets("scirel.field.circular_filament_green")
    points = geometry(0.45, 0.0, 2, 2, 0.04, 0.05, 0.0)
    r_grid = _inputs()["r_grid"]
    z_grid = _inputs()["z_grid"]
    expected = green(np.column_stack((points, np.ones(points.shape[0]))), np.column_stack((r_grid.ravel(), z_grid.ravel())))
    np.testing.assert_allclose(result["psi_vac"], (1000.0 * expected["gpsi"]).reshape(r_grid.shape), rtol=2.0e-14, atol=1.0e-300)


def test_rejects_missing_current_contract():
    values = _inputs()
    del values["rectangular_coils"][0]["current_a"]
    with pytest.raises(ValueError, match="current_a"):
        run_graph(values, asset_loader=_assets)


def test_review_gate_keeps_two_coil_source_blocks_and_currents_independent():
    first = _inputs(700.0)
    second = _inputs(-300.0)
    second["rectangular_coils"][0]["z0_m"] = 0.08
    combined = {
        "r_grid": first["r_grid"],
        "z_grid": first["z_grid"],
        "rectangular_coils": [first["rectangular_coils"][0], second["rectangular_coils"][0]],
    }
    total = run_graph(combined, asset_loader=_assets)
    one = run_graph(first, asset_loader=_assets)
    two = run_graph(second, asset_loader=_assets)
    for name in ("psi_vac", "b_r_vac", "b_z_vac"):
        np.testing.assert_allclose(total[name], one[name] + two[name], rtol=2.0e-14, atol=1.0e-300)
    assert total["filaments"].shape == (8, 3)


def test_weights_scale_per_filament_drive_current_discriminating():
    # r81 clarification: the effective per-filament drive is
    # current_a * weights[i]. With weights 0.5 on a 2x2 section the field
    # is exactly half of the default-weights run at the same current_a.
    # This is the discriminating check for the two conditional readings
    # documented in the exact document: a caller modelling a total section
    # current must distribute weights summing to 1 (0.25 each here), which
    # reproduces the 0.25x-the-all-turns run, not the 1x run.
    one = run_graph(_inputs(1000.0), asset_loader=_assets)
    half = _inputs(1000.0)
    half["rectangular_coils"][0]["weights"] = [0.5] * 4
    half_result = run_graph(half, asset_loader=_assets)
    for name in ("psi_vac", "b_r_vac", "b_z_vac"):
        np.testing.assert_allclose(half_result[name], 0.5 * one[name], rtol=2.0e-14, atol=1.0e-300)
    # the even split of a 1000 A total over 4 filaments (0.25 each)
    # reproduces a 250 A all-turns run exactly
    spread = _inputs(1000.0)
    spread["rectangular_coils"][0]["weights"] = [0.25] * 4
    spread_result = run_graph(spread, asset_loader=_assets)
    quarter = run_graph(_inputs(250.0), asset_loader=_assets)
    for name in ("psi_vac", "b_r_vac", "b_z_vac"):
        np.testing.assert_allclose(spread_result[name], quarter[name], rtol=2.0e-14, atol=1.0e-300)
    np.testing.assert_allclose(half_result["filaments"][:, 2], [0.5] * 4)