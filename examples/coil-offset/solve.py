#!/usr/bin/env python3
"""Vacuum field of two thin coaxial rings: nominal versus upper ring raised 2 cm.

Physics: each ring contributes an elliptic-integral flux function psi = R*A_phi,
B_R = -(1/R) dpsi/dZ and B_Z = (1/R) dpsi/dR. Fields add linearly. See method.md.

Run from a checkout: PYTHONPATH=src python examples/coil-offset/solve.py
Full-precision numbers go to data/; the report only reads those files.
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import numpy as np
from scirel.field import circular_filament_green_response, superpose_current_green_field

HERE = Path(__file__).resolve().parent
MU0 = 4e-7 * math.pi
RADIUS = 0.50          # m
CURRENT = 1000.0       # A per ring, along +phi
STATES = {"nominal": (-0.25, 0.25), "offset": (-0.25, 0.27)}
# Explanatory only: the offset equals a common shift plus a wider gap.
AUXILIARY = {"shift_only": (-0.24, 0.26), "gap_only": (-0.26, 0.26)}
GRID_R = (0.02, 0.05, 0.10, 0.15, 0.20)
GRID_Z = (-0.20, -0.10, 0.0, 0.10, 0.20)
REFERENCE = (0.02, 0.0)
FLUX_POINT = (0.10, 0.0)
TIE_RTOL = 1e-9


def field(rings, points, *, radius=RADIUS, current=CURRENT):
    """Superpose ring responses at (R, Z) points; psi in Wb/rad, Br and Bz in T."""
    points = np.asarray(points, dtype=float)
    per_amp = [circular_filament_green_response([[radius, z, 1.0]], points) for z in rings]
    stack = {key: np.stack([ring[key] for ring in per_amp], axis=1) for key in ("gpsi", "gBR", "gBZ")}
    currents = np.full(len(rings), float(current))
    total = superpose_current_green_field(currents, stack["gpsi"], stack["gBR"], stack["gBZ"])
    psi, br, bz = (np.asarray(total[key], dtype=float) for key in ("psi", "BR", "BZ"))
    return {"psi": psi, "Br": br, "Bz": bz, "per_amp": stack}


def biot_savart(rings, points, *, radius=RADIUS, current=CURRENT, nodes=4096):
    """Direct line integral of Biot-Savart and of A_phi, independent of the Green kernel."""
    points = np.asarray(points, dtype=float)
    theta = 2 * np.pi * (np.arange(nodes) + 0.5) / nodes
    weight = 2 * np.pi / nodes
    out = {"psi": np.zeros(len(points)), "Br": np.zeros(len(points)), "Bz": np.zeros(len(points))}
    for z0 in rings:
        for index, (r, z) in enumerate(points):
            dx, dy, dz = r - radius * np.cos(theta), -radius * np.sin(theta), z - z0 + 0 * theta
            dist3 = (dx * dx + dy * dy + dz * dz) ** 1.5
            lx, ly = -radius * np.sin(theta), radius * np.cos(theta)
            factor = MU0 * current / (4 * np.pi) * weight
            # dB = (mu0 I / 4 pi) dl x d / |d|^3, evaluated in the phi=0 plane where x=R.
            out["Br"][index] += factor * np.sum(ly * dz / dist3)
            out["Bz"][index] += factor * np.sum((lx * dy - ly * dx) / dist3)
            # A_phi is the y component of (mu0 I / 4 pi) dl / |d|.
            out["psi"][index] += r * factor * np.sum(ly / np.sqrt(dist3 ** (2 / 3)))
    return out


def on_axis(rings, z, *, radius=RADIUS, current=CURRENT):
    """Textbook on-axis field of a sum of rings, B = mu0 I a^2 / (2 (a^2+dz^2)^(3/2))."""
    z = np.asarray(z, dtype=float)
    return sum(MU0 * current * radius**2 / (2 * (radius**2 + (z - z0) ** 2) ** 1.5) for z0 in rings)


def axis_curvature(separation, *, radius=RADIUS, current=CURRENT):
    """d2Bz/dZ2 at the midpoint of a coaxial pair; zero at the Helmholtz spacing."""
    return 3 * MU0 * current * radius**2 * (separation**2 - radius**2) / (radius**2 + separation**2 / 4) ** 3.5


def axial_shape(rings):
    """Dense on-axis profile, descriptive only: midpoint value and the highest value within |Z|<=0.10 m."""
    z = np.linspace(-0.10, 0.10, 2001)
    bz = on_axis(rings, z)
    midpoint = float(on_axis(rings, sum(rings) / 2))
    return {"midpoint_T": midpoint, "max_T": float(bz.max()), "min_T": float(bz.min()),
            "dip_percent": 100 * (float(bz.max()) / midpoint - 1), "curvature_T_per_m2": axis_curvature(rings[1] - rings[0])}


def grid_points():
    return np.array([(r, z) for r in GRID_R for z in GRID_Z])


def is_center(point):
    return point[0] <= 0.10 + 1e-12 and abs(point[1]) <= 0.10 + 1e-12


def evaluate(rings):
    points = grid_points()
    result = field(rings, points)
    br, bz = result["Br"], result["Bz"]
    return {
        "R": points[:, 0], "Z": points[:, 1], "Br": br, "Bz": bz, "Bmag": np.hypot(br, bz),
        "psi": result["psi"], "tilt": np.abs(np.arctan2(br, bz)),
    }


def _extreme_points(values, mask, points):
    values = np.where(mask, values, -np.inf)
    largest = float(values.max())
    ties = np.isclose(values, largest, rtol=TIE_RTOL, atol=0.0)
    return largest, [[float(points[i, 0]), float(points[i, 1])] for i in np.flatnonzero(ties)]


def metrics(rings):
    state = evaluate(rings)
    points = np.column_stack((state["R"], state["Z"]))
    center = np.array([is_center(p) for p in points])
    index = int(np.flatnonzero((points == REFERENCE).all(axis=1))[0])
    bref = float(state["Bz"][index])
    uniformity, u_at = _extreme_points(np.abs(state["Bz"] / bref - 1.0), center, points)
    tilt, tilt_at = _extreme_points(state["tilt"], center, points)
    flux_index = int(np.flatnonzero((points == FLUX_POINT).all(axis=1))[0])
    psi_point = float(state["psi"][flux_index])
    return {
        "rings_z_m": list(rings), "separation_m": rings[1] - rings[0], "midpoint_z_m": sum(rings) / 2,
        "bref_T": bref, "U": uniformity, "U_at": u_at, "tilt_max_rad": tilt, "tilt_at": tilt_at,
        "psi_point_Wb_per_rad": psi_point, "phi_point_Wb": 2 * math.pi * psi_point,
        "center_points": int(center.sum()),
    }


def check(name, passed, **detail):
    return {"name": name, "status": "PASS" if passed else "FAIL", **detail}


def run_checks(states):
    """Tolerances are fixed here, before results are read, from round-off or quadrature error."""
    out = []
    scale = MU0 * CURRENT / (2 * RADIUS)  # ring-centre field, the natural magnitude
    points = grid_points()
    # Independent line integrals of Biot-Savart and of the vector potential.
    for name, rings in STATES.items():
        direct, kernel = biot_savart(rings, points), field(rings, points)
        for key, ref in (("Br", scale), ("Bz", scale), ("psi", scale * RADIUS**2)):
            error = float(np.max(np.abs(kernel[key] - direct[key])))
            out.append(check(f"{name}_{key}_vs_biot_savart", error <= 1e-11 * ref, max_abs_error=error, tol=1e-11 * ref))
    # Textbook on-axis solution; psi and Br must vanish on the axis.
    z_axis = np.linspace(-0.4, 0.4, 41)
    axis = np.column_stack((np.zeros_like(z_axis), z_axis))
    for name, rings in STATES.items():
        kernel = field(rings, axis)
        error = float(np.max(np.abs(kernel["Bz"] - on_axis(rings, z_axis))))
        out.append(check(f"{name}_Bz_on_axis_analytic", error <= 1e-12 * scale, max_abs_error=error, tol=1e-12 * scale))
        out.append(check(f"{name}_psi_zero_on_axis", bool(np.all(kernel["psi"] == 0.0))))
        out.append(check(f"{name}_Br_zero_on_axis", bool(np.max(np.abs(kernel["Br"])) <= 1e-12 * scale)))
        out.append(check(f"{name}_positive_phi_gives_positive_Bz", bool(np.all(kernel["Bz"] > 0))))
    # Helmholtz closed form for the nominal pair.
    centre = float(field(STATES["nominal"], [[0.0, 0.0]])["Bz"][0])
    helmholtz = (4 / 5) ** 1.5 * MU0 * CURRENT / RADIUS
    out.append(check("nominal_centre_matches_helmholtz", abs(centre - helmholtz) <= 1e-12 * helmholtz,
                     value_T=centre, closed_form_T=helmholtz))
    # Closed-form curvature against a finite difference of the on-axis solution.
    for name, rings in STATES.items():
        # Fourth-order stencil: the truncation of the three-point rule exceeds this tolerance.
        mid, step = sum(rings) / 2, 5e-3
        stencil = ((-2, -1 / 12), (-1, 4 / 3), (0, -5 / 2), (1, 4 / 3), (2, -1 / 12))
        numeric = float(sum(c * on_axis(rings, mid + i * step) for i, c in stencil) / step**2)
        tolerance = 1e-5 * scale / RADIUS**2
        out.append(check(f"{name}_axis_curvature_closed_form", abs(numeric - axis_curvature(rings[1] - rings[0])) <= tolerance,
                         numeric=numeric, closed_form=axis_curvature(rings[1] - rings[0])))
    # B must follow from psi: B_Z = (1/R) dpsi/dR, B_R = -(1/R) dpsi/dZ.
    step = 1e-4
    for name, rings in STATES.items():
        kernel = field(rings, points)
        d_r = (field(rings, points + [step, 0])["psi"] - field(rings, points - [step, 0])["psi"]) / (2 * step)
        d_z = (field(rings, points + [0, step])["psi"] - field(rings, points - [0, step])["psi"]) / (2 * step)
        bz_error = float(np.max(np.abs(d_r / points[:, 0] - kernel["Bz"])))
        br_error = float(np.max(np.abs(-d_z / points[:, 0] - kernel["Br"])))
        out.append(check(f"{name}_field_from_psi_derivatives", max(bz_error, br_error) <= 1e-6 * scale,
                         bz_error=bz_error, br_error=br_error, tol=1e-6 * scale))
    # 2 pi psi must equal the flux integral over the disk of radius 0.10 m.
    nodes, weights = np.polynomial.legendre.leggauss(64)
    r_nodes = 0.05 * (nodes + 1)
    for name, rings in STATES.items():
        bz = field(rings, np.column_stack((r_nodes, np.zeros_like(r_nodes))))["Bz"]
        integral = float(np.sum(0.05 * weights * 2 * np.pi * r_nodes * bz))
        phi = states[name]["phi_point_Wb"]
        out.append(check(f"{name}_flux_equals_disk_integral", abs(integral - phi) <= 1e-12 * abs(phi),
                         integral_Wb=integral, phi_Wb=phi))
    # Nominal mirror symmetry about Z=0, without altering any output.
    state = evaluate(STATES["nominal"])
    n_r, n_z = len(GRID_R), len(GRID_Z)
    br, bz, psi = (state[k].reshape(n_r, n_z) for k in ("Br", "Bz", "psi"))
    midplane = float(np.max(np.abs(br[:, n_z // 2])))
    odd = float(np.max(np.abs(br + br[:, ::-1])))
    even_bz = float(np.max(np.abs(bz - bz[:, ::-1])))
    even_psi = float(np.max(np.abs(psi - psi[:, ::-1])))
    out.append(check("nominal_midplane_Br_zero", midplane <= 1e-14 * scale, max_abs=midplane, tol=1e-14 * scale))
    out.append(check("nominal_Br_odd_in_Z", odd <= 1e-14 * scale, max_abs=odd))
    out.append(check("nominal_Bz_even_in_Z", even_bz <= 1e-14 * scale, max_abs=even_bz))
    out.append(check("nominal_psi_even_in_Z", even_psi <= 1e-14 * scale * RADIUS**2, max_abs=even_psi))
    # Linear superposition, compared with the round-off bound of the two-term sum.
    kernel = field(STATES["nominal"], points)
    for key, green in (("Br", "gBR"), ("Bz", "gBZ"), ("psi", "gpsi")):
        terms = kernel["per_amp"][green] * CURRENT
        bound = 8 * np.finfo(float).eps * np.sum(np.abs(terms), axis=1)
        error = np.abs(kernel[key] - terms.sum(axis=1))
        out.append(check(f"nominal_superposition_{key}", bool(np.all(error <= bound)), max_abs_error=float(error.max())))
    out.append(check("grid_has_25_points_and_9_central",
                     len(points) == 25 and states["nominal"]["center_points"] == 9))
    return out


def write_points(states_eval):
    keys = ("Br", "Bz", "Bmag", "psi", "tilt")
    header = ["state", "R_m", "Z_m", "Br_T", "Bz_T", "Bmag_T", "psi_Wb_per_rad", "tilt_rad"]
    with (HERE / "data" / "points.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(header)
        for name in ("nominal", "offset"):
            state = states_eval[name]
            for i in range(25):
                writer.writerow([name, state["R"][i], state["Z"][i], *(repr(float(state[k][i])) for k in keys)])
        for i in range(25):
            a, b = states_eval["nominal"], states_eval["offset"]
            writer.writerow(["offset_minus_nominal", a["R"][i], a["Z"][i], *(repr(float(b[k][i] - a[k][i])) for k in keys)])


def main():
    (HERE / "data").mkdir(exist_ok=True)
    states = {name: metrics(rings) for name, rings in {**STATES, **AUXILIARY}.items()}
    nominal, offset = states["nominal"], states["offset"]
    difference = {key: offset[key] - nominal[key]
                  for key in ("bref_T", "U", "tilt_max_rad", "psi_point_Wb_per_rad", "phi_point_Wb")}
    # First-order estimate: only the upper ring moved, and it supplies half the central field.
    z0 = STATES["nominal"][1]
    estimate = -3 * z0 * 0.02 / (RADIUS**2 + z0**2) / 2
    summary = {
        "inputs": {"radius_m": RADIUS, "current_A": CURRENT, "mu0_H_per_m": MU0},
        "states": states, "offset_minus_nominal": difference,
        "bref_relative_change": difference["bref_T"] / nominal["bref_T"],
        "bref_first_order_estimate": estimate,
        "helmholtz_centre_T": (4 / 5) ** 1.5 * MU0 * CURRENT / RADIUS,
        "axial_shape": {name: axial_shape(rings) for name, rings in STATES.items()},
    }
    checks = run_checks(states)
    write_points({name: evaluate(STATES[name]) for name in STATES})
    (HERE / "data" / "summary.json").write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
    (HERE / "data" / "checks.json").write_text(json.dumps(checks, indent=1) + "\n", encoding="utf-8")
    failed = [item["name"] for item in checks if item["status"] != "PASS"]
    print(f"{len(checks)} checks, {len(failed)} failed: {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
