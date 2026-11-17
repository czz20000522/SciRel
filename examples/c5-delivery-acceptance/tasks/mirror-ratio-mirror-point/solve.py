"""C5 task A: magnetic-mirror ratio and mirror-point criterion, using only the delivered package.

Physics asked for:
  For a mirror field with B_min at the midplane and B_max at the plug, state the mirror
  ratio R_m, the loss-cone pitch angle, and decide for two particles (pitch angles 20 deg
  and 45 deg at the midplane) whether each is trapped, and where its mirror point is.

What the package can answer: the loss-cone angular spectrum operator
`scirel.mirror.loss_cone_spectrum.solve_loss_cone_spectrum`, which takes the loss-cone
pitch-cosine boundary xi_tp as an *input*. What it cannot answer: R_m itself, the loss-cone
angle and the mirror-point location are not outputs of any asset in the package (no asset
accepts a field profile and returns a mirror ratio; `scirel.mirror.grid-mirror-kinetic-closure`
interpolates B at caller-named planes but returns pressures/fluxes, not R_m). Those three
relations are ordinary code here and are labelled as such.

Independent checks (declared before running):
  C1 exact integer mode: at xi_tp = 1/sqrt(3) the regular even solution is the Legendre
     polynomial P_2, i.e. degree exactly 2, eigenvalue exactly 6, eigenfunction 1-3*xi^2.
     Tolerance 2e-10 absolute, taken from the contract's own example block.
  C2 endpoint residual: contract declares |u(xi_tp)| <= 2e-8.
  C3 mirror point: analytically B(z_m) = B_min/sin^2(theta_0). Checked by integrating the
     guiding-centre equation of motion in the same analytic field and finding the first
     turning point; tolerance 1e-6 m on z_m, derived from the RK4 step and the field scale.
  C4 energy conservation along that integration: |dE/E| <= 1e-10 (RK4 with h=1e-6 s).
"""

from __future__ import annotations

import json
import math
import os
import pathlib

import numpy as np

from scirel.mirror.loss_cone_spectrum import solve_loss_cone_spectrum

PACKAGE_ROOT = pathlib.Path(os.environ["SCIREL_PACKAGE_ROOT"]).resolve()
CONTRACT = PACKAGE_ROOT / "catalog" / "contracts" / "scirel.mirror.loss-cone-spectrum.json"

# Frozen inputs (literal binding: written here before any call).
B_MIN_T = 0.50  # midplane field, T
B_MAX_T = 1.50  # plug field, T
Z_PLUG_M = 0.30  # plug position, m
PITCH_DEG = (20.0, 45.0)
ENERGY_EV = 1000.0
PROTON_MASS_KG = 1.67262192369e-27
ELEMENTARY_CHARGE_C = 1.602176634e-19

CALLS: list[dict] = []


def record(entrypoint: str, args: dict, status: str, **extra) -> None:
    CALLS.append({"entrypoint": entrypoint, "arguments": args, "status": status, **extra})


def field_b(z):
    """Parabolic mirror field matching B_min at z=0 and B_max at z=+/-Z_PLUG."""
    return B_MIN_T + (B_MAX_T - B_MIN_T) * (np.asarray(z, dtype=float) / Z_PLUG_M) ** 2


def mirror_point_m(pitch_deg: float) -> tuple[float | None, float]:
    """Analytic mirror point from the magnetic-moment invariant. Returns (z_m, B_m)."""
    sin2 = math.sin(math.radians(pitch_deg)) ** 2
    b_mirror = B_MIN_T / sin2
    if b_mirror > B_MAX_T:
        return None, b_mirror
    # B(z) = B_min + (B_max-B_min)(z/z_plug)^2  =>  solve for z
    ratio = (b_mirror - B_MIN_T) / (B_MAX_T - B_MIN_T)
    return Z_PLUG_M * math.sqrt(ratio), b_mirror


def turning_point_m(pitch_deg: float) -> dict:
    """Integrate the guiding-centre motion and locate the first turning point inside the plug."""
    speed = math.sqrt(2.0 * ENERGY_EV * ELEMENTARY_CHARGE_C / PROTON_MASS_KG)
    mu = PROTON_MASS_KG * speed**2 * math.sin(math.radians(pitch_deg)) ** 2 / (2.0 * B_MIN_T)
    energy = 0.5 * PROTON_MASS_KG * speed**2

    def rhs(z, vpar):
        dbdz = 2.0 * (B_MAX_T - B_MIN_T) * z / Z_PLUG_M**2
        return vpar, -mu * dbdz / PROTON_MASS_KG

    z, vpar = 0.0, speed * math.cos(math.radians(pitch_deg))
    # Step resolved against the transit time: ~2000 steps from midplane to plug.
    step = Z_PLUG_M / (2000.0 * abs(vpar))
    max_energy_drift = 0.0
    for _ in range(200_000):
        k1z, k1v = rhs(z, vpar)
        k2z, k2v = rhs(z + 0.5 * step * k1z, vpar + 0.5 * step * k1v)
        k3z, k3v = rhs(z + 0.5 * step * k2z, vpar + 0.5 * step * k2v)
        k4z, k4v = rhs(z + step * k3z, vpar + step * k3v)
        z_next = z + step * (k1z + 2 * k2z + 2 * k3z + k4z) / 6.0
        vpar_next = vpar + step * (k1v + 2 * k2v + 2 * k3v + k4v) / 6.0
        current = 0.5 * PROTON_MASS_KG * vpar_next**2 + mu * float(field_b(z_next))
        max_energy_drift = max(max_energy_drift, abs(current - energy) / energy)
        if vpar_next <= 0.0:
            frac = vpar / (vpar - vpar_next)
            return {
                "turning_point_m": z + frac * (z_next - z),
                "max_relative_energy_drift": max_energy_drift,
                "escaped": False,
            }
        if z_next >= Z_PLUG_M:  # reached the plug plane still moving outward: left the mirror
            return {
                "turning_point_m": None,
                "max_relative_energy_drift": max_energy_drift,
                "escaped": True,
                "exit_field_t": float(field_b(z_next)),
            }
        z, vpar = z_next, vpar_next
    raise RuntimeError("guiding-centre integration did not terminate")


def main() -> dict:
    if not CONTRACT.is_file():
        raise SystemExit(f"contract not found in package: {CONTRACT}")
    contract = json.loads(CONTRACT.read_text())
    record(
        "catalog/contracts read",
        {"path": str(CONTRACT.relative_to(PACKAGE_ROOT))},
        "ok",
        asset_id=contract["asset_id"],
    )

    # --- relations the package does not provide: computed as ordinary code ---
    mirror_ratio = B_MAX_T / B_MIN_T
    xi_tp = math.sqrt(B_MIN_T / B_MAX_T)
    theta_loss_deg = math.degrees(math.asin(xi_tp))

    # --- the package operator, at the loss-cone boundary it requires as input ---
    args = {"xi_tp": xi_tp, "mode_count": 3, "grid_points": 256}
    result = solve_loss_cone_spectrum(**args)
    record(
        "scirel.mirror.loss_cone_spectrum.solve_loss_cone_spectrum",
        args,
        "returned",
        returned_fields=sorted(result),
    )

    degrees = np.asarray(result["degrees"], dtype=float)
    eigenvalues = np.asarray(result["eigenvalues"], dtype=float)
    eigenfunctions = np.asarray(result["eigenfunctions"], dtype=float)
    xi = np.asarray(result["xi"], dtype=float)
    residual = np.max(np.abs(np.asarray(result["boundary_residuals"], dtype=float)))

    # --- checks ---
    exact_u = 1.0 - 3.0 * xi**2
    check_c1 = {
        "criterion": "exact integer mode P_2 at xi_tp=1/sqrt(3)",
        "degree_0": float(degrees[0]),
        "eigenvalue_0": float(eigenvalues[0]),
        "degree_0_deviation": abs(float(degrees[0]) - 2.0),
        "eigenvalue_0_deviation": abs(float(eigenvalues[0]) - 6.0),
        "eigenfunction_max_abs_deviation": float(np.max(np.abs(eigenfunctions[:, 0] - exact_u))),
        "declared_tolerance": 2e-10,
        "passed": bool(
            abs(float(degrees[0]) - 2.0) <= 1e-10
            and abs(float(eigenvalues[0]) - 6.0) <= 1e-10
            and float(np.max(np.abs(eigenfunctions[:, 0] - exact_u))) <= 2e-10
        ),
    }
    check_c2 = {
        "criterion": "contract endpoint residual |u(xi_tp)| <= 2e-8",
        "max_abs_boundary_residual": float(residual),
        "declared_tolerance": 2e-8,
        "passed": bool(residual <= 2e-8),
    }
    # The contract's own example block declares the first two eigenvalues at xi_tp=1/sqrt(3).
    declared_second = "58.08747396"
    check_c5 = {
        "criterion": "contract example declaration: eigenvalues at xi_tp=1/sqrt(3) are 6.0 and 58.08747396",
        "declared_second_eigenvalue": declared_second,
        "observed_second_eigenvalue": float(eigenvalues[1]),
        "deviation": abs(float(eigenvalues[1]) - float(declared_second)),
        "declared_tolerance": 1e-8,
        "passed": bool(abs(float(eigenvalues[1]) - float(declared_second)) <= 1e-8),
    }

    particles = []
    for pitch in PITCH_DEG:
        z_analytic, b_mirror = mirror_point_m(pitch)
        integration = turning_point_m(pitch)
        if z_analytic is None:
            point_check = {
                "criterion": "escaped: analytic mirror field exceeds B_max",
                "analytic_mirror_field_t": b_mirror,
                "b_max_t": B_MAX_T,
                "integration_escaped": integration["escaped"],
                "passed": bool(integration["escaped"]),
            }
        else:
            deviation = abs(integration["turning_point_m"] - z_analytic)
            point_check = {
                "criterion": "integrated turning point equals analytic mirror point",
                "analytic_mirror_point_m": z_analytic,
                "integrated_turning_point_m": integration["turning_point_m"],
                "deviation_m": deviation,
                "declared_tolerance_m": 1e-6,
                "passed": bool(deviation <= 1e-6),
            }
        particles.append(
            {
                "pitch_angle_deg": pitch,
                "sin_pitch": math.sin(math.radians(pitch)),
                "trapped": z_analytic is not None,
                "mirror_field_t": b_mirror,
                "mirror_point_m": z_analytic,
                "criterion_check": point_check,
                "energy_check": {
                    "criterion": "RK4 energy drift <= 1e-10",
                    "max_relative_energy_drift": integration["max_relative_energy_drift"],
                    "declared_tolerance": 1e-10,
                    "passed": bool(integration["max_relative_energy_drift"] <= 1e-10),
                },
            }
        )

    return {
        "task_id": "mirror-ratio-mirror-point",
        "assets_used": [contract["asset_id"]],
        "calls": CALLS,
        "answer": {
            "mirror_ratio": {"value": mirror_ratio, "units": "dimensionless"},
            "loss_cone_pitch_cosine": {"value": xi_tp, "units": "dimensionless"},
            "loss_cone_pitch_angle": {"value": theta_loss_deg, "units": "degree"},
            "pitch_cosine_endpoint": {
                "value": 1.0 / math.sqrt(3.0),
                "units": "dimensionless",
                "note": "= sqrt(B_min/B_max) = 1/sqrt(3) exactly for R_m=3",
            },
            "angular_modes": {
                "degrees": degrees.tolist(),
                "eigenvalues": eigenvalues.tolist(),
                "units": "dimensionless",
            },
            "particles": particles,
        },
        "independent_check": {
            "C1_exact_integer_mode": check_c1,
            "C2_endpoint_residual": check_c2,
            "C3_mirror_point_vs_integration": [p["criterion_check"] for p in particles],
            "C4_energy_conservation": [p["energy_check"] for p in particles],
            "C5_contract_declared_example": check_c5,
            "note": "C3 and C4 come from an independent route (RK4 orbit in the same analytic field); "
            "C1 comes from the closed-form Legendre polynomial, not from the operator.",
        },
        "package_sufficient": False,
        "gaps": [
            "No asset computes the mirror ratio R_m = B_max/B_min: all 12 mirror-domain contracts "
            "take the loss-cone boundary as an input rather than deriving it.",
            "No asset computes the loss-cone pitch angle or the mirror-point location from a field "
            "profile; both were written as ordinary code here.",
            "No general magnetic-field constructor is delivered: scirel.mirror.grid-mirror-kinetic-closure "
            "interpolates a caller-supplied b_t grid at two named planes and is explicitly excluded as "
            "a field constructor, so the analytic B(z) used here is consumer code.",
        ],
    }


if __name__ == "__main__":
    out = main()
    destination = pathlib.Path(__file__).with_suffix(".result.json")
    destination.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=2, ensure_ascii=False))
