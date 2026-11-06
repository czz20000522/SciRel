import inspect

from scirel.kinetic.frank_egedal_pressure_closure import solve_frank_egedal_pressure_closure
from cross_domain._review_bindings import load_asset as _load_asset
from pathlib import Path

import numpy as np
import pytest

from scirel.kinetic import frank_egedal_pressure_closure as composition


def _asset_loader(asset_ref):
    return _load_asset(asset_ref)


def _run_composition(inputs):
    return composition._run_composition(inputs, asset_loader=_asset_loader)


def test_public_callable_documents_the_catalog_contract():
    text = inspect.getdoc(solve_frank_egedal_pressure_closure) or ""
    assert "params" in text
    assert "closure_state" in text
    assert "RuntimeError" in text


def _inputs(**parameter_overrides):
    params = {
        "hot_pressure_scale": 8.0,
        "psi_axis": 0.0,
        "psi_edge": 1.0,
        "B0": 1.0,
        "mirror_ratio": 2.0,
        "legendre_degrees": [0.5],
        "source_coefficients": [1.0],
        "velocity_nodes": 6,
        "pitch_nodes": 6,
    }
    params.update(parameter_overrides)
    return {
        "psi": np.array([[0.0, 0.5], [0.25, 1.0]]),
        "B": np.array([[1.0, 1.1], [1.2, 1.3]]),
        "params": params,
    }


# 验证：YAML 必须显式声明 PFM 映射、节点与不可交换边，避免 composition_fixture.py 独占组合合同。
def test_yaml_declares_the_non_interchangeable_closure_pipeline():
    contract = Path(__file__).with_name("composition.yaml").read_text(encoding="utf-8")
    assert "primary_pfm_node: N4" in contract
    assert "id: loss_cone_spectrum" in contract
    assert "id: hot_ion_moments" in contract
    assert "from: hot_ion_moments" in contract
    assert (
        "inputs: [mirror_ratio, legendre_terms, legendre_backend, legendre_degrees, "
        "legendre_mode_count, legendre_spectrum_grid_points, source_coefficients, "
        "nbi_pitch_angle_deg, spectrum_operator]"
    ) in contract
    assert "to_input: spectrum_operator" in contract
    assert "inputs: [params, spectrum_function]" not in contract
    assert "inputs: [psi, psi_axis, psi_edge, alpha]" in contract
    assert (
        "inputs: [psi, radial_shape, hot_parallel_shape, hot_perpendicular_shape, "
        "hot_density_shape, hot_pressure_scale, gas_dynamic_pressure, "
        "gas_dynamic_density, hot_density_scale, electron_temperature]"
    ) in contract
    assert "p0" not in contract
    assert "background_density" not in contract


# 验证：显式 degree 分支仍须产生有限、同 shape 的两个压力场和可审查闭合状态。
def test_returns_finite_grid_shaped_pressure_and_explicit_closure_state():
    result = _run_composition(_inputs())
    assert result["p_parallel"].shape == (2, 2)
    assert result["p_perp"].shape == (2, 2)
    assert np.all(np.isfinite(result["p_parallel"]))
    assert np.all(np.isfinite(result["p_perp"]))
    assert np.all(result["p_parallel"] >= 0.0)
    assert np.all(result["p_perp"] >= 0.0)
    assert result["closure_state"]["degree_source"] == "caller_supplied"
    assert (
        result["closure_state"]["normalization"]
        == "pressure moments referenced to hot_parallel(b=1); density referenced to hot_density(b=1)"
    )


# 验证：热矩先以 b=1 归一化，随后才乘 hot_pressure_scale，不能把径向或尺度因子混入归一化。
def test_b_equals_one_hot_shapes_are_normalized_before_pressure_scale():
    inputs = _inputs()
    inputs["B"] = np.ones((2, 2))
    inputs["psi"] = np.zeros((2, 2))
    result = _run_composition(inputs)
    # With zero gas/electron terms and radial_shape=1, hot_pressure_scale
    # multiplies the b=1 shapes. p_perp is intentionally referenced to
    # p_parallel,0 and may therefore differ from p_parallel at b=1.
    np.testing.assert_allclose(result["p_parallel"], np.full((2, 2), 8.0), rtol=1.0e-12)
    np.testing.assert_allclose(result["p_perp"], result["p_perp"][0, 0], rtol=1.0e-12)
    assert result["p_perp"][0, 0] > result["p_parallel"][0, 0]


# 验证：密度和电子温度输出的 nullable 合同与源 profile 的可选尺度语义一致。
def test_density_and_temperature_are_only_reported_when_configured():
    without_optional_fields = _run_composition(_inputs())
    assert without_optional_fields["density"] is None
    assert without_optional_fields["electron_temperature"] is None

    with_optional_fields = _run_composition(
        _inputs(gas_dynamic_density=3.0, hot_density_scale=2.0, electron_temperature=4.0)
    )
    assert with_optional_fields["density"].shape == (2, 2)
    np.testing.assert_allclose(with_optional_fields["electron_temperature"], 4.0)
    assert np.all(with_optional_fields["p_parallel"] >= with_optional_fields["density"] * 4.0)


@pytest.mark.parametrize("alias", ["p0", "background_density"])
def test_rejects_legacy_pressure_scale_aliases(alias):
    with pytest.raises(ValueError, match="canonical pressure scale names"):
        _run_composition(_inputs(**{alias: 1.0}))


# Historical node ID: a vc-only perpendicular cut selects a different population.
# At vc=1 the common population remains nonempty, and a constant angular mode
# at B=B0 gives p_perp/p_parallel=(3-xi_max²)/(2*xi_max²)=2.5 for Rm=2.
def test_perpendicular_moment_is_zero_when_critical_speed_reaches_beam_speed():
    result = _run_composition(
        _inputs(
            vc_over_v0=1.0,
            legendre_degrees=[0.0],
            source_coefficients=[1.0],
            beta_m=0.0,
        )
    )
    np.testing.assert_allclose(result["p_perp"][0, 0], 20.0, atol=1.0e-14)
    assert np.all(result["p_perp"] >= 0.0)
    assert result["closure_state"]["velocity_domain"]["lower"] == 0.0
    # Preserve the original degree=.5 case as a nontrivial-mode witness too.
    original_mode = _run_composition(
        _inputs(vc_over_v0=1.0, legendre_degrees=[0.5], source_coefficients=[1.0])
    )
    # The supplied radial envelope vanishes at psi=psi_edge=1.
    assert np.all(original_mode["p_perp"][np.array([[True, True], [True, False]])] > 0.0)
    np.testing.assert_allclose(original_mode["p_perp"][1, 1], 0.0, atol=1e-14)


# 验证：未给 degree 时只从 emitted function 读取损失锥谱，而不是读取原始 SciRel 源码。
def test_uses_emitted_loss_cone_asset_when_degrees_are_not_supplied():
    inputs = _inputs()
    del inputs["params"]["legendre_degrees"]
    del inputs["params"]["source_coefficients"]
    inputs["params"]["legendre_mode_count"] = 1
    inputs["params"]["legendre_spectrum_grid_points"] = 16
    result = _run_composition(inputs)
    assert result["closure_state"]["degree_source"] == "scirel.kinetic.loss_cone_spectrum"
    assert result["closure_state"]["degrees"].shape == (1,)


def test_requires_explicit_params_contract():
    inputs = _inputs()
    inputs.pop("params")
    with pytest.raises(ValueError, match="params is required"):
        _run_composition(inputs)


@pytest.mark.parametrize(
    "mutator",
    [
        lambda value: {**value, "B": np.ones((3, 3))},
        lambda value: {**value, "psi": np.ones((2, 2, 1))},
        lambda value: {**value, "params": {**value["params"], "psi_edge": 0.0}},
    ],
)
# 验证：shape、二维网格和径向归一化合同不合法时必须 fail closed。
def test_rejects_invalid_grid_or_radial_contract(mutator):
    with pytest.raises(ValueError):
        _run_composition(mutator(_inputs()))
