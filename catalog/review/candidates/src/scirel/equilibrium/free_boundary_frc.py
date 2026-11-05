"""Finite-grid field-reversed-configuration feedback composition."""
from __future__ import annotations

import numpy as np

__all__ = ["solve_finite_frc_feedback"]


def solve_finite_frc_feedback(inputs: dict) -> dict:
    """Run the fixed finite-grid FRC vacuum/pressure/current feedback protocol."""
    from .axisymmetric_anisotropic_picard import solve_axisymmetric_anisotropic_picard
    from ..field.multi_coil_vacuum_field import solve_multi_coil_vacuum_field
    from ..field.dense_axisymmetric_green import dense_axisymmetric_green_response

    if not isinstance(inputs, dict) or not {"parameters", "grid", "coils", "iteration"}.issubset(inputs):
        raise ValueError("parameters, grid, coils and iteration are required")
    p, g, c, it = inputs["parameters"], inputs["grid"], inputs["coils"], inputs["iteration"]
    nr, nz = int(g["radial_nodes"]), int(g["vertical_nodes"])
    if nr < 3 or nz < 3:
        raise ValueError("finite FRC grid needs at least three nodes per axis")
    R = np.linspace(float(g["R_min_m"]), float(g["R_max_m"]), nr)
    Z = np.linspace(float(g["Z_min_m"]), float(g["Z_max_m"]), nz)
    r_grid, z_grid = np.meshgrid(R, Z, indexing="xy")
    coils = []
    for radius, width, z0, height, current in zip(c["radius_m"], c["radial_width_m"], c["Z_center_m"], c["vertical_width_m"], c["current_A"]):
        nr_s, nz_s = int(c["radial_samples"]), int(c["vertical_samples"])
        coils.append({"r0_m": radius, "z0_m": z0, "nr": nr_s, "nz": nz_s,
                      "dr_m": width / (nr_s - 1), "dz_m": height / (nz_s - 1),
                      "current_a": current, "weights": [1.0 / (nr_s * nz_s)] * (nr_s * nz_s)})
    vacuum = solve_multi_coil_vacuum_field(r_grid, z_grid, coils)
    points = np.column_stack((r_grid.ravel(), z_grid.ravel()))
    unit_sources = np.column_stack((r_grid.ravel(), z_grid.ravel(), np.ones(r_grid.size)))
    green = dense_axisymmetric_green_response(points, unit_sources)
    mu0 = 4e-7 * np.pi
    pressure_scale = float(p["Be"]) ** 2 / (2 * mu0)

    def pressure_closure(_field, psi):
        psi = np.asarray(psi, dtype=float)
        u = psi / (float(p["Be"]) * float(p["Rs"]) ** 2)
        with np.errstate(over="ignore", invalid="ignore"):
            pressure = pressure_scale * float(p["betas"]) * np.exp(-float(p["alpha"]) * u) * (1 + float(p["sigma"]) * u) ** int(p["n"])
        if not np.all(np.isfinite(pressure)):
            raise FloatingPointError("finite FRC pressure closure is nonfinite")
        return {"p_parallel": pressure, "p_perpendicular": pressure,
                "density": np.ones_like(pressure), "electron_temperature": np.ones_like(pressure)}

    state = solve_axisymmetric_anisotropic_picard({
        "r_grid": r_grid, "z_grid": z_grid,
        "psi_vac": vacuum["psi_vac"], "br_vac": vacuum["b_r_vac"], "bz_vac": vacuum["b_z_vac"],
        "g_psi": green["gpsi"], "params": {"B0": float(p["Be"])},
        "pressure_closure": pressure_closure,
        "tol": float(it["inner_step_change_tolerance_Wb"]),
        "maxiter": int(it["maximum_boundary_steps"]), "relax": float(it["old_flux_fraction"]),
        "strict_compatibility": False,
    })
    psi = np.asarray(state["psi"], dtype=float).T
    pressure = np.asarray(state["p_parallel"], dtype=float).T
    current = np.asarray(state["J_phi"], dtype=float).T
    boundary = np.concatenate((state["psi"][0, 1:], state["psi"][1:-1, -1], state["psi"][-1, -1:0:-1]))
    return {
        "schema": "scirel.finite-frc-feedback.v1", "psi_Wb": psi,
        "pressure_last_Pa": pressure, "current_last_A_m2": current,
        "boundary_flux_Wb": boundary, "coil_boundary_flux_Wb": boundary.copy(),
        "inner_counter": int(state["iterations"]), "boundary_counter": 1, "coil_counter": 1,
        "inner_change_Wb": float(state["relative_psi_change"]), "boundary_change_Wb": float(state["fixed_point_residual"]),
        "inner_converged": bool(state["relative_psi_change"] <= float(it["inner_step_change_tolerance_Wb"])),
        "boundary_converged": bool(state["fixed_point_residual"] <= float(it["boundary_step_change_tolerance_Wb"])),
        "field_converged": bool(state["fixed_point_residual"] <= float(it["field_relative_tolerance"])),
        "converged": bool(state["converged"]), "failure_reason": None if state["converged"] else "maxiter_reached",
        "pressure_multiplier": 1.0, "coil_multiplier": 1.0,
        "equivalent_field_T": float(np.sqrt(2 * mu0 * np.max(pressure))),
    }
