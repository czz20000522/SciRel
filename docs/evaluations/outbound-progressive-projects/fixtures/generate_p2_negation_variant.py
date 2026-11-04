"""Create staged, synthetic P2 inputs with a tentative negated science note."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


RADII_M = (0.12, 0.22, 0.32, 0.42, 0.52, 0.62, 0.72, 0.82)
HEIGHTS_M = (-0.3, -0.2, -0.1, 0.0, 0.1, 0.2, 0.3)


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def write_map(path: Path, *, scale: float, reverse_rows: bool) -> None:
    points = [(r, z) for z in HEIGHTS_M for r in RADII_M]
    if reverse_rows:
        points.reverse()
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(("R_cm", "Z_cm", "B_R_mT", "B_Z_mT", "psi_mWb_per_rad"))
        for r, z in points:
            psi = scale * r * r * (0.34 + 0.02 * z * z)
            br = -scale * 0.04 * r * z
            bz = scale * (0.68 + 0.04 * z * z)
            writer.writerow((r * 100, z * 100, br * 1000, bz * 1000, psi * 1000))


def grid(xy: list[float], z: list[float]) -> dict:
    return {
        "coordinates_m": {"x": xy, "y": xy, "z": z},
        "xpoint_half_length_m": 0.11,
        "pml_cells": 1,
        "pec_index_box_inclusive": {"x": [3, 3], "y": [3, 3], "z": [2, 2]},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("solver_root", type=Path)
    parser.add_argument("examiner_root", type=Path)
    args = parser.parse_args()
    solver = args.solver_root.resolve()
    examiner = args.examiner_root.resolve()
    for directory in (solver / "input" / "exports", solver / "input" / "reader", examiner):
        directory.mkdir(parents=True, exist_ok=False)

    write_map(solver / "input" / "exports" / "birch.csv", scale=1.0, reverse_rows=True)
    write_map(solver / "input" / "exports" / "opal.csv", scale=1.08, reverse_rows=False)
    write_json(solver / "input" / "cases.json", {
        "origin": "saved synthetic equilibrium maps; not measurements",
        "source_columns": "R and Z in cm, B_R and B_Z in mT, psi in mWb/rad; B_phi absent",
        "cases": {
            "birch": {
                "file": "exports/birch.csv",
                "separatrix_flux_wb_per_rad": 0.07,
                "closed_flux_side": "greater_than",
                "side_source": "signed export manifest",
            },
            "opal": {
                "file": "exports/opal.csv",
                "separatrix_flux_wb_per_rad": 0.07,
                "closed_flux_side": None,
            },
        },
    })
    write_json(solver / "input" / "reader" / "scan-a.json",
               grid([-0.6, -0.4, -0.2, 0.0, 0.2, 0.4, 0.6],
                    [-0.24, -0.12, 0.0, 0.12, 0.24]))
    (solver / "input" / "reader" / "contract.md").write_text(
        "# Reader contract\n\nFor each scientifically supported case and target grid, "
        "deliver an NPZ with exactly `magnetic_flux_density_t` [Nx,Ny,Nz,3] "
        "in Cartesian Tesla, `poloidal_flux_wb_per_rad` [Nx,Ny,Nz], and "
        "`material_support_mask` [Nx,Ny,Nz] boolean. All numeric values "
        "must be finite. The reader gets axes from the grid JSON. Preserve "
        "earlier outputs when another scan arrives.\n",
        encoding="utf-8",
    )
    (solver / "input" / "handoff.md").write_text(
        "# Export handoff\n\nBirch's flux side in `cases.json` was signed off "
        "by the exporter. Opal's handwritten margin says "
        "`closed_flux_side: not greater_than?` but the writer adds "
        "`perhaps less_than; needs owner confirmation`. These are tentative "
        "notes, not an export-owner declaration.\n",
        encoding="utf-8",
    )
    (examiner / "opening.txt").write_text(
        "I have two saved equilibrium maps under `input/` and need reader files "
        "for `input/reader/scan-a.json`. Please make a rerunnable small project. "
        "Give me the usable portion now, and ask only for a scientifically "
        "important condition that the files do not settle. I do not write "
        "Python; please handle the file conversion and checks.\n",
        encoding="utf-8",
    )
    (examiner / "reply.txt").write_text(
        "I checked with the export owner: opal uses the lower-flux closed "
        "region, `less_than`, at the recorded 0.07 Wb/rad separatrix. "
        "The handwritten margin was not a decision. I have a second reader "
        "scan at `input/reader/scan-b.json`. Please add that output without "
        "overwriting the first scan. If any case cannot satisfy the scientific "
        "asset on the new scan, keep a useful diagnostic separate from a "
        "reader file and tell me what failed.\n",
        encoding="utf-8",
    )
    write_json(examiner / "scan-b.json",
               grid([-0.56, -0.36, -0.16, 0.0, 0.16, 0.36, 0.56],
                    [-0.28, -0.14, 0.0, 0.14, 0.28]))


if __name__ == "__main__":
    main()
