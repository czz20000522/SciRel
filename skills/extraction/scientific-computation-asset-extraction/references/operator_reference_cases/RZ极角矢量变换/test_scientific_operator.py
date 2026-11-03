# 测试结果：
# 工作目录：本参考案例目录
# 命令：python -m pytest test_scientific_operator.py -q
# 环境变量：无
# 结果：3 passed
# 对照依据：source-derived formula + orthogonal projection invariant + boundary failure
# 源码对照状态：source_unavailable: helpers.py imports SciPy at module import time; fallback oracle used
# 证据来源：pleiades/pleiades/analysis/helpers.py:290-298::transform_to_rtheta
# 运行环境：Python 3.13.11; numpy 2.4.6; pytest 8.4.2

from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest


def _load_operator():
    path = Path(__file__).with_name("scientific_operator.py")
    spec = importlib.util.spec_from_file_location("rz_theta_operator", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


op = _load_operator()


# 验证：代表性点上，输出必须符合源码行号中的 R/Theta 和矢量投影公式。
def test_rz_to_rtheta_matches_source_derived_formula():
    rho = np.array([1.0, 0.0, -2.0])
    z = np.array([0.0, 2.0, 2.0])
    rho_component = np.array([3.0, 4.0, -1.0])
    z_component = np.array([5.0, -2.0, 0.5])

    radius, theta, r_component, theta_component = op.rz_to_rtheta(
        rho, z, rho_component, z_component
    )

    expected_radius = np.sqrt(rho**2 + z**2)
    expected_theta = np.pi / 2.0 + np.arctan2(z, rho)
    expected_r = rho_component * np.sin(expected_theta) + z_component * np.cos(
        expected_theta
    )
    expected_theta_component = rho_component * np.cos(
        expected_theta
    ) - z_component * np.sin(expected_theta)

    np.testing.assert_allclose(radius, expected_radius)
    np.testing.assert_allclose(theta, expected_theta)
    np.testing.assert_allclose(r_component, expected_r)
    np.testing.assert_allclose(theta_component, expected_theta_component)


# 验证：该变换是二维正交基投影，转换前后矢量模长应保持不变。
def test_projection_preserves_vector_magnitude():
    rho = np.array([1.5, -3.0, 2.5])
    z = np.array([2.0, 1.0, -4.0])
    rho_component = np.array([0.2, -1.1, 3.0])
    z_component = np.array([4.0, 2.5, -0.75])

    _, _, r_component, theta_component = op.rz_to_rtheta(
        rho, z, rho_component, z_component
    )

    before = rho_component**2 + z_component**2
    after = r_component**2 + theta_component**2
    np.testing.assert_allclose(after, before)


# 验证：数组形状不一致时必须显式失败，避免不同网格点被错误配对。
def test_rejects_mismatched_shapes():
    with pytest.raises(ValueError, match="same shape"):
        op.rz_to_rtheta(
            np.array([0.0, 1.0]),
            np.array([0.0]),
            np.array([1.0, 1.0]),
            np.array([1.0, 1.0]),
        )
