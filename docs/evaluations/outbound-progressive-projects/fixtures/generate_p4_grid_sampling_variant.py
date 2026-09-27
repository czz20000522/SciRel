"""Generate a staged synthetic coil case whose site values come from its preview grid."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def write_sites(path: Path, rows: tuple[tuple[str, float, float], ...]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(("site", "radius_m", "height_m"))
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("solver_root", type=Path)
    parser.add_argument("examiner_root", type=Path)
    args = parser.parse_args()
    solver_input = args.solver_root.resolve() / "input"
    examiner = args.examiner_root.resolve()
    for directory in (solver_input, examiner):
        directory.mkdir(parents=True, exist_ok=True)
        if any(directory.iterdir()):
            raise FileExistsError(f"refusing nonempty fixture directory: {directory}")

    write_json(solver_input / "coil-layout.json", {
        "coordinate_system": "axisymmetric cylindrical R-Z",
        "current_sign": "positive is one common toroidal winding direction",
        "coil_sections": [
            {"section": "upper", "radius_center_m": 0.72,
             "height_center_m": 0.23, "radial_width_m": 0.09,
             "vertical_height_m": 0.04, "radial_slices": 3,
             "vertical_slices": 2},
            {"section": "middle", "radius_center_m": 0.76,
             "height_center_m": 0.0, "radial_width_m": 0.06,
             "vertical_height_m": 0.09, "radial_slices": 2,
             "vertical_slices": 3},
            {"section": "lower", "radius_center_m": 0.72,
             "height_center_m": -0.23, "radial_width_m": 0.06,
             "vertical_height_m": 0.04, "radial_slices": 2,
             "vertical_slices": 2},
        ],
    })
    write_json(solver_input / "drive-settings.json", {
        "unit": "total_kA_turns_per_section",
        "settings": {"reference": {"upper": 6.3, "middle": -2.7,
                                   "lower": 5.4}},
    })
    write_json(solver_input / "preview-grid.json", {
        "r_m": [0.0, 0.09, 0.19, 0.31, 0.47],
        "z_m": [-0.30, -0.14, 0.02, 0.18, 0.34],
    })
    write_sites(solver_input / "readout-sites.csv", (
        ("axis", 0.0, 0.02),
        ("south", 0.035, -0.21),
        ("core", 0.24, 0.10),
        ("edge", 0.47, 0.34),
        ("outboard", 0.54, 0.03),
    ))
    (solver_input / "source-note.md").write_text(
        "# Synthetic preview handoff\n\n"
        "These are axisymmetric circular coil sections, not measured 3-D turns. "
        "Each signed drive is the total ampere-turns for its whole section, "
        "shared equally among radial_slices x vertical_slices representative "
        "filaments. Grid and readout coordinates are cylindrical [R,Z] in "
        "metres. The coarse preview grid is the product for this request: "
        "site readouts must be interpolated from the saved grid, not from a "
        "new direct field solve at each site. No plasma current, material "
        "boundary, measurement, pressure or density is supplied.\n",
        encoding="utf-8",
    )
    (examiner / "opening.txt").write_text(
        "I have the coil and readout files in input/. Please build a small "
        "project I can rerun to show a vacuum-field preview and an openable "
        "table at the listed sites. The site table must be a readout of the "
        "saved coarse preview grid: interpolate between neighboring preview "
        "rows and columns, rather than recalculating the coil field directly "
        "at each site. Keep sites outside the preview unavailable. Show field "
        "magnitude from the sampled components and explain what the synthetic "
        "files do and do not support physically. I do not know Python or "
        "SciRel; the project includes a development SciRel wheel, matching "
        "catalog and scientific skills.\n",
        encoding="utf-8",
    )
    write_json(examiner / "later-drive-settings.json", {
        "unit": "total_kA_turns_per_section",
        "settings": {
            "reference": {"upper": 6.3, "middle": -2.7, "lower": 5.4},
            "survey": {"upper": 6.3, "middle": -3.2, "lower": 5.4},
        },
    })
    write_sites(examiner / "later-readout-sites.csv", (
        ("between", 0.13, -0.06),
        ("beyond", 0.20, 0.40),
    ))
    (examiner / "followup.txt").write_text(
        "I added a survey drive in input/drive-settings.json and two sites in "
        "input/later-readout-sites.csv. Please compare both settings at all "
        "sites using values read from each setting's saved preview grid, keep "
        "the first table and image openable, and make the normal rerun command "
        "avoid stale or redundant results. Tell me whether their largest site "
        "difference bounds the vacuum-field numerical error everywhere.\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
