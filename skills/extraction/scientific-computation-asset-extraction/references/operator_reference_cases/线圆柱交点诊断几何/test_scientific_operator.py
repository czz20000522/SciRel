# 测试结果：
# 工作目录：本参考案例目录
# 命令：python -m pytest test_scientific_operator.py -q
# 环境变量：无
# 结果：4 passed
# 对照依据：source-derived geometry fixture + root-selection invariant + boundary failure
# 源码对照状态：source_unavailable: full FIDASIM Fortran module is not built in this sandbox
# 证据来源：FIDASIM/src/fidasim.f90:8094-8137::line_cylinder_intersect
# 运行环境：Python 3.13.11; numpy 2.4.6; pytest 8.4.2

from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest


def _load_operator():
    path = Path(__file__).with_name("scientific_operator.py")
    spec = importlib.util.spec_from_file_location("line_cylinder_operator", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


op = _load_operator()


# 验证：从圆柱内部沿 +x 方向出发时，应选择最近的正交点参数。
def test_selects_nearest_positive_intersection():
    point, t = op.line_cylinder_intersection(
        line_point=np.array([0.0, 0.0, 1.0]),
        line_direction=np.array([1.0, 0.0, 0.5]),
        cylinder_point=np.array([2.0, 0.0, 0.0]),
    )

    assert t == pytest.approx(2.0)
    np.testing.assert_allclose(point, np.array([2.0, 0.0, 2.0]))
    assert np.hypot(point[0], point[1]) == pytest.approx(2.0)


# 验证：两个交点都在过去方向时，应按源码逻辑选择最大的非正参数。
def test_selects_largest_non_positive_when_no_future_hit():
    point, t = op.line_cylinder_intersection(
        line_point=np.array([3.0, 0.0, 0.0]),
        line_direction=np.array([1.0, 0.0, 0.0]),
        cylinder_point=np.array([2.0, 0.0, 0.0]),
    )

    assert t == pytest.approx(-1.0)
    np.testing.assert_allclose(point, np.array([2.0, 0.0, 0.0]))


# 验证：直线没有 xy 方向运动时，源码边界行为返回 t=0 和原始点。
def test_vertical_line_returns_zero_time_boundary_behavior():
    line_point = np.array([1.0, 1.0, 3.0])
    point, t = op.line_cylinder_intersection(
        line_point=line_point,
        line_direction=np.array([0.0, 0.0, 1.0]),
        cylinder_point=np.array([2.0, 0.0, 0.0]),
    )

    assert t == pytest.approx(0.0)
    np.testing.assert_allclose(point, line_point)


# 验证：输入必须是三维有限向量，避免几何含义不明确的广播计算。
def test_rejects_non_vector_input():
    with pytest.raises(ValueError, match="3-vector"):
        op.line_cylinder_intersection(
            line_point=np.array([0.0, 0.0]),
            line_direction=np.array([1.0, 0.0, 0.0]),
            cylinder_point=np.array([2.0, 0.0, 0.0]),
        )
