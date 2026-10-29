import json
import math
import time
from pathlib import Path

import numpy as np


def _peak(k, g):
    eligible = np.arange(len(k) - 1)[k[:-1] <= 0.8]
    ratios = np.asarray(g, float) / np.asarray(k, float)
    j = int(eligible[np.argmax(ratios[eligible])])
    jmax = j + 1
    if j == 0 or j == len(k) - 1:
        return float(k[j]), float(ratios[j]), jmax
    km, kp = k[j - 1], k[j + 1]
    D = kp - km
    u = (k[j] - km) / D
    f0, f1, f2 = ratios[j - 1:j + 2]
    if f0 >= f1:
        t = 0.0
    else:
        B = (f1 - f0 * (1 - u * u) - f2 * u * u) / (u - u * u)
        C = f2 - f0 - B
        tstar = -B / (2 * C) if C != 0 else 1.0
        t = min(max(tstar, 0.0), 1.0)
    kval = km + D * t
    return float(kval), float(f0 + B * t + C * t * t) if j > 0 and f0 < f1 else float(ratios[j]), jmax


def _geometry(inp, k, width, shear, sat_rule, kmax, vzf):
    g = inp["geometry"]
    nx = 2 * int(g["nxgrid"]) - 1
    xgrid = np.polynomial.hermite.hermgauss(nx)[0]
    xgrid[nx // 2] = 0.0
    r, Rmaj, q, s = g["rmin_a"], g["rmaj_a"], g["q"], g["magnetic_shear"]
    eps = r / Rmaj
    G = float(shear)
    first = np.asarray(inp["first_growth_cs_over_a"], float)
    gref = float(first[np.argmax(first[:, 0] / k), 0])
    ky_i = k
    wE = min(ky_i / .3, 1.0) * G / gref
    if sat_rule == 1:
        kxe = -(.53 * G / gref + .25 * wE * math.tanh((.69 * wE) ** 6))
        kxe = float(np.clip(kxe, -1.45, 1.45))
    elif abs(kmax * vzf * G) > 1e-8:
        kxe = -.32 * (k / kmax) ** .3 * G / (k * vzf)
        kxe = float(np.clip(kxe, -1.6, 1.6))
    else:
        kxe = 0.0
    theta = width * xgrid
    Rx = 1 + eps * np.cos(theta)
    Bx = 1 / Rx
    kxx = -s * (theta - g["theta0"]) + g["pressure_alpha"] * np.sin(theta) - kxe
    wdx = (np.cos(theta) - np.sin(theta) * kxx) / Rx
    b0x, b2x = 1 + kxx * kxx, Bx * Bx
    cx_tor_par, cx_tor_per, cx_par_par = Rmaj * Rx, -r / q, Bx
    theta_max = min(g["theta_trapped"] * width * math.pi / math.sqrt(2), math.pi)
    Bmax, Bmin = 1 / (1 + eps * math.cos(theta_max)), 1 / (1 + eps)
    u = np.cos(math.pi * (2 * np.arange(1, nx + 1) - 1) / (2 * nx))
    th = u * theta_max
    bi = 1 / (1 + eps * np.cos(th))
    wi = np.sqrt(1 - u * u) * np.exp(-(th / width) ** 2)
    ft = float(np.sum(wi * np.sqrt(np.maximum(0, 1 - bi / Bmax))) / np.sum(wi))
    ft = max(ft, g["ft_min"])
    # The prescribed circular averages use a periodic endpoint trapezoid rule.
    ang = np.linspace(0, 2 * math.pi, 2 * nx + 1)
    Rxa = 1 + eps * np.cos(ang)
    Bxa = 1 / Rxa
    trap = lambda y: float(np.trapezoid(y, ang) / (2 * math.pi))
    B2, R2, RBt, Bave, Btave = trap(Bxa * Bxa), Rmaj ** 2 * trap(Rxa * Rxa), Rmaj, trap(Bxa), trap(Rxa)
    Bgeo0 = g["f_RBt_over_aBunit"] / Rmaj
    scalars = [ft, ft, ft, B2, R2, RBt, Bave, Btave, 1.0, r / (q * (Rmaj + r)), Bgeo0, Bgeo0, 1.0, 1.0, 1.0, 1.0, kxe]
    xarr = np.column_stack((Bx, kxx, wdx, Bx, b2x, cx_tor_par, cx_tor_per + 0 * Bx, cx_par_par))
    return {"kxe": kxe, "scalars": scalars, "xarr": xarr, "ft": ft}


def _weighted_mix(k, values, k0):
    lo, hi = k[0], k[-1]
    if len(k) < 2 or hi == lo:
        return float(np.asarray(values, dtype=float)[-1])
    if k0 <= lo:
        lo = k[0]
    grid = np.unique(np.r_[k, np.linspace(lo, hi, 257)])
    vals = np.interp(grid, k, values)
    W = math.sqrt(3) * k0 * k0 / (k0 * k0 + 3 * (grid - k0) ** 2)
    return float(np.trapezoid(vals * W, grid) / np.trapezoid(W, grid))


def _transition(x, yi, yt):
    if x < .8:
        return yi
    if x > 1:
        return yt
    return yi + (x - .8) / .2 * (yt - yi)


def _scenario(inp, sc):
    k = np.asarray(inp["ky_rhos"], float)
    first = np.asarray(inp["first_growth_cs_over_a"], float)
    second = np.asarray(inp["second_growth_cs_over_a"], float)
    width = np.asarray(inp["width_radian"], float)
    if not isinstance(sc, dict) or not {"id", "sat_rule", "exb_shear_a_over_cs", "energy_weight_variant"}.issubset(sc):
        raise ValueError("each scenario needs id, sat_rule, exb_shear_a_over_cs and energy_weight_variant")
    sat = int(sc["sat_rule"]); shear = float(sc["exb_shear_a_over_cs"])
    if sat not in (1, 2, 3) or not np.isfinite(shear) or sc["energy_weight_variant"] not in ("ITG-and-TEM", "transition", "default"):
        raise ValueError("scenario controls are invalid")
    fp_k, fp_v, fp_j = _peak(k, first[:, 0])
    gref = first[fp_j - 1, 0]
    geom = [_geometry(inp, ki, wi, shear, sat, fp_k, fp_v) for ki, wi in zip(k, width)]
    kxe = np.array([g["kxe"] for g in geom])
    gnet = second[:, 0] / (1 + np.abs((1.15 if sat == 1 else 1.21) * kxe) ** (4 if sat == 1 else 2))
    if sat == 1:
        fk, fv, fj = _peak(k, gnet)
    else:
        fk, fv, fj = fp_k, fp_v * gnet[fp_j - 1] / max(second[fp_j - 1, 0], 1e-10), fp_j
    if sat == 1:
        kmax, vzf, jmax = fk, fv, fj
    else:
        kmax, vzf, jmax = fp_k, fv, fp_j
    gm = vzf * kmax
    if sat == 1:
        w = k.copy(); h = kxe.copy(); cnorm, cz1, cz2, measure, ketg, ay = 14.63, .9, 1.0, 1.0, 1.05, .56
    else:
        kcut = .76 * fp_k; w = np.where(k < kcut, kcut, kcut + 1.22 * (k - kcut)); h = np.divide(kxe * k, w, out=np.zeros_like(k), where=w != 0)
        cnorm, cz1, cz2, measure, ketg, ay = 3.55, 0.0, 1.05, 1 / fp_k, 1000.0, 1.0
    if sat == 1:
        raw = np.where(k < kmax, np.maximum(gnet - cz1 * (kmax - k) * vzf, 0), cz2 * gm + np.maximum(gnet - cz2 * vzf * k, 0))
    else:
        raw = np.where(k < kmax, gnet, gm + np.maximum(gnet - cz2 * vzf * k, 0))
    mix = raw.copy()
    for j in range(jmax + 1, len(k)):
        mix[j] = _weighted_mix(k[jmax + 1:], raw[jmax + 1:], k[j])
    gmode = second.copy()
    P = np.zeros((len(k), 2))
    qla = np.ones((len(k), 2, 3))
    qlflux = np.asarray(inp["QL_flux_weights"], float).copy()
    qlmoment = np.asarray(inp["QL_moment_weights"], float)
    qlfield = np.asarray(inp["QL_field_weights"], float)
    ratio = np.zeros((len(k), 2))
    for i in range(len(k)):
        for m in range(2):
            if sc["energy_weight_variant"] == "transition":
                qlflux[i, 0, m, 0, 1] = inp["transition_electron_to_ion_ES_energy_ratio"][m] * qlflux[i, 1, m, 0, 1]
            ratio[i, m] = abs(qlflux[i, 0, m, 0, 1] / max(np.sum(qlflux[i, 1, m, :, 1]), 1e-30))
    x_at = np.array([.5 if kmax <= k[0] else np.interp(kmax, k, ratio[:, m]) for m in range(2)])
    for m in range(2):
        if sat == 3:
            qla[:, m, 0] = 2 * np.array([_transition(x_at[m], 1.1, .6)] * len(k))
            qla[:, m, 1] = 2 * np.array([_transition(x_at[m], .75, .6)] * len(k))
            qla[:, m, 2] = 1.6
        for i, ki in enumerate(k):
            gj, gjm = second[i, 0], second[i, m]
            geff = 0.0 if gj <= 1e-10 else mix[i] * (gjm / gj) ** 2
            if ki > ketg:
                geff *= math.sqrt(ki / ketg)
            P[i, m] = measure * cnorm * (geff / (w[i] * ki) / (1 + ay * h[i] ** 2)) ** 2
            if sat == 3:
                K, Gm = fp_k, fp_v * fp_k
                x = x_at[m]; YI = 3.3 * Gm ** 2 / K ** 5; YT = 12.7 * Gm ** 2 / K ** 4; Ym = _transition(x, YI, YT)
                # Preserve the native low/high connection shape while keeping the supplied response table explicit.
                if ki <= 1.0:
                    P[i, m] = max(P[i, m] * (Ym / max(YI, 1e-30)), 0.0)
    field = np.zeros((len(k), 2, 4)); moments = np.zeros((len(k), 2, 2, 4)); flux = np.zeros((len(k), 2, 2, 3, 5))
    for i in range(len(k)):
        for m in range(2):
            field[i, m] = [P[i, m], P[i, m], (qlfield[i, m, 2] ** 2) * P[i, m], (qlfield[i, m, 3] ** 2) * P[i, m]]
            moments[i, :, m] = qlmoment[i, :, m] * P[i, m]
            flux[i, :, m] = qlflux[i, :, m] * P[i, m]
            if sat == 3:
                moments[i, 0, m, 0] *= qla[i, m, 0]; moments[i, 1, m, 0] *= qla[i, m, 0]
                moments[i, :, m, 1] *= qla[i, m, 1]; moments[i, :, m, 2:] *= qla[i, m, 2]
                flux[i, :, m, :, 0] *= qla[i, m, 0]; flux[i, :, m, :, 1] *= qla[i, m, 1]; flux[i, :, m, :, 2:] *= qla[i, m, 2]
    interval = np.zeros((len(k), 2, 3, 5));
    interval[0] = k[0] * np.sum(flux[0], axis=1)
    for i in range(1, len(k)):
        D = math.log(k[i] / k[i - 1]) / (k[i] - k[i - 1]); a = k[i - 1] * (k[i] * D - 1); b = k[i] * (1 - k[i - 1] * D)
        interval[i] = a * np.sum(flux[i - 1], axis=1) + b * np.sum(flux[i], axis=1)
    total = np.sum(interval, axis=0)
    xgrid = np.polynomial.hermite.hermgauss(31)[0]
    xgrid[15] = 0.0
    return {"id": sc["id"], "sat_rule": sat, "shear": shear, "first_peak": [fp_v, fp_k, fp_j], "final_peak": [vzf, kmax, jmax], "peak_fields": [vzf, kmax, jmax], "native_shift_kx_over_ky": kxe.tolist(), "geometry_shift_signBt": kxe.tolist(), "x_grid": xgrid.tolist(), "geometry_scalars": np.asarray([g["scalars"] for g in geom]).tolist(), "geometry_xgrid": np.asarray([g["xarr"] for g in geom]).tolist(), "field_spectrum": field.tolist(), "moment_intensity": moments.tolist(), "flux_spectrum_GB": flux.tolist(), "flux_interval_contributions_GB": interval.tolist(), "total_flux_GB": total.tolist(), "checks": {"finite": bool(np.isfinite(field).all() and np.isfinite(moments).all() and np.isfinite(flux).all()), "nonzero_field": bool(np.any(field > 0)), "signed_flux_present": bool(np.any(flux < 0)), "shapes": {"field_spectrum": list(field.shape), "moment_intensity": list(moments.shape), "flux_spectrum_GB": list(flux.shape), "flux_interval_contributions_GB": list(interval.shape), "total_flux_GB": list(total.shape)}}}



def simulate_sat123(inputs: dict) -> dict:
    """Compute all declared SAT1/SAT2/SAT3 scenarios from supplied responses."""
    if not isinstance(inputs, dict) or not isinstance(inputs.get("scenarios"), list):
        raise ValueError("inputs.scenarios must be a list")
    required = {
        "ky_rhos", "first_growth_cs_over_a", "second_growth_cs_over_a", "width_radian",
        "geometry", "QL_field_weights", "QL_moment_weights", "QL_flux_weights",
        "transition_electron_to_ion_ES_energy_ratio",
    }
    missing = sorted(required.difference(inputs))
    if missing:
        raise ValueError(f"inputs missing required fields: {', '.join(missing)}")
    k = np.asarray(inputs["ky_rhos"], dtype=float)
    first = np.asarray(inputs["first_growth_cs_over_a"], dtype=float)
    second = np.asarray(inputs["second_growth_cs_over_a"], dtype=float)
    width = np.asarray(inputs["width_radian"], dtype=float)
    if k.ndim != 1 or k.size < 3 or np.any(~np.isfinite(k)) or np.any(k <= 0) or np.any(np.diff(k) <= 0):
        raise ValueError("ky_rhos must be a finite strictly increasing positive vector")
    if first.shape != (k.size, 2) or second.shape != (k.size, 2) or width.shape != (k.size,):
        raise ValueError("growth tables and width_radian must align with ky_rhos")
    if not np.all(np.isfinite(first)) or not np.all(np.isfinite(second)) or not np.all(np.isfinite(width)) or np.any(width <= 0):
        raise ValueError("growth tables and widths must be finite with positive widths")
    scenarios = [_scenario(inputs, scenario) for scenario in inputs["scenarios"]]
    return {
        "schema": "scirel.multiscale-sat123.v1",
        "scenario_order": [item["id"] for item in scenarios],
        "scenarios": scenarios,
    }

__all__ = ["simulate_sat123"]
