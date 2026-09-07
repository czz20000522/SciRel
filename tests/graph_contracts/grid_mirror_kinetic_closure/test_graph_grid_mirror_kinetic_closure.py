from scirel.kinetic.grid_mirror_kinetic_closure import solve_grid_mirror_kinetic_closure
import scirel
from _review_bindings import load_asset as _load_asset, load_graph as _load_graph, load_operator as _load_operator
# 覆盖：端态映射、端塞外屏蔽、YAML 嵌套声明与 caller profile(psi) 端口。
from pathlib import Path

import numpy as np


E, M = 1.602176634e-19, 1.67262192595e-27


def _inputs():
    r, z = np.linspace(0., .2, 5), np.linspace(-1., 1., 7)
    R, Z = np.meshgrid(r, z)
    return {'r_grid': R, 'z_grid': Z, 'b_t': 1.0 + 3.0*np.abs(Z), 'psi': .5*R**2, 'mass_kg': M, 'charge_c': E, 'density_ref_m3': 1e18, 'temperature_parallel_j': 1000*E, 'temperature_perpendicular_ref_j': 2000*E, 'electron_temperature_j': 500*E, 'reference_z': 0.0, 'plug_left_z': -1.0, 'plug_right_z': 1.0, 'loss_cone_refill': .05, 'quadrature_order': 24, 'plug_potential_mode': 'ambipolar_end_loss'}


def _run(inputs):
    return solve_grid_mirror_kinetic_closure(inputs)


def test_nested_kinetic_closure_maps_end_states_and_remains_neutral():
    result = _run(_inputs())
    assert result['p_parallel'].shape == (7, 5)
    assert np.all(result['end_left_potential_v'] < 0.0)
    assert np.max(np.abs(result['relative_charge_residual'])) < 1e-9


def test_confinement_mask_zeros_outside_plug_planes():
    inputs = _inputs()
    inputs['plug_left_z'], inputs['plug_right_z'] = -.6, .6
    result = _run(inputs)
    np.testing.assert_allclose(result['ion_density'][[0, -1]], 0.0)


def test_yaml_declares_nested_task_graph_dependency():
    text = Path(__file__).with_name('task_graph.yaml').read_text(encoding='utf-8')
    assert 'kind: scientific_task_graph' in text
    assert 'scirel.closures.graphs.mirror_quasineutral_closure' in text


def test_profile_port_is_evaluated_against_current_flux():
    inputs = _inputs()
    inputs['density_ref_m3'] = lambda psi: 1e18 * (1.0 - 0.2 * psi / np.max(psi))
    result = _run(inputs)
    assert np.all(np.isfinite(result['ion_density']))
    assert np.max(np.abs(result['relative_charge_residual'])) < 1e-9

def test_review_gate_reference_potential_shape_and_end_loss_refill_fail_closed():
    import pytest

    values = _inputs()
    values["phi_ref_v"] = np.zeros_like(values["psi"])
    with pytest.raises(ValueError, match="phi_ref_v"):
        _run(values)
    values = _inputs()
    values["loss_cone_refill"] = 0.0
    values.pop("ion_loss_refill", None)
    with pytest.raises(ValueError, match="positive ion_loss_refill"):
        _run(values)


def test_review_gate_keeps_pitch_integral_diagnostics_full_grid_when_confined():
    unconfined = _run({**_inputs(), "plug_left_z": -0.6, "plug_right_z": 0.6, "confine_to_plug_planes": False})
    confined = _run({**_inputs(), "plug_left_z": -0.6, "plug_right_z": 0.6, "confine_to_plug_planes": True})
    for name in ("density_pitch_integral", "parallel_pitch_integral", "perpendicular_pitch_integral"):
        np.testing.assert_allclose(confined[name], unconfined[name])
    np.testing.assert_allclose(confined["ion_density"][[0, -1]], 0.0)


def test_review_gate_rejects_nonrectilinear_or_nonboolean_controls():
    import pytest

    values = _inputs()
    values["r_grid"] = np.array(values["r_grid"], copy=True)
    values["r_grid"][1, 1] += 1.0e-3
    with pytest.raises(ValueError, match="rectilinear"):
        _run(values)

    values = _inputs()
    values["b_t"] = np.array(values["b_t"], copy=True)
    values["b_t"][0, 0] = np.nan
    with pytest.raises(ValueError, match="finite"):
        _run(values)

    values = _inputs()
    values["confine_to_plug_planes"] = 1
    with pytest.raises(ValueError, match="boolean"):
        _run(values)

    values = _inputs()
    for name in ("r_grid", "z_grid", "b_t", "psi"):
        values[name] = np.asarray(values[name])[:, :1]
    with pytest.raises(ValueError, match="strictly increasing"):
        _run(values)


def test_review_gate_rejects_quadrature_order_below_nested_moment_requirement():
    import pytest

    with pytest.raises(ValueError, match="quadrature_order"):
        _run({**_inputs(), "quadrature_order": 7})
    with pytest.raises(ValueError, match="quadrature_order"):
        _run({**_inputs(), "quadrature_order": 8.5})
