"""Build a staged, structurally different P3 input from a frozen synthetic state."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import random


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    state = json.loads(args.source.read_text(encoding="utf-8"))
    if state["array_axes"] != ["r", "z"] or state["psi_units"] != "Wb/rad":
        raise ValueError("Unexpected frozen source axes or flux units")
    first = args.output / "stage0" / "input"
    later = args.output / "later" / "input"
    first.mkdir(parents=True, exist_ok=True)
    later.mkdir(parents=True, exist_ok=True)

    records = []
    for i, radius in enumerate(state["r_axis"]):
        for j, height in enumerate(state["z_axis"]):
            records.append((
                height * 100,
                state["psi"][i][j] * 1000,
                radius * 1000,
                state["B_Z_T"][i][j],
                state["B_R_T"][i][j] * 1000,
            ))
    random.Random(1207).shuffle(records)
    for name, rows in (("field-export-A.tsv", records[::2]),
                       ("field-export-B.tsv", records[1::2])):
        with (first / name).open("w", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream, delimiter="\t")
            writer.writerow(("Z_cm", "psi_mWb_per_rad", "R_mm", "Bz_T", "Br_mT"))
            writer.writerows(rows)

    (first / "export-note.md").write_text(
        "# Synthetic axisymmetric export\n\n"
        "The two TSV files are non-overlapping chunks of one already-computed "
        "R-Z state; row order is arbitrary. `R_mm` is the positive cylindrical "
        "radius, `Z_cm` is the shared axial coordinate. `Br_mT` and `Bz_T` "
        "are the complete static magnetic field for this exercise: B_phi = 0 "
        "by construction, not as a general device assumption. "
        "`psi_mWb_per_rad` is poloidal flux in milliwebers per radian. "
        "The declared separatrix is 130 mWb/rad and the closed-flux side "
        "has lower flux. The target grid is Cartesian x/y/z, in the same "
        "spatial frame as this source. The PEC index box is inclusive and the "
        "outer PML is one cell wide. These are synthetic classifications, not "
        "measured device facts. This is a saved field, not a request to solve "
        "a new equilibrium.\n",
        encoding="utf-8",
    )
    target = {
        "axis_units": "cm",
        "z_axis_cm": [-40, -25, -11, 0, 12, 28, 40],
        "x_axis_cm": [-50, -38, -27, -15, 0, 14, 26, 39, 50],
        "y_axis_cm": [-50, -36, -24, -12, 0, 13, 25, 37, 50],
        "xpoint_half_span_cm": 20,
        "pml_width_cells": 1,
        "pec_index_box_inclusive": {"x": [3, 5], "y": [4, 4], "z": [2, 4]},
    }
    (first / "target-grid.json").write_text(
        json.dumps(target, indent=2) + "\n", encoding="utf-8"
    )
    (args.output / "stage0" / "user-request.md").write_text(
        "I have a synthetic saved equilibrium export in two table chunks and "
        "a target grid. I cannot program and would like a small reusable "
        "project that maps what these files actually support onto the grid "
        "and explains the result in plain language. The chunks are in an "
        "unhelpful order. Please keep the inputs intact; I may add material "
        "settings and a station list after seeing this first result. This "
        "is exercise data, not a measured machine.\n",
        encoding="utf-8",
    )

    settings = {
        "model": "cold local plasma response for this first comparison",
        "frequency_settings": [
            {"name": "startup", "frequency_khz": 52000},
            {"name": "trial", "frequency_khz": 76000},
        ],
        "species": [
            {"name": "electron", "number_density_m3": 1.1e17,
             "charge_c": -1.602176634e-19, "mass_kg": 9.1093837139e-31,
             "collision_rate_per_s": 8.0e4},
            {"name": "hydrogen_ion", "number_density_m3": 1.1e17,
             "charge_c": 1.602176634e-19, "mass_kg": 1.67262192595e-27,
             "collision_rate_per_s": 8.0e4},
        ],
        "density_scope": "Uniform only at valid material-support grid nodes; undefined elsewhere, including PEC, PML and uncovered nodes. No off-grid density rule is supplied.",
        "missing_data": "No RF electric field, wave solution or deposited-power data are supplied.",
    }
    (later / "rf-settings.json").write_text(
        json.dumps(settings, indent=2) + "\n", encoding="utf-8"
    )
    with (later / "stations.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(("station", "z_cm", "x_cm", "y_cm"))
        writer.writerows((
            ("north", 5.5, 33, 29),
            ("west", 2.5, -31, 28),
            ("metal_lip", 4, 17, 3),
            ("outside", 0, 62, 0),
            ("missing_height", "", 31, -27),
            ("corner", 33, 47, 47),
        ))
    (args.output / "later" / "user-followup.md").write_text(
        "I added `input/rf-settings.json` and `input/stations.csv`. Please "
        "extend the same runnable project to compare the two stated cold "
        "material-response settings where the supplied data permit it, and "
        "give me one spreadsheet-friendly station table with clear blanks "
        "and reasons where a value cannot be supported. Keep the earlier "
        "mapping result available. Can these files tell me where RF power "
        "will actually be absorbed? Please distinguish a useful partial "
        "answer from what remains unknown.\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
