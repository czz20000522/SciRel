"""Create staged synthetic inputs for a fresh P2 clarification evaluation."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


RADII_M = (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8)
HEIGHTS_M = (-0.3, -0.2, -0.1, 0.0, 0.1, 0.2, 0.3)


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def write_table(path: Path, *, unit: str, scale: float, reverse_rows: bool) -> None:
    factor = {"cm": 100.0, "mm": 1000.0}[unit]
    points = [(r, z) for z in HEIGHTS_M for r in RADII_M]
    if reverse_rows:
        points.reverse()
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, delimiter="\t")
        writer.writerow((f"radius_{unit}", f"height_{unit}", "flux_Wb_per_rad", "br_T", "bz_T"))
        for r, z in points:
            psi = scale * r * r * (0.34 + 0.03 * z * z)
            br = -scale * 0.06 * r * z
            bz = scale * (0.68 + 0.06 * z * z)
            writer.writerow((r * factor, z * factor, psi, br, bz))


def grid(axes_xy: list[float], axes_z: list[float]) -> dict:
    return {
        "source": "synthetic Cartesian target reader grid",
        "coordinates_m": {"x": axes_xy, "y": axes_xy, "z": axes_z},
        "xpoint_half_length_m": 0.2,
        "pml_cells": 1,
        "pec_index_box_inclusive": {"x": [2, 4], "y": [3, 3], "z": [1, 3]},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    solver = root / "solver-workspace"
    private = root / "examiner-private"
    for directory in (solver / "input" / "tables", solver / "input" / "reader", private):
        directory.mkdir(parents=True, exist_ok=False)

    write_table(solver / "input" / "tables" / "cedar.tsv", unit="cm", scale=1.12,
                reverse_rows=False)
    write_table(solver / "input" / "tables" / "quartz.tsv", unit="mm", scale=0.94,
                reverse_rows=True)
    write_json(solver / "input" / "export-index.json", {
        "origin": "two synthetic saved axisymmetric equilibrium exports, not measurements",
        "field_components": "cylindrical B_R and B_Z in T; B_phi not supplied",
        "flux_unit": "Wb/rad",
        "cases": {
            "cedar": {
                "table": "tables/cedar.tsv",
                "columns": {"r": "radius_cm", "z": "height_cm", "psi": "flux_Wb_per_rad",
                            "br": "br_T", "bz": "bz_T"},
                "separatrix_flux_wb_per_rad": 0.10,
                "closed_flux_side": "greater_than",
            },
            "quartz": {
                "table": "tables/quartz.tsv",
                "columns": {"r": "radius_mm", "z": "height_mm", "psi": "flux_Wb_per_rad",
                            "br": "br_T", "bz": "bz_T"},
                "separatrix_flux_wb_per_rad": 0.095,
                "closed_flux_side": None,
            },
        },
    })
    write_json(solver / "input" / "reader" / "grid-v1.json",
               grid([-0.6, -0.4, -0.2, 0.0, 0.2, 0.4, 0.6],
                    [-0.24, -0.12, 0.0, 0.12, 0.24]))
    (solver / "input" / "reader" / "target.md").write_text(
        "# Reader format\n\nOne NPZ per case: `magnetic_flux_density_t` has "
        "shape [Nx,Ny,Nz,3] and Cartesian components (Bx,By,Bz) in T; "
        "`poloidal_flux_wb_per_rad` has shape [Nx,Ny,Nz]; "
        "`material_support_mask` has shape [Nx,Ny,Nz] and bool dtype. "
        "Every field value must be finite. The reader receives x, y, z axes "
        "from the named grid file.\n",
        encoding="utf-8",
    )
    (solver / "input" / "handoff.txt").write_text(
        "These are already computed R-Z maps. The cedar index entry was signed "
        "off by the export owner. For quartz, one draft caption says the closed "
        "region is on the lower-flux side (`less_than`), but it was never "
        "checked against the exporter. Another draft says to copy cedar's "
        "setting. The two drafts have not been reconciled.\n",
        encoding="utf-8",
    )
    (private / "opening.txt").write_text(
        "We have two saved equilibrium exports in `input/` and need files for "
        "our target reader using `input/reader/grid-v1.json`. Please make a "
        "small project we can rerun when another grid arrives. I need a "
        "usable result for each case where the source information permits it, "
        "and a clear note about what is still missing. Ask me only if an "
        "important source condition is unresolved; I can check with the "
        "export owner.\n",
        encoding="utf-8",
    )
    (private / "reply.txt").write_text(
        "I checked the raw export with its owner. Quartz uses the lower-flux "
        "closed region (`less_than`) at the existing 0.095 Wb/rad separatrix; "
        "cedar remains `greater_than`. The two draft captions were guesses. "
        "A new reader grid is now at `input/reader/grid-v2.json`. Please "
        "produce both cases on that grid without overwriting the first "
        "results. I should be able to rerun the project for a later grid "
        "without editing Python.\n",
        encoding="utf-8",
    )
    write_json(private / "grid-v2.json",
               grid([-0.56, -0.35, -0.14, 0.0, 0.14, 0.35, 0.56],
                    [-0.28, -0.14, 0.0, 0.14, 0.28]))
    print(root)


if __name__ == "__main__":
    main()
