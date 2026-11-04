"""Discrete velocity moment compensation for a supplied cylindrical mesh."""

from __future__ import annotations

import numpy as np

from .cylindrical_velocity_quadrature import make_cylindrical_velocity_quadrature

__all__ = ["compensate_velocity_slice", "build_compensated_shifted_maxwellian"]

HYDROGEN_MASS = 1.6726231e-27
CHARGE = 1.602177e-19


def _cell_fields(quadrature):
    required = (
        "dvr_vol",
        "dvx",
        "dvr",
        "volume",
        "speed_squared",
        "vx_pos_first_index",
        "vx_pos_last_index",
        "vx_neg_first_index",
        "vx_neg_last_index",
    )
    if isinstance(quadrature, dict):
        radial_measure = quadrature["radial_measure"]
        return {
            "dvr_vol": radial_measure,
            "dvx": quadrature["dvx"],
            "dvr": quadrature["vr_right"] - quadrature["vr_left"],
            "volume": quadrature["volume"],
            "speed_squared": quadrature["speed_squared"],
            "vx_pos_first_index": quadrature["positive_vx_first_index"],
            "vx_pos_last_index": quadrature["positive_vx_last_index"],
            "vx_neg_first_index": quadrature["negative_vx_first_index"],
            "vx_neg_last_index": quadrature["negative_vx_last_index"],
        }
    return {name: getattr(quadrature, name) for name in required}


def compensate_velocity_slice(
    f_slice,
    quadrature,
    vr,
    vx,
    vth,
    target_vx,
    target_energy,
    nb=1.0,
    assume_pos=True,
):
    """Adjust one slice toward target drift and energy moments.

    The caller supplies the output of :func:`make_cylindrical_velocity_quadrature`.
    The four sign combinations and optional signed-distribution cutoff follow
    the bounded source transcription; no iterative convergence claim is made.
    """
    fields = _cell_fields(quadrature)
    dvr_vol, dvx = fields["dvr_vol"], fields["dvx"]
    dvr, volume = fields["dvr"], fields["volume"]
    speed_squared = fields["speed_squared"]
    vr = np.asarray(vr)
    vx = np.asarray(vx)
    vr_n, vx_n = vr.size, vx.size
    vth_diffs = np.zeros((vr_n, vx_n, 2), dtype=float)
    vrvx_diffs = np.zeros((vr_n, vx_n, 2), dtype=float)
    signs = (1.0, -1.0)
    vx_moment = vth * np.sum(dvr_vol * np.matmul(f_slice, vx * dvx)) / nb
    energy_moment = vth**2 * np.sum(dvr_vol * np.matmul(speed_squared * f_slice, dvx)) / nb
    weighted = np.zeros((vr_n + 2, vx_n + 2), dtype=np.float64)
    rs, xs = slice(1, vr_n + 1), slice(1, vx_n + 1)
    weighted[rs, xs] = f_slice * volume / nb
    allow_neg = False
    if not assume_pos:
        cutoff = 1.0e-6 * np.max(weighted)
        small = np.where((np.abs(weighted) < cutoff) & (np.abs(weighted) > 0))
        if small[0].size:
            weighted[small] = 0.0
        if max(weighted[2, :]) <= 0:
            allow_neg = True
    vx_dist = np.zeros_like(weighted)
    vr_dist = np.zeros_like(weighted)
    vth_dist = np.zeros_like(weighted)
    vx_dist[rs, xs] = weighted[rs, xs] * (vx / dvx)
    vr_dist[rs, xs] = weighted[rs, xs] * (vr[:, None] / dvr[:, None])
    vth_dist[rs, xs] = weighted[rs, xs] / dvx
    rolled = np.roll(vth_dist, 1, axis=1) - vth_dist
    vth_diffs[:, :, 0] = rolled[rs, xs]
    rolled = -np.roll(vth_dist, -1, axis=1) + vth_dist
    vth_diffs[:, :, 1] = rolled[rs, xs]
    ps, pe = fields["vx_pos_first_index"], fields["vx_pos_last_index"]
    ns, ne = fields["vx_neg_first_index"], fields["vx_neg_last_index"]
    vrvx_diffs[:, ps + 1 : pe + 1, 0] = vx_dist[rs, ps + 1 : pe + 1] - vx_dist[rs, ps + 2 : pe + 2]
    vrvx_diffs[:, ps, 0] = -vx_dist[rs, ps + 1]
    vrvx_diffs[:, ne, 0] = vx_dist[rs, ne + 1]
    vrvx_diffs[:, ns:ne, 0] = -vx_dist[rs, ns + 2 : ne + 2] + vx_dist[rs, ns + 1 : ne + 1]
    vrvx_diffs[:, :, 0] += vr_dist[:vr_n, xs] - vr_dist[rs, xs]
    vrvx_diffs[:, ps + 1 : pe + 1, 1] = -vx_dist[rs, ps + 3 : pe + 3] + vx_dist[rs, ps + 2 : pe + 2]
    vrvx_diffs[:, ps, 1] = -vx_dist[rs, ps + 2]
    vrvx_diffs[:, ne, 1] = vx_dist[rs, ne]
    vrvx_diffs[:, ns:ne, 1] = vx_dist[rs, ns:ne] - vx_dist[rs, ns + 1 : ne + 1]
    vrvx_diffs[1:vr_n, :, 1] += vr_dist[2 : vr_n + 1, xs] - vr_dist[3 : vr_n + 2, xs]
    vrvx_diffs[0, :, 1] -= vr_dist[2, xs]
    if allow_neg:
        vrvx_diffs[0, :, 1] -= vr_dist[1, xs]
        vrvx_diffs[1, :, 1] += vr_dist[1, xs]
    weighted = weighted[rs, xs]
    tb1 = np.zeros(2, dtype=float)
    tb2 = np.zeros(2, dtype=float)
    do_break = False
    for ia in range(2):
        ta1 = vth * np.sum(np.matmul(vth_diffs[:, :, ia], vx))
        ta2 = vth**2 * np.sum(speed_squared * vth_diffs[:, :, ia])
        for ib in range(2):
            if tb1[ib] == 0:
                tb1[ib] = vth * np.sum(np.matmul(vrvx_diffs[:, :, ib], vx))
            if tb2[ib] == 0:
                tb2[ib] = vth**2 * np.sum(speed_squared * vrvx_diffs[:, :, ib])
            denom = ta2 * tb1[ib] - ta1 * tb2[ib]
            vrvx_scalar = 0.0
            vth_scalar = 0.0
            if denom != 0 and ta1 != 0:
                vrvx_scalar = (
                    ta2 * (target_vx - vx_moment) - ta1 * (target_energy - energy_moment)
                ) / denom
                vth_scalar = (target_vx - vx_moment - tb1[ib] * vrvx_scalar) / ta1
            do_break = (vth_scalar * signs[ia] > 0) and (vrvx_scalar * signs[ib] > 0)
            if do_break:
                break
        if do_break:
            break
    correction = vth_diffs[:, :, ia] * vth_scalar + vrvx_diffs[:, :, ib] * vrvx_scalar
    scale = 1.0
    if (not assume_pos) and (not allow_neg):
        nz = np.nonzero(weighted)
        if np.size(nz) > 0:
            scale = min(1 / np.max(-correction[nz] / weighted[nz]), 1)
    result = nb * (weighted + scale * correction) / volume
    return result, float(scale)


def build_compensated_shifted_maxwellian(
    *, vr, vx, temperatures_eV, shifts_ms, mu, molecularity, tnorm_eV
):
    """Build and moment-compensate shifted Maxwellian slices."""
    vr, vx = np.asarray(vr), np.asarray(vx)
    temperatures_eV, shifts_ms = np.asarray(temperatures_eV), np.asarray(shifts_ms)
    out = np.zeros((vr.size, vx.size, shifts_ms.size), dtype=float)
    thermal_speed = np.sqrt(2 * CHARGE * tnorm_eV / (mu * HYDROGEN_MASS))
    cells = make_cylindrical_velocity_quadrature(vr=vr, vx=vx)
    for k in range(shifts_ms.size):
        if temperatures_eV[k] <= 0:
            continue
        argument = (
            -(vr[:, None] ** 2 + (vx - shifts_ms[k] / thermal_speed) ** 2)
            * molecularity
            * tnorm_eV
            / temperatures_eV[k]
        )
        argument = np.where((argument > -80) & (argument < 0.0), argument, -80)
        out[:, :, k] = np.exp(argument)
        integral = np.sum(cells["radial_measure"] * np.matmul(out[:, :, k], cells["dvx"]))
        out[:, :, k] /= np.nansum(integral)
        target_energy = shifts_ms[k] ** 2 + 3 * CHARGE * temperatures_eV[k] / (
            molecularity * mu * HYDROGEN_MASS
        )
        out[:, :, k], _ = compensate_velocity_slice(
            out[:, :, k], cells, vr, vx, thermal_speed, shifts_ms[k], target_energy
        )
        out[:, :, k] /= np.sum(cells["radial_measure"] * np.matmul(out[:, :, k], cells["dvx"]))
    return out
