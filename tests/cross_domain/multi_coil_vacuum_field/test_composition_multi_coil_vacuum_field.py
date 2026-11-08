import inspect

from scirel.field.multi_coil_vacuum_field import solve_multi_coil_vacuum_field
from cross_domain._review_bindings import load_asset as _load_asset
import numpy as np
import pytest

from scirel.field.multi_coil_vacuum_field import _run_composition


def _assets(asset_ref):
    return _load_asset(asset_ref)


def _inputs(current=1000.0):
    r_grid, z_grid = np.meshgrid(np.linspace(0.0, 0.3, 5), np.linspace(-0.2, 0.2, 4))
    return {
        "r_grid": r_grid,
        "z_grid": z_grid,
        "rectangular_coils": [
            {
                "r0_m": 0.45,
                "z0_m": 0.0,
                "nr": 2,
                "nz": 2,
                "dr_m": 0.04,
                "dz_m": 0.05,
                "current_a": current,
            }
        ],
    }


def _private(values):
    return _run_composition(
        values["r_grid"],
        values["z_grid"],
        values["rectangular_coils"],
        asset_loader=_assets,
    )


def _public(values):
    return solve_multi_coil_vacuum_field(
        values["r_grid"],
        values["z_grid"],
        values["rectangular_coils"],
    )


def test_public_function_has_explicit_physical_inputs_and_rejects_legacy_entry_points():
    signature = inspect.signature(solve_multi_coil_vacuum_field)
    assert str(signature) == "(r_grid, z_grid, rectangular_coils)"
    assert all(
        parameter.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
        and parameter.default is inspect.Parameter.empty
        for parameter in signature.parameters.values()
    )
    assert str(inspect.signature(_run_composition)) == (
        "(r_grid, z_grid, rectangular_coils, *, asset_loader)"
    )

    values = _inputs()
    with pytest.raises(TypeError, match="missing"):
        solve_multi_coil_vacuum_field(values)
    with pytest.raises(TypeError, match="unexpected keyword argument 'inputs'"):
        solve_multi_coil_vacuum_field(inputs=values)
    with pytest.raises(TypeError, match="unexpected keyword argument 'unknown'"):
        solve_multi_coil_vacuum_field(**values, unknown=True)


def test_explicit_public_call_matches_the_pre_change_mapping_snapshot():
    # Captured from the parent revision's mapping entry point before this interface migration.
    expected = {
        "psi_vac": np.array(
            [
                [
                    0.0,
                    1.1995592059861515e-05,
                    4.813742541289008e-05,
                    1.0833973584263316e-04,
                    1.8987372604306507e-04,
                ],
                [
                    0.0,
                    1.5307063064789825e-05,
                    6.298920703328872e-05,
                    1.49119545072835e-04,
                    2.8695886103297135e-04,
                ],
                [
                    0.0,
                    1.5307063064789825e-05,
                    6.298920703328872e-05,
                    1.49119545072835e-04,
                    2.8695886103297135e-04,
                ],
                [
                    0.0,
                    1.1995592059861515e-05,
                    4.813742541289008e-05,
                    1.0833973584263316e-04,
                    1.898737260430651e-04,
                ],
            ],
            dtype=float,
        ),
        "b_r_vac": np.array(
            [
                [
                    0.0,
                    -4.034803829526184e-04,
                    -8.730358994964485e-04,
                    -1.4823435424997423e-03,
                    -2.2832279940890403e-03,
                ],
                [
                    0.0,
                    -2.0338471566620816e-04,
                    -4.737535135330508e-04,
                    -9.418466942901099e-04,
                    -1.9994354332732705e-03,
                ],
                [
                    0.0,
                    2.033847156662081e-04,
                    4.737535135330507e-04,
                    9.418466942901097e-04,
                    1.999435433273269e-03,
                ],
                [
                    0.0,
                    4.034803829526184e-04,
                    8.730358994964485e-04,
                    1.4823435424997423e-03,
                    2.2832279940890403e-03,
                ],
            ],
            dtype=float,
        ),
        "b_z_vac": np.array(
            [
                [
                    0.004258757023639076,
                    0.004271037543465926,
                    0.0042914720506763695,
                    0.0042531420881130174,
                    0.003979623603195386,
                ],
                [
                    0.005393120674315974,
                    0.005492571649502415,
                    0.005816541170928677,
                    0.006455493049471145,
                    0.0075973502080489645,
                ],
                [
                    0.005393120674315974,
                    0.005492571649502417,
                    0.005816541170928676,
                    0.006455493049471145,
                    0.0075973502080489645,
                ],
                [
                    0.004258757023639076,
                    0.004271037543465925,
                    0.0042914720506763695,
                    0.0042531420881130174,
                    0.003979623603195386,
                ],
            ],
            dtype=float,
        ),
        "filaments": np.array(
            [
                [0.43, -0.025, 1.0],
                [0.43, 0.025, 1.0],
                [0.47000000000000003, -0.025, 1.0],
                [0.47000000000000003, 0.025, 1.0],
            ],
            dtype=float,
        ),
    }

    result = _public(_inputs())

    assert isinstance(result, dict)
    assert list(result) == ["psi_vac", "b_r_vac", "b_z_vac", "filaments"]
    for name, value in result.items():
        assert value.dtype == np.float64
        assert value.shape == expected[name].shape
        np.testing.assert_allclose(value, expected[name], rtol=2.0e-14, atol=1.0e-300)


def test_public_callable_documents_the_catalog_contract():
    text = inspect.getdoc(solve_multi_coil_vacuum_field) or ""
    assert "rectangular_coils" in text
    assert "psi_vac" in text
    assert "Wb/rad" in text
    assert "Raises" in text


def test_explicit_coil_current_scales_vacuum_field_linearly():
    one = _private(_inputs())
    two = _private(_inputs(2000.0))
    for name in ("psi_vac", "b_r_vac", "b_z_vac"):
        np.testing.assert_allclose(two[name], 2.0 * one[name], rtol=2.0e-14, atol=1.0e-300)
    assert one["filaments"].shape == (4, 3)
    np.testing.assert_allclose(one["filaments"][:, 2], 1.0)


def test_current_is_one_set_drive_not_sum_divided_filament_current():
    result = _private(_inputs(1000.0))
    geometry = _assets("scirel.field.rectangular_coil_filaments")
    green = _assets("scirel.field.circular_filament_green")
    points = geometry(0.45, 0.0, 2, 2, 0.04, 0.05, 0.0)
    r_grid = _inputs()["r_grid"]
    z_grid = _inputs()["z_grid"]
    expected = green(
        np.column_stack((points, np.ones(points.shape[0]))),
        np.column_stack((r_grid.ravel(), z_grid.ravel())),
    )
    np.testing.assert_allclose(
        result["psi_vac"],
        (1000.0 * expected["gpsi"]).reshape(r_grid.shape),
        rtol=2.0e-14,
        atol=1.0e-300,
    )


def test_rejects_missing_current_contract():
    values = _inputs()
    del values["rectangular_coils"][0]["current_a"]
    with pytest.raises(ValueError, match="current_a"):
        _private(values)


@pytest.mark.parametrize("shape", [(0, 2), (2, 0), (0, 0)])
def test_rejects_empty_target_grids_before_indexing(shape):
    values = _inputs()
    values["r_grid"] = np.empty(shape)
    values["z_grid"] = np.empty(shape)
    with pytest.raises(ValueError, match="nonempty"):
        _public(values)


@pytest.mark.parametrize("shape", [(1, 1), (1, 3), (3, 1)])
def test_singleton_target_axes_remain_supported(shape):
    values = _inputs()
    values["r_grid"], values["z_grid"] = np.meshgrid(
        np.linspace(0.0, 0.3, shape[1]), np.linspace(-0.2, 0.2, shape[0])
    )
    result = _public(values)
    for name in ("psi_vac", "b_r_vac", "b_z_vac"):
        assert result[name].shape == shape
        assert np.isfinite(result[name]).all()


def test_unrepresentable_vacuum_field_fails_closed():
    r_grid = np.array([[0.0, 0.47 + 1e-16], [0.0, 0.47 + 1e-16]])
    z_grid = np.array([[0.0, 0.0], [0.025, 0.025]])
    values = {
        "r_grid": r_grid,
        "z_grid": z_grid,
        "rectangular_coils": [
            {
                "r0_m": 0.45,
                "z0_m": 0.0,
                "nr": 2,
                "nz": 2,
                "dr_m": 0.04,
                "dz_m": 0.05,
                "current_a": 1e308,
            }
        ],
    }

    with pytest.raises(FloatingPointError) as raised:
        _private(values)
    assert (
        str(raised.value)
        == "current-weighted Green response is not representable as finite float64"
    )


def test_contract_keeps_two_coil_source_blocks_and_currents_independent():
    first = _inputs(700.0)
    second = _inputs(-300.0)
    second["rectangular_coils"][0]["z0_m"] = 0.08
    combined = {
        "r_grid": first["r_grid"],
        "z_grid": first["z_grid"],
        "rectangular_coils": [first["rectangular_coils"][0], second["rectangular_coils"][0]],
    }
    total = _private(combined)
    one = _private(first)
    two = _private(second)
    for name in ("psi_vac", "b_r_vac", "b_z_vac"):
        np.testing.assert_allclose(total[name], one[name] + two[name], rtol=2.0e-14, atol=1.0e-300)
    assert total["filaments"].shape == (8, 3)


def test_ampere_turns_are_split_over_filaments_in_proportion_to_weights():
    per_filament = _private(_inputs(250.0))
    values = _inputs()
    coil = values["rectangular_coils"][0]
    del coil["current_a"]
    coil["ampere_turns_a"] = 1000.0
    total = _private(values)
    for name in ("psi_vac", "b_r_vac", "b_z_vac"):
        np.testing.assert_allclose(total[name], per_filament[name], rtol=2.0e-14, atol=1.0e-300)
    coil["weights"] = [1.0, 1.0, 2.0, 4.0]
    weighted = _private(values)
    values["rectangular_coils"][0] = {
        key: value for key, value in coil.items() if key != "ampere_turns_a"
    }
    values["rectangular_coils"][0]["current_a"] = 1000.0 / 8.0
    np.testing.assert_allclose(weighted["b_z_vac"], _private(values)["b_z_vac"], rtol=2.0e-14)


def test_single_filament_axis_field_matches_the_loop_formula_for_both_current_forms():
    radius, current = 0.3, 1234.0
    r_grid, z_grid = np.meshgrid([0.0, 0.01], [-0.2, 0.0, 0.35])
    for key in ("current_a", "ampere_turns_a"):
        coil = {
            "r0_m": radius,
            "z0_m": 0.0,
            "nr": 1,
            "nz": 1,
            "dr_m": 0.01,
            "dz_m": 0.01,
            key: current,
        }
        field = _private({"r_grid": r_grid, "z_grid": z_grid, "rectangular_coils": [coil]})
        expected = (
            4e-7 * np.pi * current * radius**2 / (2.0 * (radius**2 + z_grid[:, 0] ** 2) ** 1.5)
        )
        np.testing.assert_allclose(field["b_z_vac"][:, 0], expected, rtol=1e-6)


@pytest.mark.parametrize("keys", [(), ("current_a", "ampere_turns_a")])
def test_coil_needs_exactly_one_current_form(keys):
    values = _inputs()
    coil = values["rectangular_coils"][0]
    del coil["current_a"]
    for key in keys:
        coil[key] = 1000.0
    with pytest.raises(ValueError, match="exactly one of current_a"):
        _private(values)


def test_ampere_turns_reject_weights_that_sum_to_zero():
    values = _inputs()
    coil = values["rectangular_coils"][0]
    del coil["current_a"]
    coil.update(ampere_turns_a=1000.0, weights=[1.0, -1.0, 1.0, -1.0])
    with pytest.raises(ValueError, match="nonzero finite sum"):
        _private(values)
