from scirel.kinetic.frank_egedal_pressure_closure import solve_frank_egedal_pressure_closure
import scirel
from _review_bindings import load_asset as _load_asset, load_graph as _load_graph, load_operator as _load_operator
import importlib.util
from pathlib import Path

import numpy as np
import pytest

from scirel.kinetic import frank_egedal_pressure_closure as graph
def _asset_loader(asset_ref):
    return _load_asset(asset_ref)

def _run_graph(inputs):
    return graph.run_graph(inputs, asset_loader=_asset_loader)


def _inputs(**parameter_overrides):
    params = {
        "p0": 8.0,
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


# 验证：YAML 必须显式声明 PFM 映射、节点与不可交换边，避免 graph.py 独占组合合同。
def test_yaml_declares_the_non_interchangeable_closure_pipeline():
    contract = Path(__file__).with_name("task_graph.yaml").read_text(encoding="utf-8")
    assert "primary_pfm_node: N4" in contract
    assert "- id: loss_cone_spectrum_port" in contract
    assert "id: hot_ion_moments" in contract
    assert "from: hot_ion_moments" in contract


# 验证：显式 degree 分支仍须产生有限、同 shape 的两个压力场和可审查闭合状态。
def test_returns_finite_grid_shaped_pressure_and_explicit_closure_state():
    result = _run_graph(_inputs())
    assert set(result) == {
        "p_parallel", "p_perp", "density", "electron_temperature", "closure_state"
    }
    assert result["p_parallel"].shape == (2, 2)
    assert result["p_perp"].shape == (2, 2)
    assert np.all(np.isfinite(result["p_parallel"]))
    assert np.all(np.isfinite(result["p_perp"]))
    assert np.all(result["p_parallel"] >= 0.0)
    assert np.all(result["p_perp"] >= 0.0)
    assert result["closure_state"]["degree_source"] == "caller_supplied"
    assert result["closure_state"]["normalization"] == "pressure moments referenced to hot_parallel(b=1); density referenced to hot_density(b=1)"


# 验证：热矩先以 b=1 归一化，随后才乘 p0，不能把径向或尺度因子混入归一化。
def test_b_equals_one_hot_shapes_are_normalized_before_pressure_scale():
    inputs = _inputs()
    inputs["B"] = np.ones((2, 2))
    inputs["psi"] = np.zeros((2, 2))
    result = _run_graph(inputs)
    # With zero gas/electron terms and radial_shape=1, p0 multiplies the b=1
    # shapes.  p_perp is intentionally referenced to p_parallel,0 and may
    # therefore differ from p_parallel at b=1.
    np.testing.assert_allclose(result["p_parallel"], np.full((2, 2), 8.0), rtol=1.0e-12)
    np.testing.assert_allclose(result["p_perp"], result["p_perp"][0, 0], rtol=1.0e-12)
    assert result["p_perp"][0, 0] > result["p_parallel"][0, 0]


# 验证：密度和电子温度输出的 nullable 合同与源 profile 的可选尺度语义一致。
def test_density_and_temperature_are_only_reported_when_configured():
    without_optional_fields = _run_graph(_inputs())
    assert without_optional_fields["density"] is None
    assert without_optional_fields["electron_temperature"] is None

    with_optional_fields = _run_graph(
        _inputs(background_density=3.0, hot_density_scale=2.0, electron_temperature=4.0)
    )
    assert with_optional_fields["density"].shape == (2, 2)
    np.testing.assert_allclose(with_optional_fields["electron_temperature"], 4.0)
    assert np.all(with_optional_fields["p_parallel"] >= with_optional_fields["density"] * 4.0)


def test_flux_relabeling_requires_matching_axis_and_edge_references():
    inputs = _inputs()
    baseline = solve_frank_egedal_pressure_closure(inputs)
    factor = 2.0 * np.pi
    relabeled = _inputs()
    relabeled["psi"] = factor * relabeled["psi"]
    relabeled["params"]["psi_axis"] *= factor
    relabeled["params"]["psi_edge"] *= factor
    changed = solve_frank_egedal_pressure_closure(relabeled)

    for key in ("p_parallel", "p_perp"):
        np.testing.assert_allclose(changed[key], baseline[key], rtol=1.0e-12)
    np.testing.assert_allclose(
        changed["closure_state"]["radial_shape"],
        baseline["closure_state"]["radial_shape"],
        rtol=1.0e-12,
    )

    relabeled["params"]["psi_edge"] /= factor
    unmatched = solve_frank_egedal_pressure_closure(relabeled)
    assert not np.allclose(unmatched["p_parallel"], baseline["p_parallel"])


# Eq. (19b) integrates the perpendicular moment only over v >= v_c.
def test_perpendicular_moment_is_zero_when_critical_speed_reaches_beam_speed():
    result = _run_graph(
        _inputs(
            vc_over_v0=1.0,
            legendre_degrees=[0.5],
            source_coefficients=[1.0],
        )
    )
    np.testing.assert_allclose(result["p_perp"], 0.0, atol=1.0e-14)


# 验证：未给 degree 时只从 emitted operator 读取损失锥谱，而不是读取原始 SciRel 源码。
def test_uses_emitted_loss_cone_asset_when_degrees_are_not_supplied():
    inputs = _inputs()
    del inputs["params"]["legendre_degrees"]
    del inputs["params"]["source_coefficients"]
    inputs["params"]["legendre_mode_count"] = 1
    inputs["params"]["legendre_spectrum_grid_points"] = 16
    result = _run_graph(inputs)
    assert result["closure_state"]["degree_source"] == "scirel.kinetic.loss_cone_spectrum"
    assert result["closure_state"]["degrees"].shape == (1,)


def test_mirror_ratio_precedes_turning_b_with_turning_fallback():
    baseline = _run_graph(_inputs(mirror_ratio=2.0))
    both = _run_graph(_inputs(mirror_ratio=2.0, turning_b=4.0))
    fallback_inputs = _inputs(turning_b=2.0)
    del fallback_inputs["params"]["mirror_ratio"]
    fallback = _run_graph(fallback_inputs)

    for result in (both, fallback):
        np.testing.assert_allclose(result["p_parallel"], baseline["p_parallel"])
        np.testing.assert_allclose(result["p_perp"], baseline["p_perp"])
        assert result["closure_state"]["xi_tp_mid"] == baseline["closure_state"]["xi_tp_mid"]


def test_requires_explicit_params_contract():
    inputs = _inputs()
    inputs.pop("params")
    with pytest.raises(ValueError, match="params is required"):
        _run_graph(inputs)


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
        _run_graph(mutator(_inputs()))
