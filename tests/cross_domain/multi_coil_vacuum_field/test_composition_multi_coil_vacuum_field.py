import inspect

from scirel.field.multi_coil_vacuum_field import solve_multi_coil_vacuum_field
import scirel
from cross_domain._review_bindings import load_asset as _load_asset, load_composition as _load_composition, load_callable as _load_callable
import numpy as np
import pytest

from scirel.field.multi_coil_vacuum_field import run_composition
def _assets(asset_ref):
    return _load_asset(asset_ref)

def _inputs(current=1000.0):
    r_grid, z_grid = np.meshgrid(np.linspace(0.0, 0.3, 5), np.linspace(-0.2, 0.2, 4))
    return {
        "r_grid": r_grid,
        "z_grid": z_grid,
        "rectangular_coils": [{"r0_m": 0.45, "z0_m": 0.0, "nr": 2, "nz": 2, "dr_m": 0.04, "dz_m": 0.05, "current_a": current}],
    }


def test_public_callable_documents_the_catalog_contract():
    text = inspect.getdoc(solve_multi_coil_vacuum_field) or ""
    assert "rectangular_coils" in text
    assert "psi_vac" in text
    assert "Wb/rad" in text
    assert "Raises" in text


def test_explicit_coil_current_scales_vacuum_field_linearly():
    one = run_composition(_inputs(), asset_loader=_assets)
    two = run_composition(_inputs(2000.0), asset_loader=_assets)
    for name in ("psi_vac", "b_r_vac", "b_z_vac"):
        np.testing.assert_allclose(two[name], 2.0 * one[name], rtol=2.0e-14, atol=1.0e-300)
    assert one["filaments"].shape == (4, 3)
    np.testing.assert_allclose(one["filaments"][:, 2], 1.0)


def test_current_is_one_set_drive_not_sum_divided_filament_current():
    result = run_composition(_inputs(1000.0), asset_loader=_assets)
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
        run_composition(values, asset_loader=_assets)


@pytest.mark.parametrize("shape", [(0, 2), (2, 0), (0, 0)])
def test_rejects_empty_target_grids_before_indexing(shape):
    values = _inputs()
    values["r_grid"] = np.empty(shape)
    values["z_grid"] = np.empty(shape)
    with pytest.raises(ValueError, match="nonempty"):
        solve_multi_coil_vacuum_field(values)


@pytest.mark.parametrize("shape", [(1, 1), (1, 3), (3, 1)])
def test_singleton_target_axes_remain_supported(shape):
    values = _inputs()
    values["r_grid"], values["z_grid"] = np.meshgrid(
        np.linspace(0.0, 0.3, shape[1]), np.linspace(-0.2, 0.2, shape[0])
    )
    result = solve_multi_coil_vacuum_field(values)
    for name in ("psi_vac", "b_r_vac", "b_z_vac"):
        assert result[name].shape == shape
        assert np.isfinite(result[name]).all()


def test_unrepresentable_vacuum_field_fails_closed():
    r_grid = np.array([[0.0, 0.47 + 1e-16], [0.0, 0.47 + 1e-16]])
    z_grid = np.array([[0.0, 0.0], [0.025, 0.025]])
    values = {
        "r_grid": r_grid,
        "z_grid": z_grid,
        "rectangular_coils": [{
            "r0_m": 0.45, "z0_m": 0.0, "nr": 2, "nz": 2,
            "dr_m": 0.04, "dz_m": 0.05, "current_a": 1e308,
        }],
    }

    with pytest.raises(FloatingPointError, match="not representable"):
        run_composition(values, asset_loader=_assets)


def test_review_gate_keeps_two_coil_source_blocks_and_currents_independent():
    first = _inputs(700.0)
    second = _inputs(-300.0)
    second["rectangular_coils"][0]["z0_m"] = 0.08
    combined = {
        "r_grid": first["r_grid"],
        "z_grid": first["z_grid"],
        "rectangular_coils": [first["rectangular_coils"][0], second["rectangular_coils"][0]],
    }
    total = run_composition(combined, asset_loader=_assets)
    one = run_composition(first, asset_loader=_assets)
    two = run_composition(second, asset_loader=_assets)
    for name in ("psi_vac", "b_r_vac", "b_z_vac"):
        np.testing.assert_allclose(total[name], one[name] + two[name], rtol=2.0e-14, atol=1.0e-300)
    assert total["filaments"].shape == (8, 3)
