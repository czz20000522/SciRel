from scirel.kinetic.grid_mirror_kinetic_closure import solve_grid_mirror_kinetic_closure

# 覆盖：端态映射、端塞外屏蔽、YAML 嵌套声明与 caller profile(psi) 端口。
from pathlib import Path
import inspect

import numpy as np
import pytest


E, M = 1.602176634e-19, 1.67262192595e-27


def _inputs():
    r, z = np.linspace(0.0, 0.2, 5), np.linspace(-1.0, 1.0, 7)
    R, Z = np.meshgrid(r, z)
    return {
        "r_grid": R,
        "z_grid": Z,
        "b_t": 1.0 + 3.0 * np.abs(Z),
        "psi": 0.5 * R**2,
        "mass_kg": M,
        "charge_c": E,
        "density_ref_m3": 1e18,
        "temperature_parallel_j": 1000 * E,
        "temperature_perpendicular_ref_j": 2000 * E,
        "electron_temperature_j": 500 * E,
        "reference_z": 0.0,
        "plug_left_z": -1.0,
        "plug_right_z": 1.0,
        "loss_cone_refill": 0.05,
        "quadrature_order": 24,
        "plug_potential_mode": "ambipolar_end_loss",
    }


def _run(inputs):
    return solve_grid_mirror_kinetic_closure(inputs)


def test_public_solver_docstring_declares_contract():
    doc = inspect.getdoc(solve_grid_mirror_kinetic_closure)
    assert doc is not None
    for section in ("Parameters", "Returns", "Raises", "Notes"):
        assert section in doc
    for field in ("current_balance_solved", "confine_to_plug_planes", "psi"):
        assert field in doc


def test_nested_kinetic_closure_maps_end_states_and_remains_neutral():
    result = _run(_inputs())
    assert result["p_parallel"].shape == (7, 5)
    assert np.all(result["end_left_potential_v"] < 0.0)
    assert np.max(np.abs(result["relative_charge_residual"])) < 1e-9


def test_prescribed_end_potentials_evaluate_without_endpoint_current_balance():
    inputs = {
        **_inputs(),
        "plug_potential_mode": "prescribed",
        "phi_plug_left_v": 20.0,
        "phi_plug_right_v": -10.0,
    }
    result = _run(inputs)
    np.testing.assert_allclose(result["end_left_potential_v"], 20.0)
    np.testing.assert_allclose(result["end_right_potential_v"], -10.0)
    assert np.max(np.abs(result["end_left_relative_current_residual"])) > 1e-3
    assert result["converged"]
    assert np.max(np.abs(result["relative_charge_residual"])) < 1e-9


def test_flux_coordinate_rescaling_requires_rescaled_profile_callbacks():
    inputs = _inputs()
    scaled = {**inputs, "psi": inputs["psi"] * (2.0 * np.pi)}
    original = _run(inputs)
    consistent = _run(scaled)
    for name in ("p_parallel", "p_perpendicular", "ion_density", "end_left_potential_v"):
        np.testing.assert_allclose(consistent[name], original[name], rtol=1e-11, atol=0.0)

    psi_max = np.max(inputs["psi"])
    unadjusted_profile = lambda psi: 1e18 * (1.0 - 0.05 * psi / psi_max)
    unscaled_profile = _run({**inputs, "density_ref_m3": unadjusted_profile})
    scaled_profile = _run({**scaled, "density_ref_m3": unadjusted_profile})
    assert np.max(np.abs(unscaled_profile["ion_density"] - scaled_profile["ion_density"])) > 1e15


def test_confinement_mask_zeros_outside_plug_planes():
    inputs = _inputs()
    inputs["plug_left_z"], inputs["plug_right_z"] = -0.6, 0.6
    result = _run(inputs)
    np.testing.assert_allclose(result["ion_density"][[0, -1]], 0.0)


def test_confinement_preserves_original_moments_and_endpoint_diagnostics():
    inputs = {**_inputs(), "plug_left_z": -0.6, "plug_right_z": 0.6}
    confined = _run(inputs)
    full = _run({**inputs, "confine_to_plug_planes": False})
    for name in (
        "density_m3",
        "p_parallel_pa",
        "electrostatic_potential",
        "end_left_potential_v",
        "end_right_ion_particle_flux_m2_s",
    ):
        np.testing.assert_allclose(confined[name], full[name])
    assert np.all(confined["ion_density"][[0, -1]] == 0.0)
    assert np.all(confined["electron_density"][[0, -1]] == 0.0)
    assert np.any(full["ion_density"][[0, -1]] > 0.0)
    assert np.any(full["electron_density"][[0, -1]] > 0.0)


def test_endpoint_and_nested_failures_propagate_without_terminal_state():
    from scirel.kinetic.grid_mirror_kinetic_closure import _run_composition
    from scirel.geometry.flux_surface_profile import evaluate_flux_surface_profile
    from scirel.closures.mirror_ambipolar_potential import solve_mirror_ambipolar_potential

    calls = []

    def failed_endpoint(*args, **kwargs):
        calls.append("endpoint")
        raise RuntimeError("endpoint failure")

    def failed_nested(*args, **kwargs):
        calls.append("nested")
        raise RuntimeError("nested failure")

    def loader(endpoint):
        return lambda asset_id: {
            "scirel.geometry.flux_surface_profile": evaluate_flux_surface_profile,
            "scirel.closures.mirror_ambipolar_potential": endpoint,
        }[asset_id]

    with pytest.raises(RuntimeError, match="endpoint failure"):
        _run_composition(
            _inputs(),
            asset_loader=loader(failed_endpoint),
            composition_loader=lambda _: failed_nested,
        )
    assert calls == ["endpoint"]

    calls.clear()
    with pytest.raises(RuntimeError, match="nested failure"):
        _run_composition(
            _inputs(),
            asset_loader=loader(solve_mirror_ambipolar_potential),
            composition_loader=lambda _: failed_nested,
        )
    assert calls == ["nested"]


def test_yaml_declares_nested_composition_dependency():
    text = Path(__file__).with_name("composition.yaml").read_text(encoding="utf-8")
    assert "kind: scientific_composition" in text
    assert "scirel.closures.compositions.mirror_quasineutral_closure" in text


def test_profile_port_is_evaluated_against_current_flux():
    inputs = _inputs()
    inputs["density_ref_m3"] = lambda psi: 1e18 * (1.0 - 0.2 * psi / np.max(psi))
    result = _run(inputs)
    assert np.all(np.isfinite(result["ion_density"]))
    assert np.max(np.abs(result["relative_charge_residual"])) < 1e-9


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
    unconfined = _run(
        {**_inputs(), "plug_left_z": -0.6, "plug_right_z": 0.6, "confine_to_plug_planes": False}
    )
    confined = _run(
        {**_inputs(), "plug_left_z": -0.6, "plug_right_z": 0.6, "confine_to_plug_planes": True}
    )
    for name in (
        "density_pitch_integral",
        "parallel_pitch_integral",
        "perpendicular_pitch_integral",
    ):
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
