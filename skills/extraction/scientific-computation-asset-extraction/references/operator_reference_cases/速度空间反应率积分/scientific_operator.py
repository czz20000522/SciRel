from __future__ import annotations

import numpy as np


ELEMENTARY_CHARGE_C = 1.602177e-19
HYDROGEN_MASS_KG = 1.6726231e-27


def _require_finite_positive(name, value):
    if not np.isfinite(value) or value <= 0.0:
        raise ValueError(f"{name} must be a positive finite value")


def _create_vr_vx_mesh(nv, temperatures):
    temperatures = np.asarray(temperatures, dtype=float)
    if temperatures.ndim != 1 or temperatures.size == 0:
        raise ValueError("temperatures must be a non-empty 1D array")
    if np.any(~np.isfinite(temperatures)) or np.any(temperatures <= 0.0):
        raise ValueError("temperatures must be positive finite values")

    # 源码摘取：KN1DPy/create_vr_vx_mesh.py:16-57 的速度网格构造。
    max_t = np.max(temperatures)
    min_t = np.min(temperatures)
    tnorm = np.nanmean(temperatures)
    vmax = 3.5
    if max_t - min_t <= 0.1 * max_t:
        v = np.arange(nv + 1) * vmax / nv
    else:
        g = 2.0 * nv * np.sqrt(min_t / max_t) / (1.0 - np.sqrt(min_t / max_t))
        b = vmax / (nv * (nv + g))
        a = g * b
        v = a * np.arange(nv + 1) + b * (np.arange(nv + 1) ** 2)
    vr = v[1:]
    vx = np.concatenate([-vr[::-1], vr])
    return vx, vr, tnorm


def _make_dvr_dvx(vr, vx):
    vr = np.asarray(vr, dtype=float)
    vx = np.asarray(vx, dtype=float)
    if vr.ndim != 1 or vx.ndim != 1 or vr.size < 2 or vx.size < 2:
        raise ValueError("vr and vx must be 1D arrays with at least two points")

    # 源码摘取：KN1DPy/make_dvr_dvx.py:17-123 的速度空间微分体积。
    nvr = vr.size
    nvx = vx.size
    extended_vr = np.append(vr, 2.0 * vr[-1] - vr[-2])
    vr_mid = np.concatenate(([0.0], 0.5 * (extended_vr + np.roll(extended_vr, -1))))
    vr_r = np.roll(vr_mid, -1)[:nvr]
    vr_l = vr_mid[:nvr]
    vr_2pi_dvr = np.pi * (vr_r**2 - vr_l**2)

    extended_vx = np.concatenate(([2.0 * vx[0] - vx[1]], vx, [2.0 * vx[-1] - vx[-2]]))
    vx_r = 0.5 * (np.roll(extended_vx, -1) + extended_vx)[1 : nvx + 1]
    vx_l = 0.5 * (np.roll(extended_vx, 1) + extended_vx)[1 : nvx + 1]
    dvx = vx_r - vx_l
    return vr_2pi_dvr, dvx


def maxwellian_averaged_sigma_v(
    particle_energy_ev,
    particle_mass_amu,
    target_temperature_ev,
    target_mass_amu,
    sigma_function,
    *,
    velocity_bins=100,
):
    """计算入射粒子与 Maxwellian 目标粒子的速度空间平均反应率 <sigma v>。"""
    particle_energy_ev = np.atleast_1d(np.asarray(particle_energy_ev, dtype=float))
    if particle_energy_ev.ndim != 1 or particle_energy_ev.size == 0:
        raise ValueError("particle_energy_ev must be a non-empty scalar or 1D array")
    if np.any(~np.isfinite(particle_energy_ev)) or np.any(particle_energy_ev <= 0.0):
        raise ValueError("particle_energy_ev must contain positive finite values")
    _require_finite_positive("particle_mass_amu", particle_mass_amu)
    _require_finite_positive("target_temperature_ev", target_temperature_ev)
    _require_finite_positive("target_mass_amu", target_mass_amu)
    if velocity_bins < 2:
        raise ValueError("velocity_bins must be at least 2")

    # 源码摘取：KN1DPy/make_sigmav.py:18-60 的主积分流程。
    temperature_range = np.sort(np.concatenate([particle_energy_ev, [target_temperature_ev]]))
    vx_b, vr_b, tnorm = _create_vr_vx_mesh(int(velocity_bins), temperature_range)
    vr_2pi_dvr, dvx_b = _make_dvr_dvx(vr_b, vx_b)

    vth = np.sqrt(
        2.0 * ELEMENTARY_CHARGE_C * tnorm / (target_mass_amu * HYDROGEN_MASS_KG)
    )
    normalized_particle_vx = np.array(
        [
            np.sqrt(2.0 * ELEMENTARY_CHARGE_C * energy / (particle_mass_amu * HYDROGEN_MASS_KG))
            / vth
            for energy in particle_energy_ev
        ]
    )

    fi_hat = np.zeros((vx_b.size, vr_b.size))
    for i in range(vr_b.size):
        fi_hat[:, i] = np.exp(-(vr_b[i] ** 2 + vx_b**2) * tnorm / target_temperature_ev)
    fi_hat = fi_hat / (vr_2pi_dvr * np.matmul(dvx_b, fi_hat)).sum()

    vrel = np.zeros((normalized_particle_vx.size, vx_b.size, vr_b.size))
    for k in range(normalized_particle_vx.size):
        for i in range(vr_b.size):
            vrel[k, :, i] = np.sqrt(vr_b[i] ** 2 + (vx_b - normalized_particle_vx[k]) ** 2)

    collision_energy_ev = (
        0.5
        * vth
        * vth
        * vrel
        * vrel
        * particle_mass_amu
        * HYDROGEN_MASS_KG
        / ELEMENTARY_CHARGE_C
    )
    sigma = np.asarray(sigma_function(collision_energy_ev), dtype=float)
    if sigma.shape != collision_energy_ev.shape:
        raise ValueError("sigma_function must return an array matching the input energy shape")
    if np.any(~np.isfinite(sigma)) or np.any(sigma < 0.0):
        raise ValueError("sigma_function must return non-negative finite cross sections")

    sigma_v = np.zeros(normalized_particle_vx.size)
    for k in range(normalized_particle_vx.size):
        sigma_v[k] = vth * (
            vr_2pi_dvr * np.matmul(dvx_b, sigma[k, :, :] * vrel[k, :, :] * fi_hat)
        ).sum()
    return sigma_v
