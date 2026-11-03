from __future__ import annotations

import numpy as np


def _as_matching_arrays(*values):
    arrays = [np.asarray(value, dtype=float) for value in values]
    shape = arrays[0].shape
    if any(array.shape != shape for array in arrays):
        raise ValueError("all inputs must have the same shape")
    if any(not np.all(np.isfinite(array)) for array in arrays):
        raise ValueError("all inputs must be finite")
    return arrays


def rz_to_rtheta(rho, z, rho_component, z_component):
    """把 Rho-Z 坐标中的矢量分量转换到极角坐标的 r/theta 分量。"""
    rho, z, rho_component, z_component = _as_matching_arrays(
        rho, z, rho_component, z_component
    )

    # 源码摘取：equilibrium helpers.py:290-298 的 R/Theta 与分量投影公式。
    radius = np.sqrt(rho**2 + z**2)
    theta = np.pi / 2.0 + np.arctan2(z, rho)
    sin_t = np.sin(theta)
    cos_t = np.cos(theta)
    r_component = rho_component * sin_t + z_component * cos_t
    theta_component = rho_component * cos_t - z_component * sin_t
    return radius, theta, r_component, theta_component
