"""C5 task B: meridional polar coordinate round-trip, using only the delivered package.

Physics asked for:
  Take a set of meridional (Rho, Z) positions with attached vector components
  (v_rho, v_z), map them into the polar (r, theta) basis with the orthogonal basis
  rotation, map them back, and report whether position and vector round-trip exactly
  and whether the vector norm is preserved.

Package ports used (both are delivered contracts, samplings domain):
  scirel.geometry.sampling.transform_to_rtheta(Rho, Z, rho_component, z_component)
  scirel.geometry.sampling.transform_to_rhoz(R, Theta, r_component, theta_component)

Independent checks (declared before running):
  C1 position round-trip: max |Rho'-Rho|, |Z'-Z| <= 1e-14 (pure algebra, no truncation).
  C2 vector round-trip:    max |v_rho'-v_rho|, |v_z'-v_z| <= 1e-14.
  C3 norm preservation:    max ||v'|-|v|| / |v| <= 1e-15 both directions.
  C4 independent closed form written from the contract's stated relation
     (r=hypot(rho,z), theta=atan2(rho,z), u_r=u_rho sin+u_z cos, u_theta=u_rho cos-u_z sin)
     reproduces the package output to 1e-15.
  C5 convention discriminator: the contract states theta is measured from +Z toward +rho,
     so cos(theta)=Z/r. The legacy convention quoted in the contract's own definition
     (theta = pi/2 + atan2(Z,Rho)) would give cos(theta) = -Z/r; a point with Z<0
     separates the two, and the package must follow the declared one.
"""

from __future__ import annotations

import json
import os
import pathlib

import numpy as np

from scirel.geometry.sampling import transform_to_rtheta, transform_to_rhoz

PACKAGE_ROOT = pathlib.Path(os.environ["SCIREL_PACKAGE_ROOT"]).resolve()
CONTRACTS = PACKAGE_ROOT / "catalog" / "contracts"

CALLS: list[dict] = []


def record(entrypoint: str, args: dict, status: str, **extra) -> None:
    def plain(value):
        if isinstance(value, np.ndarray):
            return value.tolist()
        return value

    CALLS.append(
        {
            "entrypoint": entrypoint,
            "arguments": {k: plain(v) for k, v in args.items()},
            "status": status,
            **extra,
        }
    )


def main() -> dict:
    forward_contract_path = CONTRACTS / "scirel.sampling.meridional-polar-forward.json"
    inverse_contract_path = CONTRACTS / "scirel.sampling.meridional-polar-inverse.json"
    forward_contract = json.loads(forward_contract_path.read_text())
    inverse_contract = json.loads(inverse_contract_path.read_text())
    record(
        "catalog/contracts read",
        {
            "paths": [
                str(p.relative_to(PACKAGE_ROOT))
                for p in (forward_contract_path, inverse_contract_path)
            ]
        },
        "ok",
        asset_ids=[forward_contract["asset_id"], inverse_contract["asset_id"]],
    )

    # Frozen inputs: a meridional quadrant covering both signs of Z, away from the origin
    # (the polar basis at the origin is excluded by both contracts).
    rho_m = np.array([0.15, 0.40, 0.90, 1.50, 0.60, 1.10])
    z_m = np.array([1.20, -0.85, 0.35, -1.10, 0.00, 0.55])
    v_rho = np.array([1.0, -2.5, 0.75, 3.25, -0.5, 2.0])
    v_z = np.array([0.5, 1.75, -3.0, 0.25, 2.5, -1.25])

    r, theta, v_r, v_th = transform_to_rtheta(rho_m, z_m, v_rho, v_z)
    record(
        "scirel.geometry.sampling.transform_to_rtheta",
        {"Rho": rho_m, "Z": z_m, "rho_component": v_rho, "z_component": v_z},
        "returned",
        returned={"r": np.asarray(r).tolist(), "theta": np.asarray(theta).tolist()},
    )

    rho_back, z_back, v_rho_back, v_z_back = transform_to_rhoz(r, theta, v_r, v_th)
    record(
        "scirel.geometry.sampling.transform_to_rhoz",
        {"R": r, "Theta": theta, "r_component": v_r, "theta_component": v_th},
        "returned",
        returned={"rho": np.asarray(rho_back).tolist(), "z": np.asarray(z_back).tolist()},
    )

    # --- independent closed form, written from the contract text only ---
    r_ind = np.hypot(rho_m, z_m)
    theta_ind = np.arctan2(rho_m, z_m)
    v_r_ind = v_rho * np.sin(theta_ind) + v_z * np.cos(theta_ind)
    v_th_ind = v_rho * np.cos(theta_ind) - v_z * np.sin(theta_ind)

    # --- checks ---
    position_dev = float(
        max(np.max(np.abs(np.asarray(rho_back) - rho_m)), np.max(np.abs(np.asarray(z_back) - z_m)))
    )
    vector_dev = float(
        max(
            np.max(np.abs(np.asarray(v_rho_back) - v_rho)),
            np.max(np.abs(np.asarray(v_z_back) - v_z)),
        )
    )
    norm_dev = float(
        max(
            np.max(np.abs(np.hypot(v_r, v_th) - np.hypot(v_rho, v_z))),
            np.max(np.abs(np.hypot(v_rho_back, v_z_back) - np.hypot(v_rho, v_z))),
        )
    )
    closed_form_dev = float(
        max(
            np.max(np.abs(np.asarray(r) - r_ind)),
            np.max(np.abs(np.asarray(theta) - theta_ind)),
            np.max(np.abs(np.asarray(v_r) - v_r_ind)),
            np.max(np.abs(np.asarray(v_th) - v_th_ind)),
        )
    )

    negative_z = z_m < 0
    cos_declared = z_m[negative_z] / r_ind[negative_z]
    cos_legacy = -z_m[negative_z] / r_ind[negative_z]
    cos_observed = np.cos(np.asarray(theta)[negative_z])

    checks = {
        "C1_position_roundtrip": {
            "criterion": "position round-trip |Rho'-Rho|,|Z'-Z| <= 1e-14",
            "max_abs_deviation": position_dev,
            "declared_tolerance": 1e-14,
            "passed": bool(position_dev <= 1e-14),
        },
        "C2_vector_roundtrip": {
            "criterion": "vector round-trip |v'-v| <= 1e-14",
            "max_abs_deviation": vector_dev,
            "declared_tolerance": 1e-14,
            "passed": bool(vector_dev <= 1e-14),
        },
        "C3_norm_preservation": {
            "criterion": "vector norm preserved both directions <= 1e-15",
            "max_abs_deviation": norm_dev,
            "declared_tolerance": 1e-15,
            "passed": bool(norm_dev <= 1e-15),
        },
        "C4_independent_closed_form": {
            "criterion": "contract-text closed form reproduces the package output <= 1e-15",
            "max_abs_deviation": closed_form_dev,
            "declared_tolerance": 1e-15,
            "passed": bool(closed_form_dev <= 1e-15),
        },
        "C5_convention_discriminator": {
            "criterion": "cos(theta) equals Z/r (declared) and not -Z/r (legacy) at Z<0",
            "points_with_z_negative": int(np.count_nonzero(negative_z)),
            "cos_theta_declared": cos_declared.tolist(),
            "cos_theta_legacy": cos_legacy.tolist(),
            "cos_theta_observed": cos_observed.tolist(),
            "max_abs_deviation_from_declared": float(np.max(np.abs(cos_observed - cos_declared))),
            "min_abs_deviation_from_legacy": float(np.min(np.abs(cos_observed - cos_legacy))),
            "declared_tolerance": 1e-15,
            "passed": bool(
                np.max(np.abs(cos_observed - cos_declared)) <= 1e-15
                and np.min(np.abs(cos_observed - cos_legacy)) > 0.1
            ),
        },
        "C6_contract_example": {
            "criterion": "contract example: transform_to_rtheta(0,2,3,4) == (2,0,4,3)",
            "observed_forward": [float(x) for x in transform_to_rtheta(0.0, 2.0, 3.0, 4.0)],
            "observed_inverse": [float(x) for x in transform_to_rhoz(2.0, 0.0, 4.0, 3.0)],
            "passed": bool(
                tuple(float(x) for x in transform_to_rtheta(0.0, 2.0, 3.0, 4.0))
                == (2.0, 0.0, 4.0, 3.0)
                and tuple(float(x) for x in transform_to_rhoz(2.0, 0.0, 4.0, 3.0))
                == (0.0, 2.0, 3.0, 4.0)
            ),
        },
    }

    return {
        "task_id": "geometry-coordinate-roundtrip",
        "assets_used": [forward_contract["asset_id"], inverse_contract["asset_id"]],
        "calls": CALLS,
        "answer": {
            "positions": {
                "Rho_m": rho_m.tolist(),
                "Z_m": z_m.tolist(),
                "r_m": np.asarray(r).tolist(),
                "theta_rad": np.asarray(theta).tolist(),
            },
            "position_roundtrip_max_abs_error_m": position_dev,
            "vector_roundtrip_max_abs_error": vector_dev,
            "norm_preservation_max_abs_error": norm_dev,
            "units": "m for positions, rad for theta, caller vector for components",
        },
        "independent_check": checks,
        "package_sufficient": True,
        "gaps": [
            "Only the two-dimensional meridional (Rho,Z) <-> (r,theta) pair is delivered. "
            "There is no full three-dimensional Cartesian <-> cylindrical transform with the toroidal "
            "angle (a search for 'cartesian cylindrical' returns only grid-mapping/interpolation assets), "
            "so a toroidal-coordinate workflow has to supply that leg itself.",
            "Both contracts exclude the polar basis at the origin; no asset supplies a regularised "
            "origin basis or a documented fallback there.",
        ],
    }


if __name__ == "__main__":
    out = main()
    destination = pathlib.Path(__file__).with_suffix(".result.json")
    destination.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=2, ensure_ascii=False))
