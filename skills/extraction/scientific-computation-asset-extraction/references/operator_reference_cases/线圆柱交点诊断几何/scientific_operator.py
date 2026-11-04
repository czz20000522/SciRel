from __future__ import annotations

import numpy as np


def _as_vector3(name, value):
    array = np.asarray(value, dtype=float)
    if array.shape != (3,):
        raise ValueError(f"{name} must be a 3-vector")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must contain finite values")
    return array


def line_cylinder_intersection(line_point, line_direction, cylinder_point):
    """计算直线与以 z 轴为轴的圆柱面的交点和参数 t。"""
    l0 = _as_vector3("line_point", line_point)
    direction = _as_vector3("line_direction", line_direction)
    p0 = _as_vector3("cylinder_point", cylinder_point)

    # 源码摘取：FIDASIM fidasim.f90:8094-8137 的半径、判别式和根选择逻辑。
    radius = float(np.sqrt(p0[0] * p0[0] + p0[1] * p0[1]))
    x0 = float(l0[0])
    y0 = float(l0[1])
    vx = float(direction[0])
    vy = float(direction[1])

    if vx == 0.0 and vy == 0.0:
        t = 0.0
    else:
        denom = vx * vx + vy * vy
        radicand = radius * radius * denom - (vy * x0 - vx * y0) ** 2
        if radicand < 0.0:
            t = 0.0
        else:
            root = np.sqrt(radicand)
            times = np.array(
                [
                    (-vx * x0 - vy * y0 - root) / denom,
                    (-vx * x0 - vy * y0 + root) / denom,
                ],
                dtype=float,
            )
            positive_times = times[times > 0.0]
            if positive_times.size > 0:
                t = float(np.min(positive_times))
            else:
                t = float(np.max(times[times <= 0.0]))

    point = l0 + direction * t
    return point, t
