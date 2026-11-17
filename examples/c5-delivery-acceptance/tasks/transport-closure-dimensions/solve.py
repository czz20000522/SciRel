"""C5 task C: dimensional consistency of a delivered transport closure, package only.

Physics asked for:
  Assemble the neoclassical bootstrap current from the delivered coefficient fit plus the
  delivered parallel-current operator, and establish that the closure is dimensionally
  consistent: what each input's unit is, whether the returned quantity really carries
  A/m^2, and which power of each input the result scales with.

Package ports used:
  scirel.neoclassical.compute_bootstrap_coefficients(f_trap, nu_e_star, Z_eff, nu_i_star, method='redl')
  scirel.neoclassical.calculate_bootstrap_current(...)

Dimensional claim to test (written before running, from the contract's stated relation
j_face = -F*mult/(B0*dpsi_per_radian_drho) * [L31*pe*dlnne + ...]):
  [F] = T m, [B0] = T, [dpsi_per_radian_drho] = Wb/rad = T m^2, so the prefactor carries
  1/(T m); times [p] = Pa = kg m^-1 s^-2 and the dimensionless bracket leaves
  Pa/(T m) = (kg m^-1 s^-2)/(kg m A^-1 s^-2) = A m^-2. That is exactly the declared output.

Independent checks (declared before running):
  C1 hand-evaluated constant case: the contract's example inputs (-F/(B0*dpsi_per_radian)
     with a unit L31 bracket) must give -pi on non-axis faces and exactly 0 on the axis.
  C2 flux-convention equivalence: dpsi_drho = 2*pi*dpsi_per_radian_drho must not change j.
  C3 scaling exponents (the operational form of the dimensional claim), each to 1e-13 relative:
     pressure x4 -> j x4; B0 x2 -> j /2; dpsi x2 -> j /2; F x2 -> j x2.
  C4 axis handling: rho_face=0 gives exactly 0.0 and no other face is zeroed.
  C5 failure semantics: supplying both flux conventions raises the declared ValueError.
"""

from __future__ import annotations

import json
import math
import os
import pathlib

import numpy as np

from scirel.neoclassical import calculate_bootstrap_current, compute_bootstrap_coefficients

PACKAGE_ROOT = pathlib.Path(os.environ["SCIREL_PACKAGE_ROOT"]).resolve()
CONTRACTS = PACKAGE_ROOT / "catalog" / "contracts"

CALLS: list[dict] = []


def record(entrypoint: str, args: dict, status: str, **extra) -> None:
    def plain(value):
        if isinstance(value, np.ndarray):
            return value.tolist()
        if isinstance(value, (list, tuple)):
            return [plain(v) for v in value]
        return value

    CALLS.append(
        {
            "entrypoint": entrypoint,
            "arguments": {k: plain(v) for k, v in args.items()},
            "status": status,
            **extra,
        }
    )


def current(**kwargs):
    """Call the delivered operator and return the face array as float ndarray."""
    result = calculate_bootstrap_current(**kwargs)
    return np.asarray(result["j_parallel_bootstrap_face"], dtype=float)


def main() -> dict:
    current_contract_path = CONTRACTS / "scirel.neoclassical.bootstrap-current.json"
    coefficients_contract_path = CONTRACTS / "scirel.neoclassical.bootstrap-coefficients.json"
    current_contract = json.loads(current_contract_path.read_text())
    coefficients_contract = json.loads(coefficients_contract_path.read_text())
    record(
        "catalog/contracts read",
        {
            "paths": [
                str(p.relative_to(PACKAGE_ROOT))
                for p in (current_contract_path, coefficients_contract_path)
            ]
        },
        "ok",
        asset_ids=[current_contract["asset_id"], coefficients_contract["asset_id"]],
    )

    # Frozen inputs: five radial faces of a textbook-scale tokamak edge profile.
    rho_face = np.array([0.0, 0.25, 0.50, 0.75, 1.00])
    f_trap = np.array([0.0, 0.12, 0.28, 0.46, 0.62])
    nu_e_star = np.array([0.0, 0.05, 0.20, 0.60, 1.40])
    z_eff = np.full(5, 1.6)
    nu_i_star = np.array([0.0, 0.04, 0.15, 0.45, 1.10])

    coefficients = compute_bootstrap_coefficients(
        f_trap, nu_e_star, z_eff, nu_i_star, method="redl"
    )
    record(
        "scirel.neoclassical.compute_bootstrap_coefficients",
        {
            "f_trap": f_trap,
            "nu_e_star": nu_e_star,
            "Z_eff": z_eff,
            "nu_i_star": nu_i_star,
            "method": "redl",
        },
        "returned",
        returned_fields=list(coefficients),
    )
    L31 = np.asarray(coefficients["L31"], dtype=float)
    L32 = np.asarray(coefficients["L32"], dtype=float)
    L34 = np.asarray(coefficients["L34"], dtype=float)
    alpha = np.asarray(coefficients["alpha"], dtype=float)

    F_face = np.array([6.0, 6.1, 6.2, 6.3, 6.4])  # T m
    B0 = 5.3  # T
    dpsi_drho_face = np.array([-1.0e-3, -1.2e-3, -1.6e-3, -2.2e-3, -3.0e-3])  # Wb
    p_e_face = np.array([1.0e4, 9.0e3, 6.0e3, 3.0e3, 5.0e2])  # Pa
    p_i_face = np.array([8.0e3, 7.2e3, 4.8e3, 2.4e3, 4.0e2])  # Pa
    dlnne_drho_face = np.array([0.0, -0.9, -1.4, -2.2, -3.4])
    dlnni_drho_face = np.array([0.0, -0.8, -1.3, -2.0, -3.2])
    dlnte_drho_face = np.array([0.0, -1.1, -1.8, -2.7, -4.0])
    dlnti_drho_face = np.array([0.0, -1.0, -1.7, -2.5, -3.8])

    base_kwargs = dict(
        rho_face=rho_face,
        F_face=F_face,
        B0=B0,
        dpsi_drho_face=dpsi_drho_face,
        p_e_face=p_e_face,
        p_i_face=p_i_face,
        dlnne_drho_face=dlnne_drho_face,
        dlnni_drho_face=dlnni_drho_face,
        dlnte_drho_face=dlnte_drho_face,
        dlnti_drho_face=dlnti_drho_face,
        L31=L31,
        L32=L32,
        L34=L34,
        alpha=alpha,
    )
    j_base = current(**base_kwargs)
    record(
        "scirel.neoclassical.calculate_bootstrap_current",
        {k: v for k, v in base_kwargs.items()},
        "returned",
        returned={"j_parallel_bootstrap_face_A_m2": j_base.tolist()},
    )

    # --- C1: hand-evaluated constant case from the contract example ---
    one = np.ones(3)
    zero = np.zeros(3)
    example_kwargs = dict(
        rho_face=[0.0, 0.5, 1.0],
        F_face=one,
        B0=2.0,
        dpsi_drho_face=one,
        p_e_face=one,
        p_i_face=one,
        dlnne_drho_face=one,
        dlnni_drho_face=zero,
        dlnte_drho_face=zero,
        dlnti_drho_face=zero,
        L31=one,
        L32=zero,
        L34=one,
        alpha=one,
    )
    j_example = current(**example_kwargs)
    record(
        "scirel.neoclassical.calculate_bootstrap_current",
        example_kwargs,
        "returned",
        note="hand-evaluated constant case",
        returned={"j_parallel_bootstrap_face_A_m2": j_example.tolist()},
    )
    hand_value = np.array([0.0, -math.pi, -math.pi])
    check_c1 = {
        "criterion": "hand-evaluated j = -F/(B0*dpsi/2pi)*L31*p*dlnne gives [0,-pi,-pi]",
        "hand_value": hand_value.tolist(),
        "observed": j_example.tolist(),
        "max_abs_deviation": float(np.max(np.abs(j_example - hand_value))),
        "declared_tolerance": 1e-12,
        "passed": bool(np.max(np.abs(j_example - hand_value)) <= 1e-12),
    }

    # --- C2: the two flux conventions agree ---
    per_radian_kwargs = {k: v for k, v in base_kwargs.items() if k != "dpsi_drho_face"}
    per_radian_kwargs["dpsi_per_radian_drho_face"] = dpsi_drho_face / (2.0 * math.pi)
    j_per_radian = current(**per_radian_kwargs)
    record(
        "scirel.neoclassical.calculate_bootstrap_current",
        {k: v for k, v in per_radian_kwargs.items()},
        "returned",
        note="per-radian flux convention",
        returned={"j_parallel_bootstrap_face_A_m2": j_per_radian.tolist()},
    )
    convention_dev = float(
        np.max(np.abs(j_per_radian - j_base)) / max(np.max(np.abs(j_base)), 1e-30)
    )
    check_c2 = {
        "criterion": "dpsi_drho = 2*pi*dpsi_per_radian_drho leaves j unchanged, rel <= 1e-13",
        "max_relative_deviation": convention_dev,
        "declared_tolerance": 1e-13,
        "passed": bool(convention_dev <= 1e-13),
    }

    # --- C3: scaling exponents (operational form of the dimensional claim) ---
    def ratio(factor_kwargs, scale):
        j_scaled = current(**{**base_kwargs, **factor_kwargs})
        mask = rho_face > 0.0
        observed = j_scaled[mask] / j_base[mask]
        return float(np.max(np.abs(observed - scale)))

    scaling = {
        "pressure_x4_gives_j_x4": {
            "observed_max_abs_deviation": ratio(
                {"p_e_face": p_e_face * 4.0, "p_i_face": p_i_face * 4.0}, 4.0
            ),
            "expected_scale": 4.0,
        },
        "B0_x2_gives_j_div_2": {
            "observed_max_abs_deviation": ratio({"B0": B0 * 2.0}, 0.5),
            "expected_scale": 0.5,
        },
        "dpsi_x2_gives_j_div_2": {
            "observed_max_abs_deviation": ratio({"dpsi_drho_face": dpsi_drho_face * 2.0}, 0.5),
            "expected_scale": 0.5,
        },
        "F_x2_gives_j_x2": {
            "observed_max_abs_deviation": ratio({"F_face": F_face * 2.0}, 2.0),
            "expected_scale": 2.0,
        },
    }
    for name, payload in scaling.items():
        record(
            "scirel.neoclassical.calculate_bootstrap_current",
            {"scaling_case": name, "expected_scale": payload["expected_scale"]},
            "returned",
        )
    check_c3 = {
        "criterion": "each scaling deviation <= 1e-13",
        "declared_tolerance": 1e-13,
        "cases": scaling,
        "passed": bool(all(v["observed_max_abs_deviation"] <= 1e-13 for v in scaling.values())),
    }

    # --- C4: axis face exactly zero, others not zeroed ---
    check_c4 = {
        "criterion": "rho_face==0 gives exactly 0.0 and no other face is zeroed",
        "axis_face_value": float(j_base[0]),
        "nonzero_face_count": int(np.count_nonzero(j_base[1:])),
        "total_nonaxis_faces": int(j_base.size - 1),
        "passed": bool(j_base[0] == 0.0 and np.count_nonzero(j_base[1:]) == j_base.size - 1),
    }

    # --- C5: declared failure semantics for a conflicting flux convention ---
    failure = {"raised": False}
    try:
        current(**{**base_kwargs, "dpsi_per_radian_drho_face": dpsi_drho_face / (2.0 * math.pi)})
    except Exception as error:  # noqa: BLE001 - the point is to record the real type
        failure = {"raised": True, "exception": type(error).__name__, "message": str(error)[:300]}
    record(
        "scirel.neoclassical.calculate_bootstrap_current",
        {"both_flux_conventions": True},
        "raised" if failure["raised"] else "returned",
        failure=failure,
    )
    check_c5 = {
        "criterion": "declared invalid_input: ValueError when both flux conventions are supplied",
        "observed": failure,
        "declared_exception": "ValueError",
        "passed": bool(failure.get("raised") and failure.get("exception") == "ValueError"),
    }

    # --- C6: unit bookkeeping across the two operators ---
    coefficient_units = {
        item["name"]: item.get("units") for item in coefficients_contract["outputs"]
    }
    current_output_units = {item["name"]: item.get("units") for item in current_contract["outputs"]}
    input_units = {item["name"]: item.get("units") for item in current_contract["inputs"]}
    check_c6 = {
        "criterion": "coefficient outputs are dimensionless and the current output is A/m^2",
        "coefficient_output_units": coefficient_units,
        "current_output_units": current_output_units,
        "unit_algebra": (
            "[F]=T*m, [B0]=T, [dpsi_per_radian_drho]=Wb/rad=T*m^2 => prefactor 1/(T*m); "
            "[p]=Pa=kg*m^-1*s^-2; T=kg*A^-1*s^-2 => Pa/(T*m)=A*m^-2"
        ),
        "passed": bool(
            set(coefficient_units.values()) == {"1"}
            and set(current_output_units.values()) == {"A/m^2"}
        ),
    }

    return {
        "task_id": "transport-closure-dimensions",
        "assets_used": [coefficients_contract["asset_id"], current_contract["asset_id"]],
        "calls": CALLS,
        "answer": {
            "j_parallel_bootstrap_face": {"value": j_base.tolist(), "units": "A/m^2"},
            "coefficients": {
                "L31": L31.tolist(),
                "L32": L32.tolist(),
                "L34": L34.tolist(),
                "alpha": alpha.tolist(),
                "units": "dimensionless",
                "method": "redl",
            },
            "declared_output_unit": current_output_units,
            "input_units": input_units,
        },
        "independent_check": {
            "C1_hand_evaluated_constant_case": check_c1,
            "C2_flux_convention_equivalence": check_c2,
            "C3_scaling_exponents": check_c3,
            "C4_axis_face": check_c4,
            "C5_declared_failure": check_c5,
            "C6_unit_bookkeeping": check_c6,
        },
        "package_sufficient": True,
        "gaps": [
            "Neither contract derives its own inputs: trapped fraction, collisionalities and the "
            "flux-surface profiles (F, dpsi/drho, p, logarithmic gradients) must come from a "
            "geometry/equilibrium step the package does not deliver, so this task fixed them by hand.",
            "The current output is a local flux-surface quantity; no delivered asset relates it to a "
            "total current, a q profile or a magnetic shear, so the transport result cannot be closed "
            "against a tokamak discharge inside the package.",
            "The two coefficient families (redl, sauter) return different L34/alpha; the package "
            "delivers no guidance on which method a given collisionality range supports, only that "
            "the default is a declared choice.",
        ],
    }


if __name__ == "__main__":
    out = main()
    destination = pathlib.Path(__file__).with_suffix(".result.json")
    destination.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=2, ensure_ascii=False))
