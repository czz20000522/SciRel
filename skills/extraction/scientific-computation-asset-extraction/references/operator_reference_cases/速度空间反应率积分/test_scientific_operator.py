# 测试结果：
# 工作目录：本参考案例目录
# 命令：python -m pytest test_scientific_operator.py -q
# 环境变量：KN1DPY_SOURCE_ROOT=<KN1DPy source root>
# 结果：3 passed
# 对照依据：direct source routine parity + physical positivity + boundary failure
# 源码对照状态：direct_source_runnable
# 证据来源：KN1DPy/KN1DPy/make_sigmav.py:6-62::make_sigmav; KN1DPy/KN1DPy/create_vr_vx_mesh.py:16-57::create_vr_vx_mesh; KN1DPy/KN1DPy/make_dvr_dvx.py:17-123::make_dvr_dvx
# 数值差异：constant/energy-dependent cases max_abs_delta=0.000e+00; max_rel_delta=0.000e+00; l2_rel_delta=0.000e+00
# 运行环境：Python 3.13.11; numpy 2.4.6; pytest 8.4.2

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import numpy as np
import pytest


_SOURCE_ROOT_ENV = "KN1DPY_SOURCE_ROOT"
_SOURCE_ROOT_TEXT = os.environ.get(_SOURCE_ROOT_ENV)
if not _SOURCE_ROOT_TEXT:
    pytest.skip(
        f"{_SOURCE_ROOT_ENV} must point to the KN1DPy source root",
        allow_module_level=True,
    )

SOURCE_ROOT = Path(_SOURCE_ROOT_TEXT)
if not (SOURCE_ROOT / "KN1DPy" / "make_sigmav.py").exists():
    pytest.skip(
        f"{_SOURCE_ROOT_ENV} does not point to a KN1DPy source root",
        allow_module_level=True,
    )


def _load_operator():
    path = Path(__file__).with_name("scientific_operator.py")
    spec = importlib.util.spec_from_file_location("sigmav_operator", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_source_make_sigmav():
    sys.path.insert(0, str(SOURCE_ROOT))
    from KN1DPy.make_sigmav import make_sigmav

    return make_sigmav


op = _load_operator()
source_make_sigmav = _load_source_make_sigmav()


def _diff_metrics(actual, expected):
    actual_arr = np.asarray(actual, dtype=float)
    expected_arr = np.asarray(expected, dtype=float)
    delta = actual_arr - expected_arr
    denom = np.maximum(np.abs(expected_arr), 1.0e-300)
    max_abs = float(np.max(np.abs(delta)))
    max_rel = float(np.max(np.abs(delta) / denom))
    l2_rel = float(np.linalg.norm(delta) / max(np.linalg.norm(expected_arr), 1.0e-300))
    return max_abs, max_rel, l2_rel


# 验证：常数截面下，算子输出必须与 KN1DPy 源函数在同一输入上逐项一致。
def test_matches_source_for_constant_cross_section():
    energies = np.array([10.0, 50.0])

    def sigma_function(energy_ev):
        return np.ones_like(energy_ev, dtype=float) * 1.0e-20

    actual = op.maxwellian_averaged_sigma_v(energies, 1.0, 20.0, 1.0, sigma_function)
    expected = source_make_sigmav(energies, 1.0, 20.0, 1.0, sigma_function)

    max_abs, max_rel, l2_rel = _diff_metrics(actual, expected)
    print(
        "constant source parity metrics: "
        f"max_abs_delta={max_abs:.3e}, max_rel_delta={max_rel:.3e}, "
        f"l2_rel_delta={l2_rel:.3e}"
    )
    np.testing.assert_allclose(actual, expected, rtol=1e-12, atol=0.0)
    assert max_abs <= 1.0e-30
    assert max_rel <= 1.0e-12
    assert np.all(actual > 0.0)


# 验证：能量相关截面下，速度空间积分仍与源函数保持数值一致。
def test_matches_source_for_energy_dependent_cross_section():
    energies = np.array([5.0, 25.0, 80.0])

    def sigma_function(energy_ev):
        return 2.0e-22 * (1.0 + 0.015 * energy_ev)

    actual = op.maxwellian_averaged_sigma_v(energies, 2.0, 35.0, 1.0, sigma_function)
    expected = source_make_sigmav(energies, 2.0, 35.0, 1.0, sigma_function)

    max_abs, max_rel, l2_rel = _diff_metrics(actual, expected)
    print(
        "energy-dependent source parity metrics: "
        f"max_abs_delta={max_abs:.3e}, max_rel_delta={max_rel:.3e}, "
        f"l2_rel_delta={l2_rel:.3e}"
    )
    np.testing.assert_allclose(actual, expected, rtol=1e-12, atol=0.0)
    assert max_abs <= 1.0e-30
    assert max_rel <= 1.0e-12
    assert np.all(np.isfinite(actual))


# 验证：目标温度必须为正；否则 Maxwellian 归一化和热速度没有物理意义。
def test_rejects_non_positive_target_temperature():
    with pytest.raises(ValueError, match="target_temperature_ev"):
        op.maxwellian_averaged_sigma_v(
            np.array([10.0]),
            1.0,
            0.0,
            1.0,
            lambda energy_ev: np.ones_like(energy_ev),
        )
