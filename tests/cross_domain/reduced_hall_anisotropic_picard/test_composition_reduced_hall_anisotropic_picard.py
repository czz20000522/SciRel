from scirel.equilibrium.reduced_hall_anisotropic_picard import solve_reduced_hall_anisotropic_picard
import scirel
from cross_domain._review_bindings import load_asset as _load_asset, load_composition as _load_composition, load_callable as _load_callable
import importlib.util
from pathlib import Path
import inspect

import numpy as np
import pytest

from scirel.equilibrium import reduced_hall_anisotropic_picard as composition
from scirel.field.circular_filament_green import circular_filament_green_response
from scirel.field.mirror_plasma_green import build_mirror_plasma_flux_green
M, E = 1.67262192595e-27, 1.602176634e-19


def _loader(asset_ref):
    return _load_asset(asset_ref)

def _closure(B, psi):
    pressure = 10.0 + 1500.0 * psi
    return {'p_parallel': pressure, 'p_perpendicular': pressure, 'ion_density': np.full_like(psi, 1e18), 'electron_pressure': np.zeros_like(psi), 'electrostatic_potential': np.zeros_like(psi), 'ion_p_parallel': pressure, 'ion_p_perpendicular': pressure}


def _scalar_pressure_closure(B, psi):
    return {'p_parallel': 7.0, 'p_perpendicular': 5.0, 'ion_density': np.full_like(psi, 1e18), 'electron_pressure': np.zeros_like(psi), 'electrostatic_potential': np.zeros_like(psi), 'ion_p_parallel': 7.0, 'ion_p_perpendicular': 5.0}


def _inputs(**overrides):
    r, z = np.linspace(0., .4, 7), np.linspace(-.5, .5, 7)
    R, Z = np.meshgrid(r, z)
    values = dict(r_grid=R, z_grid=Z, psi_vac=.5 * 1.2 * R**2, g_psi=np.zeros((R.size, R.size)), ion_mass_kg=M, ion_charge_c=E, pressure_closure=_closure, hall_multiplier=0.0, tol=1e-12, maxiter=3)
    values.update(overrides)
    return values


def test_public_solver_docstring_declares_contract():
    doc = inspect.getdoc(solve_reduced_hall_anisotropic_picard)
    assert doc is not None
    for section in ("Parameters", "Returns", "Raises", "Notes"):
        assert section in doc
    for field in ("hall_state", "fixed-point", "global"):
        assert field in doc


def test_hall_disabled_recovers_static_pressure_current_and_vacuum_flux():
    inputs = _inputs()
    result = composition.run_composition(inputs, asset_loader=_loader)
    assert result['converged'] and result['iterations'] == 1
    np.testing.assert_allclose(result['psi'], inputs['psi_vac'])
    np.testing.assert_allclose(result['J_phi'][:, 1:], 1500.0 * inputs['r_grid'][:, 1:], rtol=1e-12)
    np.testing.assert_allclose(result['ion_toroidal_velocity'], 0.0)


def test_nonzero_green_uses_previous_actual_state_feedback():
    inputs = _inputs(maxiter=2, tol=1e-30)
    inputs['g_psi'] = np.eye(inputs['r_grid'].size) * 1e-9
    result = composition.run_composition(inputs, asset_loader=_loader)
    assert result['iterations'] == 2
    assert not result['converged']
    assert not np.array_equal(result['psi'], inputs['psi_vac'])
    assert len(result['iteration_history']) == 2


def test_per_radian_filament_and_mirror_green_feed_hall_disabled_graph():
    radial = np.linspace(0.1, 0.5, 17)
    axial = np.linspace(-0.2, 0.2, 17)
    r_grid, z_grid = np.meshgrid(radial, axial)
    points = np.column_stack((r_grid.ravel(), z_grid.ravel()))
    vacuum_source = [0.7, 0.0, 3.0]
    psi_vac = circular_filament_green_response([vacuum_source], points)['gpsi'].reshape(r_grid.shape)
    g_psi = build_mirror_plasma_flux_green(r_grid, z_grid)['g_psi']
    source_index = (8, 12)
    active = np.zeros_like(r_grid, dtype=bool)
    active[source_index] = True
    slope = 10.0

    def pressure_closure(_b, psi):
        pressure = 10.0 + slope * psi
        return {
            'p_parallel': pressure,
            'p_perpendicular': pressure,
            'ion_p_parallel': pressure,
            'ion_p_perpendicular': pressure,
            'ion_density': np.full_like(psi, 1e18),
            'electron_pressure': np.zeros_like(psi),
            'electrostatic_potential': np.zeros_like(psi),
        }

    result = composition.run_composition({
        'r_grid': r_grid,
        'z_grid': z_grid,
        'psi_vac': psi_vac,
        'g_psi': g_psi,
        'ion_mass_kg': M,
        'ion_charge_c': E,
        'pressure_closure': pressure_closure,
        'plasma_mask': active,
        'hall_multiplier': 0.0,
        'maxiter': 1,
        'tol': 1e-12,
        'relax': 0.0,
    }, asset_loader=_loader)

    cell_current = slope * r_grid[source_index] * (radial[1] - radial[0]) * (axial[1] - axial[0])
    np.testing.assert_allclose(result['J_phi'][source_index], slope * r_grid[source_index], rtol=1e-8)
    target_index = (12, 4)
    target = points[np.ravel_multi_index(target_index, r_grid.shape)]
    plasma_source = [r_grid[source_index], z_grid[source_index], cell_current]
    direct = circular_filament_green_response([vacuum_source, plasma_source], [target])
    plasma_flux = circular_filament_green_response([plasma_source], [target])['gpsi'][0]
    assert np.max(np.abs(result['psi'] - psi_vac)) / np.max(np.abs(psi_vac)) > 1e-6
    np.testing.assert_allclose(result['psi'][target_index] - psi_vac[target_index], plasma_flux, rtol=1e-10, atol=1e-18)
    np.testing.assert_allclose(result['B_R'][target_index], direct['gBR'][0], rtol=0.02, atol=0.0)
    np.testing.assert_allclose(result['B_Z'][target_index], direct['gBZ'][0], rtol=0.02, atol=0.0)


def test_scalar_pressure_broadcast_preserves_pa_value():
    result = composition.run_composition(_inputs(pressure_closure=_scalar_pressure_closure, maxiter=1, strict_compatibility=False), asset_loader=_loader)
    np.testing.assert_array_equal(result['p_parallel'], np.full_like(result['psi'], 7.0))
    np.testing.assert_array_equal(result['p_perpendicular'], np.full_like(result['psi'], 5.0))


def test_non_grid_pressure_shape_fails_closed():
    def bad_closure(B, psi):
        return {'p_parallel': np.ones((2, 2)), 'p_perpendicular': 5.0, 'ion_density': np.full_like(psi, 1e18), 'electron_pressure': np.zeros_like(psi), 'electrostatic_potential': np.zeros_like(psi), 'ion_p_parallel': 7.0, 'ion_p_perpendicular': 5.0}

    with pytest.raises(ValueError, match='pressure fields'):
        composition.run_composition(_inputs(pressure_closure=bad_closure, maxiter=1), asset_loader=_loader)


def test_yaml_declares_three_leaves_and_explicit_closure_port():
    text = Path(__file__).with_name('composition.yaml').read_text(encoding='utf-8')
    assert 'primary_pfm_node: N13' in text
    assert 'scirel.field.poloidal_field_from_flux' in text
    assert 'scirel.closures.reduced_hall_drift' in text
    assert 'scirel.equilibrium.axisymmetric_picard_update' in text
    assert 'pressure_closure' in text


def test_review_gate_rejects_nonfinite_and_coerced_hall_controls():
    with pytest.raises(ValueError, match="tol must be a finite scalar"):
        composition.run_composition(_inputs(tol=np.nan), asset_loader=_loader)
    with pytest.raises(ValueError, match="maxiter must be an integer"):
        composition.run_composition(_inputs(maxiter=1.2), asset_loader=_loader)
    with pytest.raises(ValueError, match="strict_compatibility must be a boolean"):
        composition.run_composition(_inputs(strict_compatibility=0), asset_loader=_loader)
    with pytest.raises(ValueError, match="inertia_tolerance must be a finite scalar"):
        composition.run_composition(_inputs(inertia_tolerance=np.nan), asset_loader=_loader)


def test_review_gate_allows_negative_firehose_threshold_to_disable_that_check():
    def loader(reference):
        asset = _load_asset(reference)
        if reference != "scirel.closures.reduced_hall_drift":
            return asset

        def drift(*args, **kwargs):
            result = dict(asset(*args, **kwargs))
            result["firehose_margin"] = -np.ones_like(result["J_phi"])
            return result

        return drift

    result = composition.run_composition(
        _inputs(minimum_firehose_margin=-1.0, strict_compatibility=False),
        asset_loader=loader,
    )
    assert np.all(result["firehose_margin"] == -1.0)


def test_review_gate_rejects_nonfinite_hall_grid_state():
    values = _inputs()
    values["psi_vac"] = np.array(values["psi_vac"], copy=True)
    values["psi_vac"][0, 0] = np.nan
    with pytest.raises(ValueError, match="must be finite"):
        composition.run_composition(values, asset_loader=_loader)


def test_reduced_hall_terminal_floor_precedes_terminal_closure():
    calls = {'field': 0, 'closure': 0}

    def instrumented_closure(B, psi):
        calls['closure'] += 1
        return _closure(B, psi)

    def loader(reference):
        asset = _load_asset(reference)
        if reference != 'scirel.field.poloidal_field_from_flux':
            return asset

        def field(_r_grid, _z_grid, psi):
            calls['field'] += 1
            level = 2.0 if calls['field'] == 1 else 0.5
            shape = np.asarray(psi).shape
            return {
                'B_R': np.zeros(shape),
                'B_Z': np.full(shape, level),
                'B': np.full(shape, level),
            }

        return field

    with pytest.raises(FloatingPointError, match='terminal magnetic field vanished'):
        composition.run_composition(
            _inputs(pressure_closure=instrumented_closure, minimum_field=1.0, maxiter=1),
            asset_loader=loader,
        )
    assert calls['field'] == 2
    assert calls['closure'] == 1


def test_reduced_hall_rejects_nonboolean_fixed_and_callable_masks():
    with pytest.raises(ValueError, match='boolean array'):
        composition.run_composition(
            _inputs(plasma_mask=np.ones((7, 7), dtype=int)), asset_loader=_loader
        )

    def nonboolean_callable(_b, psi):
        return np.ones_like(psi, dtype=int)

    with pytest.raises(ValueError, match='callable plasma_mask.*boolean'):
        composition.run_composition(
            _inputs(plasma_mask=nonboolean_callable, maxiter=1), asset_loader=_loader
        )

    def boolean_callable(_b, psi):
        return np.ones_like(psi, dtype=bool)

    result = composition.run_composition(
        _inputs(plasma_mask=boolean_callable, maxiter=1), asset_loader=_loader
    )
    assert result['J_phi'].shape == (7, 7)
