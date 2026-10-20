import inspect

from scirel.diagnostics.equilibrium_synthesis_diagnostics import synthesize_equilibrium_diagnostics
import scirel
from _review_bindings import load_asset as _load_asset, load_composition as _load_composition, load_callable as _load_callable
from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest

from scirel.diagnostics import equilibrium_synthesis_diagnostics as composition
def _asset_loader(asset_ref):
    return _load_asset(asset_ref)

def _run(inputs):
    return composition.run_composition(inputs, asset_loader=_asset_loader)


def test_public_callable_documents_the_catalog_contract():
    text = inspect.getdoc(synthesize_equilibrium_diagnostics) or ""
    assert "observations" in text
    assert "flux_loops" in text
    assert "FloatingPointError" in text


def test_public_scirel_injects_declared_sampler_dependency():

    result = synthesize_equilibrium_diagnostics(_inputs())
    np.testing.assert_allclose(result["flux_loops"], [1.5])


def _inputs():
    R, Z = np.meshgrid(np.array([0.0, 1.0]), np.array([0.0, 1.0]))
    return {
        "R": R,
        "Z": Z,
        "equilibrium": {
            "psi": R + 2.0 * Z,
            "psi_unit": "Wb/rad",
            "profile_units": {"p_parallel":"Pa", "p_perp":"Pa", "density":"m^-3", "electron_temperature":"eV"},
            "profiles": {
                "p_parallel": 10.0 + R + Z,
                "p_perp": 20.0 + 2.0 * R + Z,
                "density": 3.0 + R,
                "electron_temperature": 4.0 + Z,
            },
        },
        "observations": {
            "flux_loops": {"points": np.array([[0.5, 0.5]]), "quantity":"raw_psi", "unit":"Wb/rad"},
            "thomson": {"points": np.array([[0.5, 0.5]]), "p_parallel":{"unit":"Pa"}, "p_perp":{"unit":"Pa"}, "density":{"unit":"m^-3"}, "electron_temperature":{"unit":"eV"}},
        },
    }


# 验证：YAML 必须公开 N9、两个观测输出及对 emitted sampler 的显式依赖。
def test_yaml_declares_observer_only_sampling_contract():
    contract = Path(__file__).with_name("composition.yaml").read_text(encoding="utf-8")
    assert "primary_pfm_node: N9" in contract
    assert "id: flux_loop_sampling" in contract
    assert "id: thomson_sampling" in contract
    assert "scirel.geometry.bilinear_grid_sampling" in contract


# 验证：flux 分支读取 psi，结果按 source 的 flux-first key 顺序出现。
def test_predicts_flux_loop_from_equilibrium_flux_only():
    inputs = _inputs()
    inputs["observations"] = {"flux_loops": {"points": np.array([[0.5, 0.5]]), "quantity":"raw_psi", "unit":"Wb/rad"}}
    result = _run(inputs)
    assert list(result) == ["flux_loops", "units"]
    np.testing.assert_allclose(result["flux_loops"], [1.5])


# 验证：Thomson 压强为必需端口，密度和电子温度仅在 source profile 实际提供时加入。
def test_predicts_required_and_optional_thomson_fields():
    result = _run(_inputs())
    assert list(result) == ["flux_loops", "thomson", "units"]
    np.testing.assert_allclose(result["thomson"]["p_parallel"], [11.0])
    np.testing.assert_allclose(result["thomson"]["p_perp"], [21.5])
    np.testing.assert_allclose(result["thomson"]["density"], [3.5])
    np.testing.assert_allclose(result["thomson"]["electron_temperature"], [4.5])
    inputs = _inputs()
    inputs["equilibrium"]["profiles"]["density"] = None
    inputs["equilibrium"]["profiles"]["electron_temperature"] = None
    # Optional source profiles need not exist only when those channels were not requested.
    del inputs["observations"]["thomson"]["density"]
    del inputs["observations"]["thomson"]["electron_temperature"]
    thomson = _run(inputs)["thomson"]
    assert set(thomson) == {"p_parallel", "p_perp"}


# 验证：空和未知 observations 是配置错误，不再静默返回空 mapping。
def test_empty_or_unknown_observations_return_empty_mapping():
    inputs = _inputs()
    inputs["observations"] = {}
    with pytest.raises(ValueError):
        _run(inputs)
    inputs["observations"] = {"unknown": {"points": np.array([[0.5, 0.5]])}}
    with pytest.raises(ValueError):
        _run(inputs)


@pytest.mark.parametrize(
    "mutator",
    [
        lambda value: {**value, "observations": {"flux_loops": {"points": np.array([[2.0, 0.5]])}}},
        lambda value: {**value, "equilibrium": {"profiles": value["equilibrium"]["profiles"]}},
        lambda value: {**value, "equilibrium": {"psi": value["equilibrium"]["psi"], "profiles": {"p_perp": value["equilibrium"]["profiles"]["p_perp"]}}},
    ],
)
# 验证：越界点和缺少必需 state port 不能被图静默填充或外推。
def test_rejects_out_of_domain_point_or_missing_required_equilibrium_port(mutator):
    with pytest.raises(ValueError):
        _run(mutator(_inputs()))


# 验证：observer-only 图不得改变 caller-owned equilibrium arrays 或嵌套 mapping 值。
def test_diagnostics_do_not_mutate_equilibrium_state():
    inputs = _inputs()
    before = deepcopy(inputs["equilibrium"])
    _run(inputs)
    for key, before_value in before.items():
        if isinstance(before_value, dict):
            for profile_key, profile_before in before_value.items():
                np.testing.assert_array_equal(inputs["equilibrium"][key][profile_key], profile_before)
        else:
            np.testing.assert_array_equal(inputs["equilibrium"][key], before_value)
