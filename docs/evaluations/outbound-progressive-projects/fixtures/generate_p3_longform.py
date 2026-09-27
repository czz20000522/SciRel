"""Generate a staged long-table P3 evaluation input from a frozen synthetic state."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--target-grid", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    state = json.loads(args.source.read_text(encoding="utf-8"))
    target = json.loads(args.target_grid.read_text(encoding="utf-8"))
    if state["array_axes"] != ["r", "z"] or state["psi_units"] != "Wb/rad":
        raise ValueError("fixture source axes or flux units differ from the expected frozen state")

    base = args.output / "stage0" / "input"
    later = args.output / "later" / "input"
    base.mkdir(parents=True, exist_ok=True)
    later.mkdir(parents=True, exist_ok=True)

    with (base / "field-points.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(("axial_cm", "psi_wb_per_rad", "b_z_t", "radial_cm", "b_r_t"))
        for j in reversed(range(len(state["z_axis"]))):
            for i in range(len(state["r_axis"])):
                writer.writerow(
                    (
                        state["z_axis"][j] * 100,
                        state["psi"][i][j],
                        state["B_Z_T"][i][j],
                        state["r_axis"][i] * 100,
                        state["B_R_T"][i][j],
                    )
                )

    (base / "field-notes.md").write_text(
        "# Synthetic field export\n\n"
        "This long table is an already-computed axisymmetric state, not measured device data. "
        "Each (radial_cm, axial_cm) pair occurs once; row order is export order, not array-axis order. "
        "The positive radial coordinate is cylindrical R. The columns `b_r_t` and `b_z_t` "
        "are the complete static field for this synthetic exercise; B_phi = 0 by construction, "
        "not by a tokamak default. `psi_wb_per_rad` is poloidal flux. "
        f"The declared separatrix level is {state['flux_surface']['separatrix_flux_wb_per_rad']} "
        f"Wb/rad and the closed side is `{state['flux_surface']['closed_flux_side']}`.\n\n"
        "The target grid axes are Cartesian x/y/z in meters. The PEC index box is inclusive, "
        "and the outer PML width is stated in cells. These are synthetic classifications; "
        "do not infer a real device boundary.\n",
        encoding="utf-8",
    )
    (base / "target-grid.json").write_text(
        json.dumps(target, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )

    with (later / "species.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(("species", "number_density_m3", "charge_c", "mass_kg", "collision_rate_s_inv"))
        writer.writerows(
            (
                ("electron", 1e17, -1.602176634e-19, 9.1093837139e-31, 1e5),
                ("hydrogen_ion", 1e17, 1.602176634e-19, 1.67262192595e-27, 1e5),
            )
        )
    (later / "rf-note.md").write_text(
        "# Synthetic material-response request\n\n"
        "Use the cold local response approximation for this first comparison. "
        "Compare `startup_check` at 50 MHz and `heating_trial` at 80 MHz. "
        "Species density is number density and is uniform only at valid material-support "
        "grid points. It is undefined outside that support, including uncovered, PEC and PML "
        "points. The location sheet uses Cartesian x/y/z coordinates in millimeters, in the "
        "same basis as the target grid. There is no RF electric field, wave solution or "
        "deposited-power data in these materials.\n",
        encoding="utf-8",
    )
    with (later / "locations.tsv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, delimiter="\t")
        writer.writerow(("location", "y_mm", "x_mm", "z_mm"))
        writer.writerows(
            (
                ("desk_a", 310, 290, 50),
                ("desk_b", 300, -310, 40),
                ("shield_near", 50, 140, 40),
                ("beyond_box", 0, 650, 0),
                ("unspecified_height", 300, 340, ""),
                ("desk_f", -300, -290, 30),
            )
        )


if __name__ == "__main__":
    main()
