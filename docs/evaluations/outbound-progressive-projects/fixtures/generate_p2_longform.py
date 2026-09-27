"""Create staged synthetic inputs for the P2 long-form export evaluation."""

from __future__ import annotations

import csv
import json
from pathlib import Path


RADII_M = (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7)
HEIGHTS_M = (-0.4, -0.3, -0.2, -0.1, 0.0, 0.1, 0.2, 0.3, 0.4)


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def write_map(path: Path, *, length_unit: str, scale: float) -> None:
    factor = {"cm": 100.0, "mm": 1000.0}[length_unit]
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow((f"R_{length_unit}", f"Z_{length_unit}",
                         "psi_Wb_per_rad", "B_R_T", "B_Z_T"))
        for z in HEIGHTS_M:
            for r in RADII_M:
                # psi = scale * r^2 * (0.35 + 0.02*z^2), so the fields
                # satisfy B_R = -d(psi)/dZ / R and B_Z = d(psi)/dR / R.
                psi = scale * r * r * (0.35 + 0.02 * z * z)
                br = -scale * 0.04 * r * z
                bz = scale * (0.7 + 0.04 * z * z)
                writer.writerow((r * factor, z * factor, psi, br, bz))


def main() -> None:
    root = Path(__file__).resolve().parents[4] / "build" / "verification" / "p2-longform-evaluation"
    initial = root / "solver-workspace" / "input"
    later = root / "examiner-private" / "later"
    for directory in (initial, later):
        directory.mkdir(parents=True, exist_ok=False)

    write_map(initial / "alpha-points.csv", length_unit="cm", scale=1.0)
    write_map(initial / "beta-points.csv", length_unit="mm", scale=1.08)
    write_json(initial / "alpha-export.json", {
        "source": "synthetic precomputed axisymmetric equilibrium export; not measured",
        "data_file": "alpha-points.csv",
        "coordinate_columns": ["R_cm", "Z_cm"],
        "poloidal_flux_convention": "Wb/rad",
        "field_components": "cylindrical B_R and B_Z in tesla; no toroidal component",
        "separatrix_flux_wb_per_rad": 0.13,
        "closed_flux_side": "less_than",
    })
    write_json(initial / "beta-export.json", {
        "source": "synthetic precomputed axisymmetric equilibrium export; not measured",
        "data_file": "beta-points.csv",
        "coordinate_columns": ["R_mm", "Z_mm"],
        "poloidal_flux_convention": "Wb/rad",
        "field_components": "cylindrical B_R and B_Z in tesla; no toroidal component",
        "separatrix_flux_wb_per_rad": 0.14,
        "closed_flux_side": None,
        "missing_declaration": "original export notes did not include the closed flux side",
    })
    write_json(initial / "grid-initial.json", {
        "source": "synthetic Cartesian target-grid specification",
        "axis_units": "m",
        "x_axis": [-0.5, -0.375, -0.25, -0.125, 0.0, 0.125, 0.25, 0.375, 0.5],
        "y_axis": [-0.5, -0.375, -0.25, -0.125, 0.0, 0.125, 0.25, 0.375, 0.5],
        "z_axis": [-0.3, -0.2, -0.1, 0.0, 0.1, 0.2, 0.3],
        "xpoint_half_length_m": 0.2,
        "pml_cells": 1,
        "pec_index_box_inclusive": {"x": [3, 5], "y": [4, 4], "z": [2, 4]},
    })
    (initial / "source-note.md").write_text(
        "# Export handoff\n\nBoth CSV tables are synthetic, already-computed "
        "axisymmetric equilibrium maps, not measurements or inputs to a new "
        "equilibrium solve. Each row describes one R-Z point. The field "
        "columns are cylindrical B_R and B_Z; no toroidal component is "
        "supplied. The grid is Cartesian, and its PEC box uses inclusive, "
        "zero-based indices. Please do not infer missing flux-surface "
        "declarations from the field values.\n",
        encoding="utf-8",
    )
    (initial / "target-format.md").write_text(
        "# Target reader contract\n\nOne .npz per case. Required arrays: "
        "magnetic_flux_density_t [N_x,N_y,N_z,3] in Cartesian "
        "(B_x,B_y,B_z) and tesla; poloidal_flux_wb_per_rad "
        "[N_x,N_y,N_z]; material_support_mask [N_x,N_y,N_z] of "
        "boolean dtype. Axes follow the target-grid x,y,z arrays. "
        "The target reader rejects nonfinite fields and nonboolean masks.\n",
        encoding="utf-8",
    )
    (later / "beta-export-note.md").write_text(
        "# Colleague's follow-up for beta\n\nThe missing `closed_flux_side` "
        "in beta's original export is `less_than`. The separatrix value "
        "in beta-export.json is unchanged. This note is a source declaration, "
        "not a new equilibrium calculation.\n",
        encoding="utf-8",
    )
    write_json(later / "grid-followup.json", {
        "source": "synthetic revised Cartesian target-grid specification",
        "axis_units": "m",
        "x_axis": [-0.54, -0.36, -0.18, 0.0, 0.18, 0.36, 0.54],
        "y_axis": [-0.54, -0.36, -0.18, 0.0, 0.18, 0.36, 0.54],
        "z_axis": [-0.32, -0.16, 0.0, 0.16, 0.32],
        "xpoint_half_length_m": 0.2,
        "pml_cells": 1,
        "pec_index_box_inclusive": {"x": [2, 4], "y": [3, 3], "z": [1, 3]},
    })
    print(root)


if __name__ == "__main__":
    main()
